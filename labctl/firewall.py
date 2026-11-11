"""nftables rules that isolate the containers on the NAT bridge from the host, the LAN and each other.

Rules for traffic on the NAT bridge:
- to the host itself: everything dropped. Containers have fixed addresses and name servers
  elsewhere, so they need nothing from the host.
- forwarded out: dropped to private/special ranges, to configured protected networks and
  to the default gateway itself, except the containers' own name servers on port 53.
  Everything else must be routed *via* a known default gateway (`rt ip nexthop`), so
  on-link LAN hosts are unreachable even when the LAN uses public addresses.
- forwarded in: only SSH that the host port-forwards to a container, and replies.
- IPv6 dropped entirely.

Traffic between two containers never reaches these rules: it is bridged, and the bridge
rules in labctl.pve drop it.

The gateway set starts empty and is filled by `render_gateway_sync`. While it is empty or
stale (e.g. DHCP moved the host to another network), containers cannot reach anything:
the design fails closed.
"""

import ipaddress

# 私有、共享、保留與特殊用途位址，容器一律不能直接連。
BLOCKED_V4 = [
    "0.0.0.0/8",
    "10.0.0.0/8",
    "100.64.0.0/10",
    "127.0.0.0/8",
    "169.254.0.0/16",
    "172.16.0.0/12",
    "192.0.0.0/24",
    "192.168.0.0/16",
    "198.18.0.0/15",
    "224.0.0.0/4",
    "240.0.0.0/4",
]


def _v4_set(networks):
    collapsed = ipaddress.collapse_addresses(ipaddress.ip_network(n, strict=True) for n in networks)
    return ", ".join(str(n) for n in collapsed)


def render_ruleset(protected_networks, table, bridge, dns_servers=()):
    """Return an nft script that atomically replaces `table` with the rules for `bridge`."""
    lab = f'"{bridge}"'
    # 名稱伺服器可能在私有網段或受保護網段裡，只對它們開 53 埠，其他目的地照樣限制。
    dns = ""
    if dns_servers:
        servers = ", ".join(str(ipaddress.IPv4Address(s)) for s in dns_servers)
        dns = "".join(
            f"\t\tiifname {lab} ip daddr {{ {servers} }} {proto} dport 53 accept\n" for proto in ("udp", "tcp")
        )
    return (
        "#!/usr/sbin/nft -f\n"
        "# Managed by labctl. Regenerate instead of editing.\n"
        f"table {table}\n"
        f"delete table {table}\n"
        "\n"
        f"table {table} {{\n"
        "\tset blocked_v4 {\n"
        "\t\ttype ipv4_addr\n"
        "\t\tflags interval\n"
        f"\t\telements = {{ {_v4_set(BLOCKED_V4 + list(protected_networks))} }}\n"
        "\t}\n"
        "\n"
        "\t# Filled by gateway sync. Empty or stale means containers are cut off (fail-closed).\n"
        "\tset uplink_gateways {\n"
        "\t\ttype ipv4_addr\n"
        "\t}\n"
        "\n"
        "\tchain input {\n"
        "\t\ttype filter hook input priority filter - 10; policy accept;\n"
        f"\t\tiifname {lab} drop\n"
        "\t}\n"
        "\n"
        "\tchain forward {\n"
        "\t\ttype filter hook forward priority filter - 10; policy accept;\n"
        f"\t\tiifname {lab} meta nfproto ipv6 drop\n"
        f"\t\toifname {lab} meta nfproto ipv6 drop\n"
        # 轉發進來的 SSH 的回程：使用者可能在私有或同一個網段，不受下面的目的地限制。
        f"\t\tiifname {lab} ct status dnat accept\n"
        f"{dns}"
        f"\t\tiifname {lab} ip daddr @blocked_v4 drop\n"
        f"\t\tiifname {lab} ip daddr @uplink_gateways drop\n"
        f"\t\tiifname {lab} rt ip nexthop != @uplink_gateways drop\n"
        f"\t\toifname {lab} ct state established,related accept\n"
        f"\t\toifname {lab} ct status dnat tcp dport 22 accept\n"
        f"\t\toifname {lab} drop\n"
        "\t}\n"
        "}\n"
    )


def default_gateways(routes):
    """Gateways from `ip -j -4 route show default` output, sorted and validated."""
    gateways = set()
    for route in routes:
        if "gateway" in route:
            gateways.add(ipaddress.IPv4Address(route["gateway"]))  # ValueError on garbage
    return [str(g) for g in sorted(gateways)]


def render_gateway_sync(gateways, table):
    """Return an nft script that atomically replaces the allowed uplink gateways in `table`."""
    addresses = [str(ipaddress.IPv4Address(g)) for g in gateways]
    script = f"flush set {table} uplink_gateways\n"
    if addresses:
        script += f"add element {table} uplink_gateways {{ {', '.join(addresses)} }}\n"
    return script
