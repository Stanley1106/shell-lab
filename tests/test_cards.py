import stat
import unittest

from labctl.cards import build_connect_cards, parse_connect_lines, write_connect_markdown
from tests.helpers import scratch_dir

TWO = ["student01", "student02"]


class ConnectCardsTest(unittest.TestCase):
    """PVE deployment: the access mode prints the commands, labctl adds the passwords."""

    def test_commands_and_passwords_end_up_in_one_private_file(self):
        commands = parse_connect_lines(
            "student01\tssh student@192.0.2.1 -p 22001\nstudent02\tssh student@192.0.2.1 -p 22002\n"
        )
        cards = build_connect_cards(TWO, commands, {"student01": "aaaa-bbbb-cccc", "student02": "dddd-eeee-ffff"})
        path = scratch_dir() / "pve-cards.md"
        write_connect_markdown(path, cards)
        text = path.read_text(encoding="utf-8")
        self.assertIn("- student02\n  ```\n  ssh student@192.0.2.1 -p 22002\n  ```\n  - 密碼 `dddd-eeee-ffff`", text)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_missing_data_names_the_student(self):
        commands = parse_connect_lines("student01\tssh student@192.0.2.1 -p 22001\n")
        with self.assertRaises(ValueError) as ctx:
            build_connect_cards(TWO, commands, {"student01": "aaaa-bbbb-cccc"})
        self.assertIn("student02 (command, password)", str(ctx.exception))

    def test_lines_that_would_break_the_list_are_refused(self):
        for line in ("student01 ssh x", "student01\tssh `id`", "student01\t", "student01\tssh a\nstudent01\tssh b"):
            with self.assertRaises(ValueError, msg=line):
                parse_connect_lines(line)
