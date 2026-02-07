#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# TX Models - VM 端一鍵更新腳本
# 從 GitHub 拉取最新程式碼並重啟服務
# 用法: ./update_vm.sh
# ═══════════════════════════════════════════════════════════════

set -e

APP_DIR="$HOME/tx_models"
SERVICE_NAME="tx-signals"

echo "═══════════════════════════════════════════════"
echo "  TX Models - 更新程式"
echo "═══════════════════════════════════════════════"

cd "${APP_DIR}"

# 拉取最新程式碼
echo "[1/3] 拉取最新程式碼..."
git fetch origin
git reset --hard origin/main

# 更新套件（如果 requirements.txt 有變動）
echo "[2/3] 檢查套件更新..."
source venv/bin/activate
pip install -r requirements.txt --quiet

# 重啟服務
echo "[3/3] 重啟服務..."
sudo systemctl restart ${SERVICE_NAME}

echo ""
echo "✅ 更新完成！"
echo ""
sudo systemctl status ${SERVICE_NAME} --no-pager | head -5
echo ""
echo "網頁: http://35.212.199.216:8501"
