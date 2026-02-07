#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 網頁打不開時，在 VM 上執行此腳本協助診斷
# 用法: chmod +x check_web.sh && ./check_web.sh
# ═══════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════"
echo "  TX 網頁連線診斷"
echo "═══════════════════════════════════════════════════"
echo ""

# 1. 服務是否在跑
echo "[1] 服務狀態 (tx-signals):"
if systemctl is-active --quiet tx-signals 2>/dev/null; then
    echo "    ✓ 服務正在運行"
else
    echo "    ✗ 服務未運行！請執行: sudo systemctl start tx-signals"
    echo "    查看日誌: sudo journalctl -u tx-signals -n 30"
fi
echo ""

# 2. 是否有程式在聽 8501
echo "[2] 埠 8501 是否被監聽:"
if command -v ss >/dev/null 2>&1; then
    ss -tlnp 2>/dev/null | grep 8501 || echo "    無程式監聽 8501"
else
    netstat -tlnp 2>/dev/null | grep 8501 || echo "    無程式監聽 8501"
fi
echo ""

# 3. 監聽的位址 (0.0.0.0 才能從外部連)
echo "[3] 監聽位址 (應為 0.0.0.0:8501 才能從外網連):"
ss -tlnp 2>/dev/null | grep 8501 || true
echo ""

# 4. 本機 curl 測試
echo "[4] 本機連線測試 (curl localhost:8501):"
if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 http://127.0.0.1:8501 2>/dev/null | grep -q 200; then
    echo "    ✓ 本機可連線 (HTTP 200)"
else
    echo "    ✗ 本機無法連線 (服務可能未啟動或只聽 127.0.0.1)"
fi
echo ""

# 5. 外部 IP
echo "[5] 此 VM 的對外 IP (請用瀏覽器開 http://此IP:8501):"
curl -s -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip 2>/dev/null || echo "    (非 GCP 或無法取得)"
echo ""

# 6. GCP 防火牆提醒
echo "[6] 若本機可連但外網不行，請檢查 GCP 防火牆:"
echo "    - GCP Console → VPC 網路 → 防火牆"
echo "    - 需有「輸入」規則允許 tcp:8501，來源 0.0.0.0/0"
echo "    - 目標：若設「指定標籤」，你的 VM 必須有該網路標籤"
echo ""

echo "═══════════════════════════════════════════════════"
