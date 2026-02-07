#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 一鍵設定 LINE 金鑰：寫入 /etc/tx_signals/env 並重啟服務
# 用法 1（互動）：./setup_line_env.sh
# 用法 2（參數）：./setup_line_env.sh 你的Channel_ID 你的Channel_Secret
# ═══════════════════════════════════════════════════════════════

SERVICE_NAME="tx-signals"
ENV_FILE="/etc/tx_signals/env"

echo "═══════════════════════════════════════════════"
echo "  LINE 金鑰一鍵設定"
echo "═══════════════════════════════════════════════"
echo ""

if [ -n "$1" ] && [ -n "$2" ]; then
    LINE_CHANNEL_ID="$1"
    LINE_CHANNEL_SECRET="$2"
    echo "使用參數中的金鑰"
else
    echo "請到 LINE Developers 取得金鑰："
    echo "  https://developers.line.biz/console/"
    echo "  → 選你的 Provider → 選 Channel → Basic settings"
    echo ""
    read -p "請貼上 Channel ID: " LINE_CHANNEL_ID
    read -p "請貼上 Channel secret: " LINE_CHANNEL_SECRET
fi

LINE_CHANNEL_ID=$(echo "$LINE_CHANNEL_ID" | tr -d '[:space:]')
LINE_CHANNEL_SECRET=$(echo "$LINE_CHANNEL_SECRET" | tr -d '[:space:]')

if [ -z "$LINE_CHANNEL_ID" ] || [ -z "$LINE_CHANNEL_SECRET" ]; then
    echo "錯誤：Channel ID 與 Channel secret 不可為空"
    exit 1
fi

sudo mkdir -p /etc/tx_signals
sudo tee "$ENV_FILE" > /dev/null <<EOF
LINE_CHANNEL_ID=$LINE_CHANNEL_ID
LINE_CHANNEL_SECRET=$LINE_CHANNEL_SECRET
LINE_ENABLED=true
EOF
sudo chmod 600 "$ENV_FILE"

echo ""
echo "已寫入 $ENV_FILE"
echo "正在重啟服務..."
sudo systemctl restart "$SERVICE_NAME"

echo ""
echo "✅ 設定完成！若要測試 LINE 是否成功，請執行："
echo "   ./test_line.sh"
echo "═══════════════════════════════════════════════"
