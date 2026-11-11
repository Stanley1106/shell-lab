"""第 0 題：學生登入後輸入 hello，小壹出來打招呼，介紹提示字元和每一題都會用到的指令。

不在 ~/lab 裡，也沒有 flag。它裝成容器裡的 /usr/local/bin/hello，學生登入後不用先學 cd 就能執行，
做完就知道怎麼走進 ~/lab 開始第 1 題。
"""

from labctl.labs import art

# 在學生的終端機裡印出來，不是 Markdown。{prompt}、{user}、{host} 在執行時換成學生自己的。
GREETING = """\
你好！我是小壹，這片蛛網的接待員。歡迎你來！

你剛剛執行了第一個指令：hello。畫面最左邊的這一串叫「提示字元」：

    {prompt}

  {user}：你的帳號
  {host}：這台主機的名稱
  ~：你現在所在的位置，~ 代表你的家目錄
  $：表示你是一般使用者，管理員 root 的提示字元結尾是 #

看到提示字元，就表示可以輸入指令了。每一題都會用到這幾個：

  ls          看看這裡有什麼
  cd 資料夾   走進資料夾，cd .. 回到上一層
  pwd         顯示你現在在哪裡
  cat 檔案    讀檔案的內容
  ./程式      執行這裡的程式，./ 的意思是「就在這裡」

題目放在 lab 資料夾裡，一題一個小資料夾。從這裡開始：

    cd ~/lab
    cat README.md

忘了這些的話，隨時再輸入 hello。
"""

SCRIPT = '''\
#!/usr/bin/env python3
"""shell-lab 第 0 題：小壹打招呼。由 labctl 產生。"""
import getpass
import socket

SPIDER = {spider!r}
GREETING = {greeting!r}

user, host = getpass.getuser(), socket.gethostname()
print(SPIDER)
print(GREETING.format(prompt=f"{{user}}@{{host}}:~$", user=user, host=host), end="")
'''


def render_script():
    """The /usr/local/bin/hello program, the same for every student."""
    return SCRIPT.format(spider=art.spider(), greeting=GREETING)
