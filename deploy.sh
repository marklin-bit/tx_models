#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# TX Models - Google Cloud VM 一鍵部署腳本
# 
# 用法 A (從 GitHub 部署):
#   curl -sL https://raw.githubusercontent.com/你的帳號/tx_models/main/deploy.sh | bash -s -- --repo https://github.com/你的帳號/tx_models.git
#
# 用法 B (檔案已在本機):
#   chmod +x deploy.sh && ./deploy.sh
# ═══════════════════════════════════════════════════════════════

set -e

APP_DIR="$HOME/tx_models"
SERVICE_NAME="tx-signals"
PYTHON_VERSION="3.11"
REPO_URL=""

# 解析參數
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --repo) REPO_URL="$2"; shift ;;
    esac
    shift
done

echo "═══════════════════════════════════════════════════"
echo "  TX 台指期訊號監控系統 - VM 部署"
echo "═══════════════════════════════════════════════════"
echo ""

# ─── Step 1: 系統更新 & 安裝 Python + Git ───
echo "[1/7] 更新系統 & 安裝 Python ${PYTHON_VERSION}..."

# Debian 用系統 Python；Ubuntu 用 deadsnakes PPA。若先前誤加 PPA 在 Debian 上會 404，先移除
if [ -f /etc/os-release ] && grep -q '^ID=debian' /etc/os-release; then
    sudo rm -f /etc/apt/sources.list.d/deadsnakes-ubuntu-ppa-*.list 2>/dev/null || true
fi

sudo apt-get update -y

if [ -f /etc/os-release ] && grep -q '^ID=debian' /etc/os-release; then
    echo "  偵測到 Debian，使用系統套件庫..."
    sudo apt-get install -y git python${PYTHON_VERSION} python${PYTHON_VERSION}-venv python${PYTHON_VERSION}-dev python3-pip curl
else
    echo "  偵測到 Ubuntu，使用 deadsnakes PPA..."
    sudo apt-get install -y software-properties-common git python3-launchpadlib
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    sudo apt-get update -y
    sudo apt-get install -y python${PYTHON_VERSION} python${PYTHON_VERSION}-venv python${PYTHON_VERSION}-dev python3-pip curl
fi

echo "  Python: $(python${PYTHON_VERSION} --version)"
echo "  Git:    $(git --version)"

# ─── Step 2: 取得/更新專案程式碼 ───
echo ""
echo "[2/7] 設定專案目錄..."

if [ -n "$REPO_URL" ]; then
    # 從 GitHub 克隆
    if [ -d "${APP_DIR}/.git" ]; then
        echo "  專案已存在，更新中..."
        cd "${APP_DIR}"
        git fetch origin
        git reset --hard origin/main
    else
        echo "  從 GitHub 克隆: ${REPO_URL}"
        git clone "$REPO_URL" "${APP_DIR}"
        cd "${APP_DIR}"
    fi
else
    # 使用本機檔案
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    if [ "$SCRIPT_DIR" != "$APP_DIR" ]; then
        mkdir -p "${APP_DIR}"
        echo "  複製檔案到 ${APP_DIR}..."
        rsync -av --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' \
              "${SCRIPT_DIR}/" "${APP_DIR}/"
    fi
    cd "${APP_DIR}"
fi

mkdir -p "${APP_DIR}/database"
echo "  專案目錄: ${APP_DIR}"

# ─── Step 3: 建立虛擬環境 & 安裝套件 ───
echo ""
echo "[3/7] 建立 Python 虛擬環境..."

if [ ! -d "${APP_DIR}/venv" ]; then
    python${PYTHON_VERSION} -m venv venv
fi
source venv/bin/activate

echo "  安裝 Python 套件..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

echo "  已安裝套件:"
pip list --format=columns 2>/dev/null | grep -iE "streamlit|pandas|numpy|xgboost|plotly|requests|line-bot" || true

# ─── Step 4: 驗證模型檔案 ───
echo ""
echo "[4/7] 驗證模型檔案..."
MODEL_COUNT=$(ls -1 "${APP_DIR}"/*.json 2>/dev/null | grep -cE "(Long|Short)" || echo "0")
echo "  找到 ${MODEL_COUNT} 個模型檔案"

if [ "$MODEL_COUNT" -lt 20 ]; then
    echo "  ⚠ 警告: 預期 20 個模型，只找到 ${MODEL_COUNT} 個！"
fi

# ─── Step 5: 驗證資料庫 ───
echo ""
echo "[5/7] 驗證資料庫..."
if [ -f "${APP_DIR}/database/tx_data.db" ]; then
    DB_SIZE=$(du -h "${APP_DIR}/database/tx_data.db" | cut -f1)
    echo "  資料庫存在: ${DB_SIZE}"
else
    echo "  資料庫不存在，首次啟動時會自動建立"
fi

# ─── Step 6: 設定 update_vm.sh 權限 ───
echo ""
echo "[6/7] 設定更新腳本權限..."
if [ -f "${APP_DIR}/update_vm.sh" ]; then
    chmod +x "${APP_DIR}/update_vm.sh"
    echo "  update_vm.sh 已設定可執行"
fi

# ─── Step 7: 建立 systemd 服務 ───
echo ""
echo "[7/7] 設定系統服務 (開機自啟動)..."

sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<SERVICEEOF
[Unit]
Description=TX Futures Signal Monitor (Streamlit)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$(whoami)
Group=$(id -gn)
WorkingDirectory=${APP_DIR}
Environment="PATH=${APP_DIR}/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="HOME=${HOME}"
ExecStart=${APP_DIR}/venv/bin/streamlit run app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
MemoryMax=2G

[Install]
WantedBy=multi-user.target
SERVICEEOF

sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}

# 開放 port
sudo iptables -C INPUT -p tcp --dport 8501 -j ACCEPT 2>/dev/null || \
    sudo iptables -I INPUT -p tcp --dport 8501 -j ACCEPT

echo ""
echo "═══════════════════════════════════════════════════"
echo "  ✅ 部署完成！"
echo "═══════════════════════════════════════════════════"
echo ""
echo "  啟動:  sudo systemctl start ${SERVICE_NAME}"
echo "  狀態:  sudo systemctl status ${SERVICE_NAME}"
echo "  LOG:   sudo journalctl -u ${SERVICE_NAME} -f"
echo "  更新:  cd ~/tx_models && ./update_vm.sh"
echo ""
echo "  網頁:  http://35.212.199.216:8501"
echo ""
echo "  ⚠ 確保 GCP 防火牆已開放 TCP:8501"
echo "═══════════════════════════════════════════════════"
