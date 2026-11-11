# 學生連線說明

每個人都有一台自己的 Linux（Ubuntu），用 **SSH** 從自己的電腦登入。只需要電腦內建的 ssh，不用另外安裝軟體。

需要：自己的電腦（Windows 10／11、macOS 或 Linux）。

## 課前準備：確認電腦有 ssh

**Windows**：開始 → 輸入 `Windows PowerShell` → 開啟，輸入：

```powershell
ssh -V
```

看到 `OpenSSH_for_Windows_...` 就可以了（Windows 10、11 內建）。
如果出現「無法辨識」：設定 → 系統 → 選用功能 → 新增功能（檢視功能）→ 搜尋 **OpenSSH 用戶端** → 安裝，裝完關掉 Windows PowerShell 再開一次。

**macOS**：開啟「終端機」，輸入 `ssh -V`（內建）。

**Linux**：開終端機輸入 `ssh -V`，沒有的話安裝 `openssh-client`。

## 上課時：登入你的 Linux

老師會私下給你一段**連線資訊**：一行連線指令和你的密碼。連線資訊只給你一個人，不要拍照傳到群組。

打開 Windows PowerShell（macOS／Linux 用終端機），把連線指令**整行複製貼上**。它長得像這樣（下面是範例，每個人的埠號不同）：

```powershell
ssh student@203.0.113.10 -p 22005
```

- `student` 是帳號，每個人都一樣。
- `-p` 後面的數字是你自己的埠號，決定連到哪一台。打錯就會連到別人的、登不進去。

1. 第一次連線會問 `Are you sure you want to continue connecting (yes/no)?`，輸入 `yes`。
2. 輸入密碼。**打字時畫面不會顯示任何東西，這是正常的**，打完按 Enter。
3. 看到 `student@lab-studentXX:~$` 就登入成功了。題目在 `~/lab`：輸入 `cat ~/lab/README.md` 開始。

離開：輸入 `exit`。下次上課再執行同一行連線指令就好。

## 常見問題

| 狀況 | 怎麼辦 |
|---|---|
| 輸入密碼看不到字 | 正常，直接打完按 Enter |
| `Permission denied` | 密碼打錯，注意大小寫；或 `-p` 的埠號不是你的。連續錯很多次請找老師 |
| `Connection timed out`、`Connection refused` | 確認你的網路連得到老師給的位址，例如在上課的網路環境裡。還是不行請找老師 |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | 你的 Linux 被老師重建過。找老師確認，**不要自己隨便刪設定** |
| 中文變成亂碼 | Windows 請用「Windows 終端機」（Windows 11 內建）開 Windows PowerShell |
| 想看英文原文的說明 | 在你的 Linux 裡輸入 `export LANG=C.UTF-8 LANGUAGE=` |
| `sudo` 說「不在 sudoers 檔案中」 | 這台 Linux 預設不能用 `sudo`，題目都用不到。需要什麼工具請找老師 |

如果把自己的 Linux 弄壞了也沒關係，告訴老師，老師可以幫你重建一台新的。
