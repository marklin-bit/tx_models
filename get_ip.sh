#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 查詢此 VM 的目前外部 IP（GCP 臨時 IP 可能重開後變動）
# 用法: chmod +x get_ip.sh && ./get_ip.sh
# ═══════════════════════════════════════════════════════════════

IP=$(curl -s -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip 2>/dev/null)

if [ -z "$IP" ]; then
    echo "無法取得外部 IP（可能非 GCP VM 或網路異常）"
    exit 1
fi

echo ""
echo "此 VM 目前的外部 IP: $IP"
echo "網頁入口: http://${IP}:8501"
echo ""
echo "若 IP 已變動，請用上面網址開啟網頁。"
echo ""
