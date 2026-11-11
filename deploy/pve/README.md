# 部署說明

每個學生在 Proxmox VE 上分到一台 Ubuntu 的 LXC 容器。你在自己的電腦上執行 `make`，它透過 ssh 把程式送到 PVE 主機並在那裡執行；密碼和連線清單留在你的電腦。

- [第一次部署](#第一次部署)：從零開始，照順序做一遍
- [日常操作](#日常操作)：開關機、重設題目、加減人
- [設定項目](#設定項目)：`.env` 每個設定的意思
- [運作方式](#運作方式)：主機上會改動什麼、隔離怎麼做、連線方式
- [常見問題](#常見問題)、[安全注意事項](#安全注意事項)

## 第一次部署

### 1. 準備

**PVE 主機**

- Proxmox VE 9。
- 有 `python3` 和 `nftables`，缺的話腳本會提示安裝指令。產生題目要用的 `git`，沒有的話放題目時會自動安裝。
- 下載好 Ubuntu 的 LXC 樣板：
  ```bash
  pveam update
  pveam available --section system | grep ubuntu
  pveam download local ubuntu-24.04-standard_24.04-2_amd64.tar.zst
  ```
- `CTID_START` 起連續 `STUDENT_COUNT` 個 CTID 沒有被使用，`PORTFORWARD_PORT_START` 起連續 `STUDENT_COUNT` 個埠沒有被占用。預設是 CTID 201 起、埠 22001 起。
- `/etc/network/interfaces` 裡有 `source /etc/network/interfaces.d/*`（PVE 預設就有）。
- 不要在主機上裝 Docker，它會把轉送的預設規則改成 DROP。

**自己的電腦**（Linux、macOS 或 WSL）：`make`、`python3`、`ssh`，以及這個 repo。

### 2. 設定 ssh 金鑰登入

`make` 每個步驟都會用 ssh 連到 PVE 主機，`make deploy` 一次就要連十幾次，所以要先設定成不用輸入密碼。**以下都在自己的電腦上執行**，不是在 PVE 上。

1. 產生一把登入 PVE 用的金鑰：
   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_pve
   ```
2. 第一次連線時，確認連到的是你的主機：到 PVE 的主控台（網頁的 Shell）執行 `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`，看到的指紋要和下一步 ssh 問你的一樣，才回答 `yes`。
3. 把金鑰加到 PVE（會要你輸入一次 PVE 的 root 密碼）：
   ```bash
   ssh-copy-id -i ~/.ssh/id_ed25519_pve.pub root@PVE主機位址
   ```
4. 讓 ssh 連這台主機時自動用這把金鑰，在 `~/.ssh/config` 加上：
   ```
   Host PVE主機位址
       IdentityFile ~/.ssh/id_ed25519_pve
   ```
5. 確認不用輸入密碼就能登入：
   ```bash
   ssh root@PVE主機位址 hostname
   ```

不想用 root 登入的話，可以用其他帳號，但那個帳號要能**免密碼 sudo**：`make` 經由 ssh 執行 sudo 時，沒有地方可以輸入密碼。

### 3. 建立設定

在 repo 根目錄：

```bash
make env
```

這會從 `.env.example` 建立 `.env`，並自動產生 `LAB_SECRET`。編輯 `.env`，至少填這三項（其他項目見[設定項目](#設定項目)）：

| 變數 | 填什麼 |
|---|---|
| `PVE_SSH` | 上一步能登入的 `帳號@PVE主機位址` |
| `STUDENT_COUNT` | 人數，1 到 99。第一次可以先填 2 試試看 |
| `PORTFORWARD_SOURCES` | 允許連進容器的來源網段，例如學生所在的網段；`0.0.0.0/0` 表示不限制 |

PVE 主機用的是公網位址時，也要看一下 [`PROTECTED_NETWORKS`](#隔離)。

### 4. 預覽，再部署

```bash
make dry-run      # 只印出會做的事：網路規則、每台的 CTID、位址和埠，不做任何變更
make deploy       # 建立全部，連線清單寫到 local/cards.md
```

`make deploy` 依序做這些事，每一步都可以重跑，已經做過的會略過：

1. 把 `labctl/` 和 `deploy/pve/` 送到主機的 `/opt/shell-lab/pve`，`.env` 放在 `/opt/shell-lab/pve/.env`（權限 600）。
2. 在主機上建立容器網路、隔離規則和連接埠轉發，再逐台建立容器，裝好題目要用的套件、語系、時區、sshd 設定、帳號 `student`、第 0 題 `hello` 和登入訊息。每台建立時要從網路裝套件，人數多時要等一段時間。
3. 替還沒有密碼的學生產生密碼，存在本機的 `local/passwords.json`（權限 600），經 stdin 設進容器。
4. 把題目放進每台容器的 `~/lab`，已經有東西的略過，不覆蓋作業。
5. 產生 `local/cards.md`：每個人的連線指令和密碼。

### 5. 發連線清單

`local/cards.md` 一人只給自己那一段，學生照[學生連線說明](../../docs/STUDENT_GUIDE.md)連線。發完之後刪掉這個檔案；需要時用 `make cards` 再產生一次。

## 日常操作

| 指令 | 做什麼 |
|---|---|
| `make stop` | 關閉所有容器，資料保留 |
| `make start` | 啟動所有容器 |
| `make reset-lab STUDENT=student05 LAB=05-organize` | 只重設一題，舊的資料夾改名成 `~/lab/.05-organize.old-時間` 留著 |
| `make guest-setup` | 把容器設定重新套用到已經建好的容器，例如加了套件或更新了 `hello` 之後 |
| `make cards` | 重新產生連線清單 |
| `make destroy` | 刪除所有容器和主機上的網路設定，要輸入 `yes` 確認 |

`make` 不加參數會列出所有指令。

**加人**：改大 `STUDENT_COUNT`，再跑 `make deploy`。已經有的容器、密碼和題目都不會變。

**減人**：先 `make destroy`，再用新的人數 `make deploy`。直接改小的話，多出來的容器不會被刪掉，而且會被隔離規則切斷網路。

**換掉一位學生的密碼**：把他從 `local/passwords.json` 刪掉，再跑 `make passwords` 和 `make cards`。

### 直接在 PVE 主機上操作

不用自己的電腦也可以：把 repo 放到 PVE 主機上，以 root 在 repo 根目錄執行下面的指令。每一行對應的 `make` 指令標在後面。

```bash
cp .env.example .env && chmod 600 .env       # make env；LAB_SECRET 用 python3 -c 'import secrets; print(secrets.token_hex(32))' 產生
deploy/pve/shell-lab-setup.sh --dry-run      # make dry-run
deploy/pve/shell-lab-setup.sh                # make deploy 的第 2 步
mkdir -p -m 700 local
python3 -m labctl passwords new              # make passwords
python3 -m labctl passwords export | deploy/pve/shell-lab-setup.sh --passwords
deploy/pve/shell-lab-setup.sh --labs         # make labs；加學生和題目就是 make reset-lab
deploy/pve/shell-lab-setup.sh --guest-setup  # make guest-setup
deploy/pve/shell-lab-setup.sh --connect | python3 -m labctl cards   # make cards
deploy/pve/shell-lab-setup.sh --stop         # make stop；--start、--destroy 同理
```

這樣密碼和連線清單會留在主機的 `local/` 裡，發完記得刪除。

## 設定項目

所有設定都在 repo 根目錄的 `.env`，不進 Git；有 `LAB_SECRET` 時權限必須是 600。值不要加引號、不要有空白。留白或刪掉的設定用下表的預設值，打錯名字的設定會直接報錯。

**必填**

| 變數 | 說明 |
|---|---|
| `PVE_SSH` | 登入 PVE 主機的 `帳號@主機`，用 `make` 時需要 |
| `STUDENT_COUNT` | 人數，1 到 99。學生 ID 是 `student01` 起 |
| `PORTFORWARD_SOURCES` | 允許連入的來源網段，用逗號分隔。`0.0.0.0/0` 表示不限制。要明確填寫，避免沒注意就全開 |

**題目與容器系統**

| 變數 | 預設 | 說明 |
|---|---|---|
| `COHORT` | `shell-lab` | 代號，題目資料由它和 `LAB_SECRET` 推導 |
| `LAB_SECRET` | `make env` 產生 | 64 位十六進位。換掉的話，題目資料會跟著變 |
| `FLAG_PREFIX` | `flag` | flag 的前綴，例如 `ctf` 會得到 `ctf{...}` |
| `GUEST_OS` | `ubuntu-24.04` | `ubuntu-24.04` 或 `ubuntu-26.04` |
| `GUEST_TEMPLATE` | `ubuntu-24.04-standard_24.04-2_amd64.tar.zst` | 樣板檔名，版本要和 `GUEST_OS` 一樣 |
| `GUEST_LOCALE` | `C.UTF-8` | 例如 `zh_TW.UTF-8`，會一起裝中文的指令說明和 man page |
| `GUEST_TIMEZONE` | `UTC` | 例如 `Asia/Taipei` |
| `STUDENT_SUDO` | `false` | 學生在容器裡能不能用 sudo。題目都用不到 |
| `PROTECTED_NETWORKS` | 留白 | 另外不讓容器連的網段，見[隔離](#隔離) |

**PVE 資源與網路**

| 變數 | 預設 | 說明 |
|---|---|---|
| `TEMPLATE_STORAGE` | `local` | 樣板所在的儲存 |
| `STORAGE` | `local-lvm` | 容器根目錄的儲存 |
| `CTID_START` | `201` | 第一台的 CTID，依序加一 |
| `CT_CORES` / `CT_MEMORY_MB` / `CT_SWAP_MB` / `CT_DISK_GB` | `1` / `1024` / `512` / `8` | 每台的資源 |
| `CT_NAMESERVER` | 留白 | 容器的 DNS。留白用主機 `/etc/resolv.conf` 裡的 IPv4 伺服器 |
| `NAT_BRIDGE` | `vmbr1` | 給容器用的橋接，不能和既有的橋接同名 |
| `NAT_SUBNET` | `10.10.10.0/24` | 容器的私有網段。第一個位址給橋接，容器從第二個開始 |

**連線方式**

| 變數 | 預設 | 說明 |
|---|---|---|
| `ACCESS_MODE` | `portforward` | 目前只有這一種，見[連線方式](#連線方式) |
| `PORTFORWARD_IFACE` | `vmbr0` | 接收連線的主機介面 |
| `PORTFORWARD_ADDRESS` | 留白 | 寫在連線清單上的位址。留白取 `PORTFORWARD_IFACE` 的 IPv4；主機前面還有一層 NAT 時，填外面看得到的位址或網域 |
| `PORTFORWARD_PORT_START` | `22001` | 第一台的埠，依序加一 |

第 N 位學生（從 1 起算）：CTID 是 `CTID_START + N - 1`，埠是 `PORTFORWARD_PORT_START + N - 1`，位址是網段起點加 `N + 1`。

## 運作方式

```text
學生電腦 ──ssh──> PVE 主機 PORTFORWARD_IFACE:22001 ──DNAT──┐
                  （只接受 PORTFORWARD_SOURCES）              │
                                                             ▼
                  NAT 橋接 NAT_BRIDGE（10.10.10.1/24）
                    ├─ CT 201 lab-student01  10.10.10.2   ← 22001
                    ├─ CT 202 lab-student02  10.10.10.3   ← 22002
                    └─ ...
                  容器出去：經主機 MASQUERADE，只能走預設閘道
```

### 主機上會改動什麼

| 項目 | 位置 | `make destroy` |
|---|---|---|
| 每位學生一台容器 | CTID `CTID_START` 起 | 刪除，含硬碟 |
| NAT 橋接 | `/etc/network/interfaces.d/shell-lab`，只啟用這座橋接，不重新套用整份網路設定 | 刪除 |
| nftables 規則：NAT、隔離、轉發 | table `ip shell_lab_nat`、`inet shell_lab_pve`、`bridge shell_lab_l2`、`ip shell_lab_access`，檔案在 `/etc/shell-lab/` | 刪除 |
| 開機時載入規則、同步閘道 | `shell-lab-pve-network.service`、`shell-lab-pve-gateway-sync.timer`、`shell-lab-pve-access.service`，都在容器啟動前執行 | 刪除 |
| IP 轉送 | `net.ipv4.ip_forward` 打開，原本的值記在 `/etc/shell-lab/` | 設回原本的值 |
| 程式和設定 | `/opt/shell-lab/pve` | 保留 |
| `git` 套件、樣板 | — | 保留 |

規則只放在自己的 table 裡，每次整張替換，不會動到主機上其他的規則，也不需要開 PVE 的防火牆。

### 隔離

| 從容器連到 | 結果 |
|---|---|
| 其他學生的容器 | 擋掉。橋接層不轉送容器之間的任何封包 |
| PVE 主機本身（包括管理網頁和 ssh） | 擋掉 |
| 私有網段（10.x、172.16–31.x、192.168.x 等） | 擋掉 |
| 和主機同一個網段的機器 | 擋掉。只放行經預設閘道出去的連線 |
| `PROTECTED_NETWORKS` | 擋掉 |
| 容器的 DNS 伺服器的 53 埠 | 放行，就算它在上面被擋的網段裡 |
| 網際網路 | 放行 |
| IPv6 | 全部擋掉 |

- 每台容器只能用自己的 IP 送封包，不能冒用別台的位址搶走轉發給別人的連線。
- 閘道同步每 30 秒把主機目前的預設閘道放進規則；同步不到閘道時，容器會斷網，不會變成全開。
- **主機用公網位址時要填 `PROTECTED_NETWORKS`**：同一個網段之外、但屬於同一個內部網路的公網位址，是經預設閘道出去的，預設不會擋，要把那些網段填進去。

這些規則有測試：`tests/pve_netlab.sh` 在全新的 network namespace 裡模擬主機、容器和外部網路，實際送封包檢查。橋接層的部分需要核心支援 nftables bridge，PVE 和 CI 的核心都有。

### 連線方式

連線方式是 `deploy/pve/access/` 裡的一支腳本，`ACCESS_MODE` 決定載入哪一支。建立容器、隔離和題目都不知道學生怎麼連進來，所以換連線方式不用改它們。

| 模式 | 學生怎麼連 | 適合 |
|---|---|---|
| `portforward` | `ssh student@主機 -p 2200N` | 學生連得到 PVE 主機時 |

每支連線方式腳本要提供四個函式：

| 函式 | 做什麼 |
|---|---|
| `access_prepare` | 前置檢查，補齊執行時才知道的值 |
| `access_apply` | 在主機上建立連線需要的東西，可以重跑；`DRY_RUN=true` 時只印出來 |
| `access_remove` | 移除 `access_apply` 建立的東西 |
| `access_connect 學生ID` | 印出這位學生的連線指令，會寫進連線清單 |

要加新的模式，例如學生要從主機連不到的地方連進來時改用 overlay 網路，就新增一支 `access/<模式>.sh`，在 `labctl/pve.py` 的 `ACCESS_SETTINGS` 加上它的設定，再把 `ACCESS_MODE` 改成它。

## 常見問題

| 狀況 | 做法 |
|---|---|
| `make` 一直要輸入 PVE 的密碼 | 還沒設定金鑰登入，見[設定 ssh 金鑰登入](#2-設定-ssh-金鑰登入) |
| `Host key verification failed` | 自己的電腦還沒記下 PVE 的主機金鑰。先 `ssh root@PVE主機位址` 手動連一次，確認指紋後回答 `yes` |
| 找不到 LXC 樣板 | 照[準備](#1-準備)用 `pveam download` 下載；檔名不同的話改 `GUEST_TEMPLATE` |
| 建容器時「連不上網路」 | 確認主機本身能上網、`CT_NAMESERVER` 或主機的 DNS 可用，以及 `nft list set inet shell_lab_pve uplink_gateways` 有主機的預設閘道 |
| 學生連不進來 | 確認學生的來源 IP 在 `PORTFORWARD_SOURCES` 裡、埠沒被其他服務占用，以及 `nft list table ip shell_lab_access` 有對應的埠 |
| 學生看到 `REMOTE HOST IDENTIFICATION HAS CHANGED` | 容器重建過，主機金鑰換了。學生執行 `ssh-keygen -R "[主機]:埠"` 後再連 |
| 學生的 sudo 顯示「不在 sudoers 檔案中」 | `STUDENT_SUDO=false` 的正常結果；需要工具的話由你加進 `labctl/guest.py` 的套件清單，再 `make guest-setup` |
| `pct exec` 時出現 `perl: warning: Setting locale failed` | 只是警告：主機的 `LANG` 被帶進容器，容器裡沒有那個語系。自己下指令時可以加 `env LANG=C.UTF-8 LC_ALL=C.UTF-8` |
| 主機上的設定檔還在 `deploy/pve/shell-lab.env` | 舊版的位置，腳本會停下並印出要執行的 `mv` |
| 本機的密碼檔還叫 `local/pve-passwords.json` | 舊版的檔名，`labctl passwords new` 會停下並印出要執行的 `mv`，學生的密碼不會被換掉 |

## 安全注意事項

- `local/passwords.json` 和 `local/cards.md` 是明碼密碼，權限 600、不進 Git。發完連線清單就刪掉 `local/cards.md`。
- 登入 PVE 的金鑰等於主機的 root 權限，只放在自己的電腦，不要分享。
- LXC 和主機共用核心，隔離比 VM 弱。容器是 unprivileged，學生預設沒有 sudo，但仍不適合拿來跑不受信任或具危害性的程式。
- 用密碼登入的 SSH 如果開放到網際網路上，會被猜密碼。`PORTFORWARD_SOURCES` 盡量只填真正會連線的網段。
