"""What every student's Linux environment gets: packages, sshd settings, locale and host name."""

PACKAGES = [
    # 映像只有最小系統（ubuntu-minimal），ubuntu-standard 補上一般 Ubuntu Server 的常用工具。
    "ubuntu-standard",
    "openssh-server",
    "tree",
    "unzip",
    "xxd",  # 看檔案的位元組（「檔案格式」一章示範用），vim 只把它列為建議套件
    "man-db",
    "vim",
    "git",
    "less",
    "file",
    "python3",
    "curl",
    "ca-certificates",
    "gnupg",
]

# 繁體中文的 --help（gettext 翻譯）與 man page，GUEST_LOCALE 是 zh_TW 時才裝。
CHINESE_PACKAGES = ["language-pack-zh-hant", "manpages-zh"]

# Ubuntu 26.04 預設的 coreutils 是 uutils（Rust 版），ls、cp、chmod 等的 --help 和錯誤訊息只有英文。
# 換回 GNU coreutils 才會用語言包的中文翻譯（24.04 本來就是 GNU 版）。coreutils-from-uutils 標成 Protected，
# packages 清單移不掉它，所以要明確移除，而且要加 --allow-remove-essential。
# apt 可能還被自動更新占用，Lock::Timeout 讓它等鎖，不會直接失敗。
SWITCH_TO_GNU_COREUTILS = [
    "env",
    "DEBIAN_FRONTEND=noninteractive",
    "apt-get",
    "install",
    "-y",
    "-o",
    "DPkg::Lock::Timeout=300",
    "--allow-remove-essential",
    "coreutils-from-gnu",
    "coreutils-from-uutils-",
]


def guest_hostname(sid):
    """Host name inside the student's environment, shown in the prompt and checked by lab 01."""
    return f"lab-{sid}"


def sshd_dropin():
    # 放在 00- 開頭：sshd 對同一設定採第一次出現的值，優先於其他 drop-in。
    return (
        "\n".join(
            [
                "# Managed by labctl.",
                "PermitRootLogin no",
                "PasswordAuthentication yes",
                "KbdInteractiveAuthentication no",
                "AllowUsers student",
                "DisableForwarding yes",
                "PermitTunnel no",
                "PermitUserRC no",
            ]
        )
        + "\n"
    )


def locale_profile(locale):
    if locale.startswith("zh_TW"):
        lines = [
            "# 學生登入時顯示繁體中文。要看英文原文可執行：export LANG=C.UTF-8 LANGUAGE=",
            f"export LANG={locale}",
            "export LANGUAGE=zh_TW:zh",
        ]
    else:
        lines = ["# 學生登入時的語系（.env 的 GUEST_LOCALE）。", f"export LANG={locale}"]
    return "\n".join(lines) + "\n"
