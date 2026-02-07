#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# LINE 通知測試：從 /etc/tx_signals/env 讀取金鑰並發送測試訊息
# 用法: chmod +x test_line.sh && ./test_line.sh
# ═══════════════════════════════════════════════════════════════

set -e
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

# 從 /etc/tx_signals/env 讀取金鑰（需 sudo）
if [ -f /etc/tx_signals/env ]; then
    export LINE_CHANNEL_ID=$(sudo grep '^LINE_CHANNEL_ID=' /etc/tx_signals/env 2>/dev/null | cut -d= -f2- | tr -d '\r')
    export LINE_CHANNEL_SECRET=$(sudo grep '^LINE_CHANNEL_SECRET=' /etc/tx_signals/env 2>/dev/null | cut -d= -f2- | tr -d '\r')
fi

if [ -z "$LINE_CHANNEL_ID" ] || [ -z "$LINE_CHANNEL_SECRET" ]; then
    echo "錯誤：找不到 LINE 金鑰。請先執行 setup_line_env.sh 或編輯 /etc/tx_signals/env"
    exit 1
fi

source venv/bin/activate
python -c "
import os
from core.line_notifier import LineNotifier
cid = os.environ.get('LINE_CHANNEL_ID', '')
secret = os.environ.get('LINE_CHANNEL_SECRET', '')
if not cid or not secret:
    print('錯誤：環境變數 LINE_CHANNEL_ID / LINE_CHANNEL_SECRET 未設定')
    exit(1)
n = LineNotifier(cid, secret)
ok = n.send_test()
if ok:
    print('')
    print('LINE 測試成功！請檢查手機是否收到測試訊息。')
else:
    print('')
    print('LINE 測試失敗，請檢查金鑰是否正確、網路是否正常。')
exit(0 if ok else 1)
"
