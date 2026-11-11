import json
import os
import stat
import subprocess
import sys
import unittest

from labctl.labs import LABS, full_flag
from tests.helpers import REPO, SECRET_HEX, scratch_dir

REQUIRED = {"PORTFORWARD_SOURCES": "198.51.100.0/24"}


def write_env(mode=0o600, **values):
    path = scratch_dir() / ".env"
    path.write_text("".join(f"{k}={v}\n" for k, v in {**REQUIRED, **values}.items()), encoding="utf-8")
    path.chmod(mode)
    return path


def labctl(*args, stdin=None):
    return subprocess.run(
        [sys.executable, "-m", "labctl", *map(str, args)], cwd=REPO, input=stdin, capture_output=True, text=True
    )


class SettingsCommandTest(unittest.TestCase):
    def test_check_reports_the_settings(self):
        result = labctl("--env", write_env(STUDENT_COUNT="3"), "check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("3 containers, access mode portforward", result.stdout)

    def test_invalid_settings_exit_2_with_a_message(self):
        result = labctl("--env", write_env(STUDENT_COUNT="0"), "check")
        self.assertEqual(result.returncode, 2)
        self.assertIn("ERROR: STUDENT_COUNT", result.stderr)

    def test_missing_settings_say_how_to_create_them(self):
        result = labctl("--env", scratch_dir() / ".env", "check")
        self.assertEqual(result.returncode, 2)
        self.assertIn("make env", result.stderr)

    def test_settings_with_a_secret_readable_by_others_are_refused(self):
        result = labctl("--env", write_env(mode=0o644, LAB_SECRET=SECRET_HEX), "check")
        self.assertEqual(result.returncode, 2)
        self.assertIn("chmod 600", result.stderr)

    def test_settings_never_print_the_secret(self):
        result = labctl("--env", write_env(LAB_SECRET=SECRET_HEX), "settings")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(SECRET_HEX, result.stdout)
        self.assertIn("STUDENT_COUNT=20\n", result.stdout)


class RenderCommandTest(unittest.TestCase):
    def test_every_render_produces_output(self):
        env = write_env(STUDENT_COUNT="2")
        for what, needle in (
            (("network", "--dns", "192.0.2.53"), "table inet shell_lab_pve"),
            (("access",), "table ip shell_lab_access"),
            (("guest-setup",), "apt-get install"),
        ):
            result = labctl("--env", env, "render", *what)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(needle, result.stdout)

    def test_gateway_sync_takes_the_default_routes(self):
        routes = [{"dst": "default", "gateway": "192.0.2.254", "dev": "vmbr0"}]
        result = labctl("--env", write_env(), "render", "gateway-sync", stdin=json.dumps(routes))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("add element inet shell_lab_pve uplink_gateways { 192.0.2.254 }", result.stdout)

    def test_gateway_sync_without_a_default_route_empties_the_set(self):
        result = labctl("--env", write_env(), "render", "gateway-sync", stdin="[]")
        self.assertEqual(result.stdout, "flush set inet shell_lab_pve uplink_gateways\n")

    def test_gateway_sync_refuses_garbage(self):
        result = labctl("--env", write_env(), "render", "gateway-sync", stdin='{"not": "a list"}')
        self.assertEqual(result.returncode, 2)


class LabsCommandTest(unittest.TestCase):
    def test_build_creates_all_labs_for_one_student(self):
        out = scratch_dir() / "lab"
        result = labctl("--env", write_env(LAB_SECRET=SECRET_HEX), "labs", "build", "student01", "--out", out)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(p.name for p in out.iterdir() if p.is_dir()), sorted(lab.LAB_ID for lab in LABS))

    def test_build_rejects_a_student_not_in_the_class(self):
        env = write_env(LAB_SECRET=SECRET_HEX, STUDENT_COUNT="2")
        result = labctl("--env", env, "labs", "build", "student03", "--out", scratch_dir() / "lab")
        self.assertEqual(result.returncode, 2)

    def test_build_needs_a_lab_secret(self):
        result = labctl("--env", write_env(), "labs", "build", "student01", "--out", scratch_dir() / "lab")
        self.assertEqual(result.returncode, 2)
        self.assertIn("LAB_SECRET is empty", result.stderr)

    def test_flags_list_the_answers_with_the_configured_prefix(self):
        result = labctl("--env", write_env(FLAG_PREFIX="ctf"), "labs", "flags")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {lab.LAB_ID: full_flag(lab, "ctf") for lab in LABS})

    def test_flags_work_without_settings(self):
        result = labctl("--env", scratch_dir() / ".env", "labs", "flags")
        self.assertEqual(json.loads(result.stdout), {lab.LAB_ID: full_flag(lab) for lab in LABS})


class PasswordsCommandTest(unittest.TestCase):
    def setUp(self):
        self.env = write_env(STUDENT_COUNT="2")
        self.file = scratch_dir() / "passwords.json"

    def test_passwords_are_created_once_and_exported_as_lines(self):
        first = labctl("--env", self.env, "passwords", "new", "--file", self.file)
        self.assertIn("added 2 passwords", first.stdout)
        self.assertEqual(stat.S_IMODE(os.stat(self.file).st_mode), 0o600)
        again = labctl("--env", self.env, "passwords", "new", "--file", self.file)
        self.assertIn("added 0 passwords", again.stdout)
        lines = labctl("--env", self.env, "passwords", "export", "--file", self.file).stdout.splitlines()
        self.assertEqual([line.split()[0] for line in lines], ["student01", "student02"])

    def test_passwords_under_the_old_name_are_not_replaced(self):
        # 舊版的檔名是 pve-passwords.json。新檔名不存在時，不能悄悄產生新密碼。
        legacy = self.file.with_name("pve-passwords.json")
        legacy.write_text('{"student01": "abcd-efgh-jkmn"}')
        legacy.chmod(0o600)
        result = labctl("--env", self.env, "passwords", "new", "--file", self.file)
        self.assertEqual(result.returncode, 2)
        self.assertIn(f"mv {legacy} {self.file}", result.stderr)
        self.assertFalse(self.file.exists())

    def test_password_file_readable_by_others_is_refused(self):
        labctl("--env", self.env, "passwords", "new", "--file", self.file)
        self.file.chmod(0o644)
        result = labctl("--env", self.env, "passwords", "export", "--file", self.file)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
