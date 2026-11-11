# 部署說明

每個學生在 Proxmox VE 上分到一台 Ubuntu 的 LXC 容器。容器放在主機的 NAT 網段裡，學生透過「連線方式」連進自己的容器；目前的連線方式是連接埠轉發：主機對外介面上的一個埠，對應一台容器的 SSH。

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

## 需要的東西

**PVE 主機**

- Proxmox VE 9，以 root 執行（或用可以 sudo 的帳號）。
- `python3` 和 `nftables`。缺的話腳本會提示安裝指令。產生題目要用的 `git` 沒有的話，放題目時會自動安裝。
- Ubuntu 的 LXC 樣板，先下載好：
  ```bash
  pveam update
  pveam available --section system | grep ubuntu
  pveam download local ubuntu-24.04-standard_24.04-2_amd64.tar.zst
  ```
- `CTID_START` 起連續 `STUDENT_COUNT` 個沒被使用的 CTID，以及 `PORTFORWARD_PORT_START` 起連續 `STUDENT_COUNT` 個沒被占用的埠。
- `/etc/network/interfaces` 裡有 `source /etc/network/interfaces.d/*`（PVE 預設就有）。
- 不要在主機上裝 Docker，它會把轉送的預設規則改成 DROP。

**自己的電腦**：`make`、`python3`、`ssh`，而且 ssh 得進 PVE 主機。

## 設定

所有設定都在 repo 根目錄的 `.env`，用 `make env` 從 `.env.example` 建立，`LAB_SECRET` 會自動產生。`.env` 不進 Git，有 `LAB_SECRET` 時權限必須是 600。值不要加引號、不要有空白。留白或刪掉的設定用程式的預設值，打錯名字的設定會直接報錯。

**一定要填的**

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

## 部署

在自己的電腦、repo 根目錄：

```bash
make env          # 建立 .env，再照上面填好
make dry-run      # 預覽：網路規則、每台的 CTID、位址和埠，不做任何變更
make deploy       # 建立全部，連線清單寫到 local/cards.md
```

`make deploy` 依序做這些事，每一步都可以重跑：

1. 把 `labctl/` 和 `deploy/pve/` 送到主機的 `/opt/shell-lab/pve`，`.env` 放在 `/opt/shell-lab/pve/.env`（權限 600）。
2. 在主機上建立容器網路、隔離規則和連接埠轉發，再逐台建立容器，裝好題目要用的套件、語系、時區、sshd 設定和帳號 `student`。已經存在的容器會略過。
3. 替還沒有密碼的學生產生密碼，存在本機的 `local/passwords.json`（權限 600），經 stdin 設進容器。
4. 把題目放進每台容器的 `~/lab`。已經有東西的略過，不覆蓋作業。
5. 產生 `local/cards.md`：每個人的連線指令和密碼。

發連線清單時，一人只給自己那一段，學生照[學生連線說明](../../docs/STUDENT_GUIDE.md)連線。每台建立時要從網路裝套件，人數多時要等一段時間。

### 直接在 PVE 主機上操作

不用 `make` 也可以，把 repo 放到主機上，以 root 在 repo 根目錄執行：

```bash
cp .env.example .env && chmod 600 .env    # 填好設定，LAB_SECRET 用 python3 -c 'import secrets; print(secrets.token_hex(32))' 產生
deploy/pve/shell-lab-setup.sh --dry-run
deploy/pve/shell-lab-setup.sh
mkdir -p -m 700 local
python3 -m labctl passwords new
python3 -m labctl passwords export | deploy/pve/shell-lab-setup.sh --passwords
deploy/pve/shell-lab-setup.sh --labs
deploy/pve/shell-lab-setup.sh --connect | python3 -m labctl cards
```

這樣密碼和連線清單會留在主機的 `local/` 裡，發完記得刪除。

## 日常操作

| `make` | 主機上的腳本 | 做什麼 |
|---|---|---|
| `make stop` | `--stop` | 關閉所有容器，資料保留 |
| `make start` | `--start` | 啟動所有容器 |
| `make reset-lab STUDENT=student05 LAB=05-organize` | `--labs student05 05-organize` | 只重設一題，舊的資料夾改名成 `~/lab/.05-organize.old-時間` 留著 |
| `make passwords` | `--passwords` | 替新加的學生產生密碼並設定 |
| `make labs` | `--labs` | 替新加的學生放題目 |
| `make cards` | `--connect` | 重新產生連線清單 |
| `make destroy` | `--destroy` | 刪除所有容器和主機上的網路設定，要輸入 `yes` 確認 |

