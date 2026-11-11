"""Render per-VM cloud-init user-data from a planned instance.

The output contains no passwords, keys or setup keys: user-data stays readable
inside the guest. Credentials are set later over stdin by the host tooling.
"""

import json

from labctl.guest import CHINESE_PACKAGES, PACKAGES, SWITCH_TO_GNU_COREUTILS, locale_profile, sshd_dropin
from labctl.labs.lab05_organize import RM_GUARD


def render_user_data(instance):
    """Return the #cloud-config document for one planned instance."""
    locale = instance["locale"]
    packages = PACKAGES + (CHINESE_PACKAGES if locale.startswith("zh_TW") else [])
    student = {"name": "student", "shell": "/bin/bash", "lock_passwd": True}
    if instance["sudo"]:
        # 跟一般 Ubuntu 一樣：加入 sudo 群組，使用 sudo 時輸入自己的密碼（不設 NOPASSWD）。
        student["groups"] = ["sudo"]
    doc = {
        "hostname": instance["hostname"],
        "manage_etc_hosts": True,
        "locale": locale,
        "timezone": instance["timezone"],
        # 不含 "default"：不建立映像預設的 ubuntu 帳號。
        "users": [student],
        "disable_root": True,
        "ssh_pwauth": True,
        "bootcmd": [["rm", "-f", "/etc/dpkg/dpkg.cfg.d/excludes"]],
        "package_update": True,
        "packages": packages,
        "write_files": [
            {
                "path": "/etc/ssh/sshd_config.d/00-shell-lab.conf",
                "owner": "root:root",
                "permissions": "0644",
                "content": sshd_dropin(),
            },
            {
                "path": "/etc/profile.d/shell-lab-locale.sh",
                "owner": "root:root",
                "permissions": "0644",
                "content": locale_profile(locale),
            },
            {
                "path": "/etc/profile.d/shell-lab-rm.sh",
                "owner": "root:root",
                "permissions": "0644",
                "content": RM_GUARD,
            },
        ],
        # runcmd 在套件安裝之後才執行。
        "runcmd": [
            *([SWITCH_TO_GNU_COREUTILS] if instance["guest_os"] == "ubuntu-26.04" else []),
            ["install", "-d", "-m", "0700", "-o", "student", "-g", "student", "/home/student/lab"],
            ["sh", "-c", "/usr/sbin/sshd -t && systemctl restart ssh"],
        ],
    }
    # JSON 是合法的 YAML。用 json.dumps 產生，避免手寫 YAML 的引號與縮排錯誤。
    return "#cloud-config\n" + json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
