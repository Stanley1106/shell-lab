import getpass
import socket
import subprocess
import sys
import unittest

from labctl.labs import art
from labctl.labs.hello import render_script
from tests.helpers import scratch_dir


class HelloTest(unittest.TestCase):
    def run_hello(self):
        path = scratch_dir() / "hello"
        path.write_text(render_script(), encoding="utf-8")
        return subprocess.run([sys.executable, str(path)], capture_output=True, text=True, check=True).stdout

    def test_spider_then_xiaoyi_says_hello(self):
        out = self.run_hello()
        self.assertTrue(out.startswith(art.spider()))
        self.assertIn("我是小壹", out)

    def test_explains_the_students_own_prompt(self):
        user, host = getpass.getuser(), socket.gethostname()
        out = self.run_hello()
        self.assertIn(f"{user}@{host}:~$", out)
        self.assertIn(f"{user}：你的帳號", out)
        self.assertIn(f"{host}：這台主機的名稱", out)

    def test_ends_with_the_way_into_the_labs(self):
        out = self.run_hello()
        self.assertIn("cd ~/lab\n    cat README.md", out)
        self.assertNotIn("flag{", out)  # 第 0 題沒有 flag

    def test_script_runs_with_the_system_python(self):
        self.assertTrue(render_script().startswith("#!/usr/bin/env python3\n"))


if __name__ == "__main__":
    unittest.main()