**加人**：改大 `STUDENT_COUNT`，再跑 `make deploy`。已經有的容器、密碼和題目都不會變。

**減人**：先 `make destroy` 再用新的人數 `make deploy`。直接改小的話，多出來的容器不會被刪掉，而且會被隔離規則切斷網路。

**換掉一位學生的密碼**：把他從 `local/passwords.json` 刪掉，再 `make passwords` 和 `make cards`。

## 主機上會改動什麼

| 項目 | 位置 | `--destroy` |
|---|---|---|
| 每位學生一台容器 | CTID `CTID_START` 起 | 刪除，含硬碟 |
| NAT 橋接 | `/etc/network/interfaces.d/shell-lab`，只啟用這座橋接，不重新套用整份網路設定 | 刪除 |
| nftables 規則：NAT、隔離、轉發 | table `ip shell_lab_nat`、`inet shell_lab_pve`、`bridge shell_lab_l2`、`ip shell_lab_access`，檔案在 `/etc/shell-lab/` | 刪除 |
| 開機時載入規則、同步閘道 | `shell-lab-pve-network.service`、`shell-lab-pve-gateway-sync.timer`、`shell-lab-pve-access.service`，都在容器啟動前執行 | 刪除 |
| IP 轉送 | `net.ipv4.ip_forward` 打開，原本的值記在 `/etc/shell-lab/` | 設回原本的值 |
| 程式和設定 | `/opt/shell-lab/pve` | 保留 |
| `git` 套件、樣板 | — | 保留 |

規則只放在自己的 table 裡，每次整張替換，不會動到主機上其他的規則，也不需要開 PVE 的防火牆。

## 隔離

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

## 連線方式

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
| 找不到 LXC 樣板 | 照[需要的東西](#需要的東西)用 `pveam download` 下載；檔名不同的話改 `GUEST_TEMPLATE` |
| 建容器時「連不上網路」 | 確認主機本身能上網、`CT_NAMESERVER` 或主機的 DNS 可用，以及 `nft list set inet shell_lab_pve uplink_gateways` 有主機的預設閘道 |
| 學生連不進來 | 確認學生的來源 IP 在 `PORTFORWARD_SOURCES` 裡、埠沒被其他服務占用，以及 `nft list table ip shell_lab_access` 有對應的埠 |
| 學生看到 `REMOTE HOST IDENTIFICATION HAS CHANGED` | 容器重建過，主機金鑰換了。學生執行 `ssh-keygen -R "[主機]:埠"` 後再連 |
| 學生的 sudo 顯示「不在 sudoers 檔案中」 | `STUDENT_SUDO=false` 的正常結果；需要工具的話由你加進 `labctl/guest.py` 的套件清單 |
| `pct exec` 時出現 `perl: warning: Setting locale failed` | 只是警告：主機的 `LANG` 被帶進容器，容器裡沒有那個語系。自己下指令時可以加 `env LANG=C.UTF-8 LC_ALL=C.UTF-8` |
| 主機上的設定檔還在 `deploy/pve/shell-lab.env` | 舊版的位置，腳本會停下並印出要執行的 `mv` |
| 本機的密碼檔還叫 `local/pve-passwords.json` | 舊版的檔名，`labctl passwords new` 會停下並印出要執行的 `mv`，學生的密碼不會被換掉 |

## 安全注意事項

- `local/passwords.json` 和 `local/cards.md` 是明碼密碼，權限 600、不進 Git。發完連線清單就刪掉 `local/cards.md`。
- LXC 和主機共用核心，隔離比 VM 弱。容器是 unprivileged，學生預設沒有 sudo，但仍不適合拿來跑不受信任或具危害性的程式。
- 用密碼登入的 SSH 如果開放到網際網路上，會被猜密碼。`PORTFORWARD_SOURCES` 盡量只填真正會連線的網段。
