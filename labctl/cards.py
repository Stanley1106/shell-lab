"""Connection list: every student's connection command and password in one Markdown file, only for the teacher.

How a student reaches their container depends on the access mode, so the commands come from
shell-lab-setup.sh --connect; this module only merges them with the passwords.
"""

import re

from labctl.passwords import PASSWORD
from labctl.private import write_private


def _matches(pattern, value):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _md_code(value):
    # 用比內容更長的反引號包起來，密碼裡有 ` 也不會把格式弄壞。
    fence = "`" * (max((len(run) for run in re.findall(r"`+", value)), default=0) + 1)
    pad = " " if value.startswith("`") or value.endswith("`") else ""
    return f"{fence}{pad}{value}{pad}{fence}"


CONNECT_MARKDOWN = """\
# Linux Lab 連線指令

每個人只拿自己的那一段。在終端機執行連線指令，第一次連線問要不要繼續時輸入 yes，再輸入密碼。

{cards}"""

CONNECT_CARD = """\
- {sid}
  ```
  {connect}
  ```
  - 密碼 {password}
"""

# 連線指令放進程式碼區塊，只接受不會弄壞格式的字元。
CONNECT = re.compile(r"[A-Za-z0-9][A-Za-z0-9 @:._/=-]{0,199}")


def parse_connect_lines(text):
    """`sid<TAB>command` lines from shell-lab-setup.sh --connect, as {sid: command}."""
    commands = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        sid, sep, command = line.partition("\t")
        if not sep or not CONNECT.fullmatch(command) or sid in commands:
            raise ValueError(f"malformed connection line: {line!r}")
        commands[sid] = command
    return commands


def build_connect_cards(students, commands, passwords):
    """{student_id: card}, stopping if anyone lacks a connection command or a password."""
    cards, problems = {}, []
    for sid in students:
        command, password = commands.get(sid), passwords.get(sid)
        bad = [name for name, ok in (("command", command), ("password", _matches(PASSWORD, password))) if not ok]
        if bad:
            problems.append(f"{sid} ({', '.join(bad)})")
            continue
        cards[sid] = {"sid": sid, "connect": command, "password": password}
    if problems:
        raise ValueError("missing or malformed card data: " + ", ".join(problems))
    return cards


def write_connect_markdown(path, cards):
    """Write the PVE connection list to `path` (mode 600), replacing it in one step."""
    text = CONNECT_MARKDOWN.format(
        cards="".join(
            CONNECT_CARD.format(sid=c["sid"], connect=c["connect"], password=_md_code(c["password"]))
            for c in cards.values()
        )
    )
    write_private(path, text)
