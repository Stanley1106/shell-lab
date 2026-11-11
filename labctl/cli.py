"""Command line entry point: python3 -m labctl [--env FILE] <command>."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from labctl import cards, passwords
from labctl.firewall import default_gateways
from labctl.labs import DEFAULT_FLAG_PREFIX, LABS, build_labs, full_flag
from labctl.pve import (
    build_plan,
    ct_fields,
    load_config,
    render_access,
    render_gateway_sync,
    render_guest_setup,
    render_network,
    shell_settings,
)
from labctl.settings import select_students

# 舊版的檔名有 pve- 前綴。新檔名不存在時不能悄悄產生新密碼，學生的密碼會全部換掉。
LEGACY_PASSWORDS = "pve-passwords.json"


def cmd_check(args):
    config = load_config(args.env)
    print(f"{args.env} OK: {config.student_count} containers, access mode {config.access_mode}")


def cmd_settings(args):
    sys.stdout.write(shell_settings(load_config(args.env)))


def cmd_students(args):
    print("\n".join(load_config(args.env).students()))


def cmd_plan(args):
    print(json.dumps(build_plan(load_config(args.env), args.students), ensure_ascii=False, indent=2))


def cmd_ct(args):
    instance = build_plan(load_config(args.env), [args.student])["instances"][0]
    print(" ".join(ct_fields(instance, args.fields)))


def cmd_render_network(args):
    dns = [d for d in args.dns.split(",") if d] if args.dns else []
    sys.stdout.write(render_network(load_config(args.env), dns))


def cmd_render_access(args):
    sys.stdout.write(render_access(load_config(args.env)))


def cmd_render_gateway_sync(args):
    load_config(args.env)  # 設定有問題就停，不清空閘道
    routes = json.loads(sys.stdin.read() or "[]")
    if not isinstance(routes, list):
        raise ValueError("expected the JSON list printed by: ip -j -4 route show default")
    sys.stdout.write(render_gateway_sync(default_gateways(routes)))


def cmd_render_guest_setup(args):
    sys.stdout.write(render_guest_setup(load_config(args.env)))


def cmd_labs_build(args):
    config = load_config(args.env)
    select_students(config.students(), [args.student])  # 不在名單上的學生直接停止
    if not config.lab_secret:
        raise ValueError("LAB_SECRET is empty, create the settings with: make env")
    flags = build_labs(args.out, config.lab_secret, config.cohort, args.student, args.round, config.flag_prefix)
    print(f"built {len(flags)} labs for {args.student} in {args.out}")


def cmd_labs_flags(args):
    # flag 是每題固定的一句話，全班相同。沒有設定檔時用預設前綴。
    prefix = load_config(args.env).flag_prefix if args.env.is_file() else DEFAULT_FLAG_PREFIX
    print(json.dumps({lab.LAB_ID: full_flag(lab, prefix) for lab in LABS}, ensure_ascii=False, indent=2))


def cmd_passwords_new(args):
    legacy = Path(args.file).with_name(LEGACY_PASSWORDS)
    if not Path(args.file).exists() and legacy.exists():
        raise ValueError(f"the passwords are in {legacy}, keep them with: mv {legacy} {args.file}")
    added = passwords.ensure(args.file, load_config(args.env).students())
    print(f"{args.file}: added {added} passwords")


def cmd_passwords_export(args):
    sys.stdout.write(passwords.export_lines(args.file, load_config(args.env).students()))


def cmd_cards(args):
    config = load_config(args.env)
    commands = cards.parse_connect_lines(sys.stdin.read())
    built = cards.build_connect_cards(config.students(), commands, passwords.load(args.passwords))
    cards.write_connect_markdown(args.out, built)
    print(f"wrote {len(built)} students to {args.out}")


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

    command(commands, "check", cmd_check, "validate every setting")
    command(commands, "settings", cmd_settings, "print the settings as KEY=value lines, without LAB_SECRET")
    command(commands, "students", cmd_students, "print every student id")
    command(commands, "plan", cmd_plan, "print the container plan as JSON").add_argument(
        "--students", nargs="+", help="limit to these students"
    )
    ct = command(commands, "ct", cmd_ct, "print fields of one container, separated by spaces")
    ct.add_argument("student")
    ct.add_argument("fields", nargs="+")

    render = group("render", "print generated rules and scripts")
    command(render, "network", cmd_render_network, "nftables rules of the container network").add_argument(
        "--dns", help="the containers' name servers, separated by commas"
    )
    command(render, "access", cmd_render_access, "nftables rules of the access mode")
    command(render, "gateway-sync", cmd_render_gateway_sync, "nft script for the uplink gateways (stdin: ip -j route)")
    command(render, "guest-setup", cmd_render_guest_setup, "bash script that sets up one container")

    labs = group("labs", "lab exercises")
    build = command(labs, "build", cmd_labs_build, "create every lab for one student in an empty directory")
    build.add_argument("student")
    build.add_argument("--out", required=True, help="empty or missing directory")
    build.add_argument("--round", type=int, default=1, help="data round, bump it for fresh data")
    command(labs, "flags", cmd_labs_flags, "print each lab's flag (the answers, the same for everyone)")

    pw = group("passwords", "student passwords in local/passwords.json")
    for name, func, help_text in (
        ("new", cmd_passwords_new, "create a password for every student who has none"),
        ("export", cmd_passwords_export, "print `sid password` lines for shell-lab-setup.sh --passwords"),
    ):
        command(pw, name, func, help_text).add_argument("--file", default="local/passwords.json")

    card = command(
        commands, "cards", cmd_cards, "write every student's connection (stdin: shell-lab-setup.sh --connect)"
    )
    card.add_argument("--passwords", default="local/passwords.json")
    card.add_argument("--out", default="local/cards.md", help="Markdown file, mode 600, replaced if it exists")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
        return 0
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
