import unittest

from labctl.firewall import default_gateways, render_gateway_sync, render_ruleset


class DefaultGatewaysTest(unittest.TestCase):
    """Input is `ip -j -4 route show default` output."""

    def test_single_default_route(self):
        routes = [{"dst": "default", "gateway": "172.27.240.1", "dev": "eth0", "protocol": "kernel", "flags": []}]
        self.assertEqual(default_gateways(routes), ["172.27.240.1"])

    def test_multiple_uplinks_all_count(self):
        routes = [
            {
                "dst": "default",
                "gateway": "192.168.1.1",
                "dev": "wlan0",
                "protocol": "dhcp",
                "prefsrc": "192.168.1.23",
                "metric": 600,
                "flags": [],
            },
            {
                "dst": "default",
                "gateway": "203.0.113.1",
                "dev": "eth1",
                "protocol": "dhcp",
                "prefsrc": "203.0.113.17",
                "metric": 100,
                "flags": [],
            },
        ]
        self.assertEqual(default_gateways(routes), ["192.168.1.1", "203.0.113.1"])

    def test_device_only_default_route_is_ignored(self):
        # 例如 VPN 介面的 "default dev wg0"：沒有閘道可放行。
        routes = [{"dst": "default", "dev": "wg0", "scope": "link", "flags": []}]
        self.assertEqual(default_gateways(routes), [])

    def test_malformed_gateway_rejected(self):
        # 閘道位址會寫進 nft 腳本，格式不對就停止。
        routes = [{"dst": "default", "gateway": "1.2.3.4 } ; flush ruleset", "dev": "eth0", "flags": []}]
        with self.assertRaises(ValueError):
            default_gateways(routes)


class RulesetTest(unittest.TestCase):
    def rules(self, **kwargs):
        return render_ruleset(["203.0.113.0/24"], "inet shell_lab_pve", "vmbr1", **kwargs)

    def test_nothing_reaches_the_host_from_the_bridge(self):
        input_chain = self.rules().split("chain input", 1)[1].split("chain forward", 1)[0]
        self.assertEqual(
            [line.strip() for line in input_chain.splitlines() if "vmbr1" in line], ['iifname "vmbr1" drop']
        )

    def test_only_port_forwarded_ssh_comes_in(self):
        text = self.rules()
        self.assertIn('oifname "vmbr1" ct status dnat tcp dport 22 accept', text)
        self.assertIn('iifname "vmbr1" ct status dnat accept', text)
        self.assertTrue(text.rstrip().endswith('oifname "vmbr1" drop\n\t}\n}'))

    def test_protected_networks_join_the_blocked_set(self):
        self.assertIn("203.0.113.0/24", self.rules())

    def test_dns_servers_only_on_port_53(self):
        self.assertNotIn("dport 53", self.rules())
        text = self.rules(dns_servers=["10.0.0.53"])
        self.assertIn('iifname "vmbr1" ip daddr { 10.0.0.53 } udp dport 53 accept', text)
        self.assertIn('iifname "vmbr1" ip daddr { 10.0.0.53 } tcp dport 53 accept', text)

    def test_gateway_sync_replaces_the_set_in_the_given_table(self):
        self.assertEqual(
            render_gateway_sync(["198.51.100.1"], "inet shell_lab_pve"),
            "flush set inet shell_lab_pve uplink_gateways\n"
            "add element inet shell_lab_pve uplink_gateways { 198.51.100.1 }\n",
        )


if __name__ == "__main__":
    unittest.main()
