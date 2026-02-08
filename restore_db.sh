#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 還原資料庫：把「已上傳的 tx_data.db」移到正確位置並重啟服務
# 用於補齊歷史回顧的 5 個交易日（VM 剛部署時 DB 是空的，只有排程抓的 2～3 天）
#
# 用法：
#   1. 在本機用 GCP SSH 視窗的「上傳檔案」把 database/tx_data.db 傳到 VM（會到你家目錄）
#   2. 在 VM 執行: chmod +x restore_db.sh && ./restore_db.sh
# ═══════════════════════════════════════════════════════════════

set -e
APP_DIR="$HOME/tx_models"
DB_DIR="$APP_DIR/database"
SERVICE_NAME="tx-signals"

# 找已上傳的 tx_data.db（可能在 ~ 或 ~/tx_models）
if [ -f "$HOME/tx_data.db" ]; then
    UPLOADED="$HOME/tx_data.db"
elif [ -f "$APP_DIR/tx_data.db" ]; then
    UPLOADED="$APP_DIR/tx_data.db"
else
    echo "找不到已上傳的 tx_data.db"
    echo "請先用 GCP SSH 視窗右上角「上傳檔案」把本機的 database/tx_data.db 傳到 VM"
    exit 1
fi

mkdir -p "$DB_DIR"
cp "$UPLOADED" "$DB_DIR/tx_data.db"
echo "已還原資料庫到 $DB_DIR/tx_data.db"
sudo systemctl restart "$SERVICE_NAME"
echo "已重啟服務。請重新整理網頁，歷史回顧應會出現 5 個交易日。"
