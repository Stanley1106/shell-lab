# 每個步驟一個指令。`make` 會列出所有指令。
SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c
.DEFAULT_GOAL := help

PYTHON ?= python3

.PHONY: help pve-env pve-check pve-upload pve-dry-run pve pve-passwords pve-labs pve-reset-lab pve-cards pve-stop \
	pve-start pve-destroy test lint fmt

help: ## 列出所有指令
	@grep -E '^[a-z-]+:.*## ' $(firstword $(MAKEFILE_LIST)) | awk -F':.*## ' '{printf "  make %-12s %s\n", $$1, $$2}'

# 設定在 deploy/pve/shell-lab.env。把腳本和設定送到 PVE 主機，以 root 執行（PVE_SSH 不是 root 時用 sudo）。
PVE_ENV ?= deploy/pve/shell-lab.env
PVE_DIR ?= /opt/shell-lab/pve
pve_get = $(shell sed -n 's/^$(1)=//p' $(PVE_ENV) 2>/dev/null)
PVE_SSH := $(call pve_get,PVE_SSH)
LABCTL_PVE := $(PYTHON) -m labctl --env $(PVE_ENV)
PVE_ROOT := s=; [ \$$(id -u) = 0 ] || s=sudo; \$$s
PVE_SETUP := $(PVE_ROOT) $(PVE_DIR)/deploy/pve/shell-lab-setup.sh
PVE_PASSWORDS := local/pve-passwords.json
PVE_CARDS := local/pve-cards.md

# 密碼存在本機（權限 600），經 ssh 的 stdin 送到主機，再經 stdin 設進容器。
define pve_set_passwords
	$(LABCTL_PVE) pve passwords-new --file $(PVE_PASSWORDS)
	$(LABCTL_PVE) pve passwords-export --file $(PVE_PASSWORDS) | ssh $(PVE_SSH) "$(PVE_SETUP) --passwords"
endef

define pve_write_cards
	ssh $(PVE_SSH) "$(PVE_SETUP) --connect" | $(LABCTL_PVE) pve cards --passwords $(PVE_PASSWORDS) --out $(PVE_CARDS)
endef

pve-env: ## 從範例建立 deploy/pve/shell-lab.env，LAB_SECRET 自動產生
	@if [ -e $(PVE_ENV) ]; then echo "$(PVE_ENV) already exists, not touched"; exit 0; fi; \
	umask 077; \
	secret=$$($(PYTHON) -c 'import secrets; print(secrets.token_hex(32))'); \
	sed "s/^LAB_SECRET=$$/LAB_SECRET=$$secret/" deploy/pve/shell-lab.env.example >$(PVE_ENV); \
	echo "created $(PVE_ENV), fill it in and run: make pve-dry-run"

pve-check:
	@[ -f $(PVE_ENV) ] || { echo "$(PVE_ENV) not found, create it with: make pve-env" >&2; exit 1; }
	@[ -n "$(PVE_SSH)" ] || { echo "set PVE_SSH in $(PVE_ENV)" >&2; exit 1; }
	@mkdir -p -m 700 local
	@$(LABCTL_PVE) pve check

# 送 labctl 和腳本，保持 repo 的目錄結構。主機上的設定檔在 deploy/pve，不會被覆蓋。
pve-upload: pve-check
	tar -cz --exclude=__pycache__ labctl deploy/pve/shell-lab-setup.sh deploy/pve/access | ssh $(PVE_SSH) \
		"$(PVE_ROOT) sh -c 'mkdir -p -m 700 $(PVE_DIR) && rm -rf $(PVE_DIR)/labctl $(PVE_DIR)/deploy/pve/access && tar -xz --no-same-owner -C $(PVE_DIR)'"
	ssh $(PVE_SSH) "$(PVE_ROOT) sh -c 'umask 077 && cat >$(PVE_DIR)/deploy/pve/shell-lab.env'" <$(PVE_ENV)

pve-dry-run: pve-upload ## 預覽會做的事，不做任何變更
	ssh $(PVE_SSH) "$(PVE_SETUP) --dry-run"

pve: pve-upload ## 建立全部、設定密碼、放題目，連線清單寫到 local/pve-cards.md
	ssh $(PVE_SSH) "$(PVE_SETUP)"
	$(pve_set_passwords)
	ssh $(PVE_SSH) "$(PVE_SETUP) --labs"
	$(pve_write_cards)

pve-passwords: pve-upload ## 替還沒有密碼的學生產生密碼，並設定到每台容器
	$(pve_set_passwords)

pve-labs: pve-upload ## 把題目放進每台容器，~/lab 已經有東西的跳過
	ssh $(PVE_SSH) "$(PVE_SETUP) --labs"

pve-reset-lab: pve-upload ## 重設一位學生的一題：make pve-reset-lab STUDENT=student05 LAB=05-organize
	@[[ "$(STUDENT)" =~ ^student[0-9]{2}$$ && "$(LAB)" =~ ^[0-9]{2}-[a-z0-9-]+$$ ]] || \
		{ echo "usage: make pve-reset-lab STUDENT=student05 LAB=05-organize" >&2; exit 2; }
	ssh $(PVE_SSH) "$(PVE_SETUP) --labs $(STUDENT) $(LAB)"

pve-cards: pve-upload ## 全部學生的連線指令和密碼，寫到 local/pve-cards.md
	$(pve_write_cards)

pve-stop: pve-upload ## 關閉所有容器（保留）
	ssh $(PVE_SSH) "$(PVE_SETUP) --stop"

pve-start: pve-upload ## 啟動所有容器
	ssh $(PVE_SSH) "$(PVE_SETUP) --start"

pve-destroy: pve-upload ## 刪除所有容器和轉發規則（要輸入 yes 確認），密碼檔保留
	ssh -t $(PVE_SSH) "$(PVE_SETUP) --destroy"

test: ## 跑測試
	$(PYTHON) -m unittest discover -s tests -t .

lint: ## 檢查程式格式
	ruff check .
	ruff format --check .
	shellcheck -x tests/*.sh deploy/pve/*.sh deploy/pve/access/*.sh

fmt: ## 自動整理程式格式
	ruff check --fix .
	ruff format .
