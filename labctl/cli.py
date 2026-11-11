"""Command line entry point: python3 -m labctl [--env FILE] <command>."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from labctl import cards, passwords
from labctl.firewall import default_gateways
from labctl.labs import build_labs
from labctl.pve import (
    build_pve_plan,
    ct_fields,
    load_pve_config,
    render_access,
    render_gateway_sync_pve,
    render_guest_setup,
    render_network,
    shell_settings,
)
from labctl.settings import select_students


def cmd_pve_check(args):
    config = load_pve_config(args.env)
    print(f"{args.env} OK: {config.student_count} containers, access mode {config.access_mode}")


def cmd_pve_settings(args):
    sys.stdout.write(shell_settings(load_pve_config(args.env)))


def cmd_pve_students(args):
    print("\n".join(load_pve_config(args.env).students()))


def cmd_pve_plan(args):
    print(json.dumps(build_pve_plan(load_pve_config(args.env), args.students), ensure_ascii=False, indent=2))


def cmd_pve_ct(args):
    instance = build_pve_plan(load_pve_config(args.env), [args.student])["instances"][0]
    print(" ".join(ct_fields(instance, args.fields)))


def cmd_pve_render_access(args):
    sys.stdout.write(render_access(load_pve_config(args.env)))


def cmd_pve_render_network(args):
    dns = [d for d in args.dns.split(",") if d] if args.dns else []
    sys.stdout.write(render_network(load_pve_config(args.env), dns))


def cmd_pve_render_gateway_sync(args):
    load_pve_config(args.env)  # 設定有問題就停，不清空閘道
    routes = json.loads(sys.stdin.read() or "[]")
    if not isinstance(routes, list):
        raise ValueError("expected the JSON list printed by: ip -j -4 route show default")
    sys.stdout.write(render_gateway_sync_pve(default_gateways(routes)))


def cmd_pve_render_guest_setup(args):
    sys.stdout.write(render_guest_setup(load_pve_config(args.env)))


def cmd_pve_labs_build(args):
    config = load_pve_config(args.env)
    select_students(config.students(), [args.student])  # 不在名單上的學生直接停止
    if not config.lab_secret:
        raise ValueError("LAB_SECRET is empty, create the settings with: make pve-env")
    flags = build_labs(args.out, config.lab_secret, config.cohort, args.student, args.round, config.flag_prefix)
    print(f"built {len(flags)} labs for {args.student} in {args.out}")


def cmd_pve_cards(args):
    config = load_pve_config(args.env)
    commands = cards.parse_connect_lines(sys.stdin.read())
    built = cards.build_connect_cards(config.students(), commands, passwords.load(args.passwords))
    cards.write_connect_markdown(args.out, built)
    print(f"wrote {len(built)} students to {args.out}")


def cmd_pve_passwords_new(args):
    added = passwords.ensure(args.file, load_pve_config(args.env).students())
    print(f"{args.file}: added {added} passwords")


def cmd_pve_passwords_export(args):
    sys.stdout.write(passwords.export_lines(args.file, load_pve_config(args.env).students()))


def build_parser():
    parser = argparse.ArgumentParser(prog="labctl", description="Shell lab tooling")
    parser.add_argument("--env", default=".env", type=Path, help="settings file (default: .env)")
    commands = parser.add_subparsers(dest="command", required=True)

    def group(name, help_text):
        return commands.add_parser(name, help=help_text).add_subparsers(dest="what", required=True)

    def command(parent, name, func, help_text):
        sub = parent.add_parser(name, help=help_text)
        sub.set_defaults(func=func)
        return sub

    pve = group("pve", "PVE LXC deployment (--env deploy/pve/shell-lab.env)")
    command(pve, "check", cmd_pve_check, "validate every setting")
    command(pve, "settings", cmd_pve_settings, "print the settings as KEY=value lines, without LAB_SECRET")
    command(pve, "students", cmd_pve_students, "print every student id")
    command(pve, "plan", cmd_pve_plan, "print the container plan as JSON").add_argument(
        "--students", nargs="+", help="limit to these students"
    )
    ct = command(pve, "ct", cmd_pve_ct, "print fields of one container, separated by spaces")
    ct.add_argument("student")
    ct.add_argument("fields", nargs="+")
    command(pve, "render-network", cmd_pve_render_network, "nftables rules of the container network").add_argument(
        "--dns", help="the containers' name servers, separated by commas"
    )
    command(
        pve,
        "render-gateway-sync",
        cmd_pve_render_gateway_sync,
        "nft script for the uplink gateways (stdin: ip -j route)",
    )
    command(pve, "render-access", cmd_pve_render_access, "nftables rules of the access mode")
    command(pve, "render-guest-setup", cmd_pve_render_guest_setup, "bash script that sets up one container")
    for name, func, help_text in (
        ("passwords-new", cmd_pve_passwords_new, "create a password for every student who has none"),
        ("passwords-export", cmd_pve_passwords_export, "print `sid password` lines for shell-lab-setup.sh"),
    ):
        command(pve, name, func, help_text).add_argument("--file", default="local/pve-passwords.json")
    pve_build = command(pve, "labs-build", cmd_pve_labs_build, "create every lab for one student in an empty directory")
    pve_build.add_argument("student")
    pve_build.add_argument("--out", required=True, help="empty or missing directory")
    pve_build.add_argument("--round", type=int, default=1, help="data round, bump it for fresh data")
    pve_cards = command(
        pve, "cards", cmd_pve_cards, "write every student's command and password (stdin: shell-lab-setup.sh --connect)"
    )
    pve_cards.add_argument("--passwords", default="local/pve-passwords.json")
    pve_cards.add_argument("--out", default="local/pve-cards.md", help="Markdown file, mode 600, replaced if it exists")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
        return 0
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
