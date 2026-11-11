# shell-lab

「Linux 常用指令」課程用的實驗環境。每個學生在 Proxmox VE 上分到一台自己的 Ubuntu 容器，用 ssh 連進去做 13 道題目，解開會拿到 flag。

```text
學生電腦 ──ssh──> PVE 主機:2200N ──轉發──> 自己的容器
                                          ├─ 容器之間互相連不到
                                          ├─ 連不到 PVE 主機和內部網段
                                          └─ 可以經主機上網
```

- **一人一台**：每台容器有自己的帳號、密碼和題目資料。
- **彼此隔離**：容器之間、容器到主機和內部網段的連線都被擋下。
- **從自己的電腦操作**：`make` 透過 ssh 在 PVE 主機上執行，密碼和連線清單留在自己的電腦。

## 快速開始

需要一台 Proxmox VE 9 主機，以及一台有 `make`、`python3`、`ssh` 的電腦。

1. 在自己的電腦設定好用金鑰登入 PVE 主機，不用輸入密碼（[做法](deploy/pve/README.md#2-設定-ssh-金鑰登入)）。
2. 在這個 repo 裡：
   ```bash
   make env          # 建立 .env，再填 PVE_SSH、STUDENT_COUNT、PORTFORWARD_SOURCES
   make dry-run      # 預覽會做的事
   make deploy       # 建容器、設密碼、放題目，連線清單寫到 local/cards.md
   ```
3. 把 `local/cards.md` 裡每個人的那一段發給學生。

完整步驟、設定和日常操作見[部署說明](deploy/pve/README.md)。打 `make` 可以看到全部的指令。

## 文件

- [部署說明](deploy/pve/README.md)：第一次部署、日常操作、設定項目、運作方式、常見問題
- [學生連線說明](docs/STUDENT_GUIDE.md)：可以直接發給學生
- [題目](docs/LABS.md)：每題在練什麼、答案、資料怎麼產生、怎麼改題目
- [開發](CONTRIBUTING.md)：測試和檢查

## 授權

[MIT](LICENSE)。答對時印出的蜘蛛是參考 is1ab 的社團 logo 畫的。

本專案改作自 TTUSSC 的 [ttussc-shell-lab](https://github.com/Jerry080401/ttussc-shell-lab)，依 MIT 授權保留原作者的版權和授權聲明：

```text
MIT License

Copyright (c) 2026 Jerry Fang
Copyright (c) 2026 Stanley Chen

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
