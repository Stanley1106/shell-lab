# 每個步驟一個指令，設定全部在 .env。`make` 會列出所有指令。
# 程式和設定送到 PVE 主機的 PVE_DIR，以 root 執行（PVE_SSH 不是 root 時用 sudo）。
SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c
.DEFAULT_GOAL := help

ENV ?= .env
PYTHON ?= python3
LABCTL := $(PYTHON) -m labctl --env $(ENV)
PVE_DIR ?= /opt/shell-lab/pve
PVE_SSH := $(shell sed -n 's/^PVE_SSH=//p' $(ENV) 2>/dev/null)
ON_PVE := s=; [ \$$(id -u) = 0 ] || s=sudo; \$$s
SETUP := $(ON_PVE) $(PVE_DIR)/deploy/pve/shell-lab-setup.sh
PASSWORDS := local/passwords.json
CARDS := local/cards.md

.PHONY: help env check upload dry-run deploy passwords labs reset-lab guest-setup cards stop start destroy test lint \
	fmt

help: ## 列出所有指令
	@grep -E '^[a-z-]+:.*## ' $(firstword $(MAKEFILE_LIST)) | awk -F':.*## ' '{printf "  make %-12s %s\n", $$1, $$2}'

# 密碼存在本機（權限 600），經 ssh 的 stdin 送到主機，再經 stdin 設進容器。
define set_passwords
	$(LABCTL) passwords new --file $(PASSWORDS)
	$(LABCTL) passwords export --file $(PASSWORDS) | ssh $(PVE_SSH) "$(SETUP) --passwords"
endef

# 連線指令由主機上的連線方式產生，在本機合併密碼。
define write_cards
	ssh $(PVE_SSH) "$(SETUP) --connect" | $(LABCTL) cards --passwords $(PASSWORDS) --out $(CARDS)
endef

env: ## 從 .env.example 建立 .env，LAB_SECRET 自動產生
	@if [ -e $(ENV) ]; then echo "$(ENV) already exists, not touched"; exit 0; fi; \
	umask 077; \
	secret=$$($(PYTHON) -c 'import secrets; print(secrets.token_hex(32))'); \
	sed "s/^LAB_SECRET=$$/LAB_SECRET=$$secret/" .env.example >$(ENV); \
	echo "created $(ENV), fill it in and run: make dry-run"

check: ## 檢查 .env
	@[ -f $(ENV) ] || { echo "$(ENV) not found, create it with: make env" >&2; exit 1; }
	@[ -n "$(PVE_SSH)" ] || { echo "set PVE_SSH in $(ENV)" >&2; exit 1; }
	@mkdir -p -m 700 local
	@$(LABCTL) check

# 送 labctl 和腳本，保持 repo 的目錄結構，設定放在 $(PVE_DIR)/.env。
upload: check
	tar -cz --exclude=__pycache__ labctl deploy/pve/shell-lab-setup.sh deploy/pve/access | ssh $(PVE_SSH) \
		"$(ON_PVE) sh -c 'mkdir -p -m 700 $(PVE_DIR) && rm -rf $(PVE_DIR)/labctl $(PVE_DIR)/deploy/pve/access && tar -xz --no-same-owner -C $(PVE_DIR)'"
	ssh $(PVE_SSH) "$(ON_PVE) sh -c 'umask 077 && cat >$(PVE_DIR)/.env'" <$(ENV)

dry-run: upload ## 預覽會做的事，不做任何變更
	ssh $(PVE_SSH) "$(SETUP) --dry-run"

deploy: upload ## 建立全部、設定密碼、放題目，連線清單寫到 local/cards.md
	ssh $(PVE_SSH) "$(SETUP)"
	$(set_passwords)
	ssh $(PVE_SSH) "$(SETUP) --labs"
	$(write_cards)

passwords: upload ## 替還沒有密碼的學生產生密碼，並設定到每台容器
	$(set_passwords)

labs: upload ## 把題目放進每台容器，~/lab 已經有東西的跳過
	ssh $(PVE_SSH) "$(SETUP) --labs"

reset-lab: upload ## 重設一位學生的一題：make reset-lab STUDENT=student05 LAB=05-organize
	@[[ "$(STUDENT)" =~ ^student[0-9]{2}$$ && "$(LAB)" =~ ^[0-9]{2}-[a-z0-9-]+$$ ]] || \
		{ echo "usage: make reset-lab STUDENT=student05 LAB=05-organize" >&2; exit 2; }
	ssh $(PVE_SSH) "$(SETUP) --labs $(STUDENT) $(LAB)"

guest-setup: upload ## 把容器設定（套件、hello、登入訊息等）重新套用到已經建好的容器
	ssh $(PVE_SSH) "$(SETUP) --guest-setup"

cards: upload ## 全部學生的連線指令和密碼，寫到 local/cards.md
	$(write_cards)

stop: upload ## 關閉所有容器（保留）
	ssh $(PVE_SSH) "$(SETUP) --stop"

start: upload ## 啟動所有容器
	ssh $(PVE_SSH) "$(SETUP) --start"

destroy: upload ## 刪除所有容器和主機上的網路設定（要輸入 yes 確認），密碼檔保留
	ssh -t $(PVE_SSH) "$(SETUP) --destroy"

test: ## 跑測試
	$(PYTHON) -m unittest discover -s tests -t .

lint: ## 檢查程式格式
	ruff check .
	ruff format --check .
	shellcheck -x tests/*.sh deploy/pve/*.sh deploy/pve/access/*.sh

fmt: ## 自動整理程式格式
	ruff check --fix .
	ruff format .
