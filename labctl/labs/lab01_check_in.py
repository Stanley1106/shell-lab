"""Lab 01: run whoami and hostname, and pass arguments to a program. The prompt is explained by hello."""

from labctl.guest import guest_hostname
from labctl.labs import art
from labctl.labs.answer_check import render_check

LAB_ID = "01-check-in"
TITLE = "新朋友報到"
FLAG = "whoami_is_a_deep_question"

README = """\
# 01 新朋友報到

這是你在蛛網的第一天。剛剛跟你打招呼的小壹，想先知道你的名字和住處，才能幫你做名牌。

提示字元和每一題都會用到的指令，忘了的話隨時輸入 `hello` 再看一次。

## 你要做的事

1. 輸入 `whoami`，看看你的帳號叫什麼，這就是你的名字。
2. 輸入 `hostname`，看看這台主機叫什麼，這就是你的住處。
3. 把這兩個答案當成「參數」，交給小壹的報到程式：

       ./check 帳號 主機名稱

   答對就會顯示 flag。

## 提示

- 一行指令的第一個字是「指令」，後面用空白隔開的都是「參數」。
- Linux 分大小寫：`whoami` 不能打成 `WhoAmI`。
- 指令或檔名打到一半按 Tab，會自動補完。
"""

NORMALIZE = "    return text.strip().lower()\n"
READ_ANSWER = """\
    if len(sys.argv) != 3:
        print("用法：./check 帳號 主機名稱（兩個參數，中間用空白隔開）")
        return 2
    answer = sys.argv[1] + " " + sys.argv[2]
"""


def seed(ws, flag, rng, student_id):
    ws.write("README.md", README)
    answer = f"student {guest_hostname(student_id)}"
    salt = format(rng.getrandbits(64), "016x")
    ws.write(
        "check",
        render_check(
            flag,
            answer,
            salt,
            "報到：./check 帳號 主機名稱",
            NORMALIZE,
            READ_ANSWER,
            "小壹查了查名冊，對不上喔。用 whoami 和 hostname 再確認一次。",
            art.render(LAB_ID),
        ),
        mode=0o755,
    )
