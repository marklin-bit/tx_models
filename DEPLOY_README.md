# TX Models - VM 部署與更新說明

## GitHub 儲存庫

- **私人 repo**: https://github.com/marklin-bit/tx_models
- **分支**: `main`

---

## 一、VM 首次部署（從 GitHub 克隆）

1. GCP Console → 你的 VM → 點 **SSH** 開啟瀏覽器終端機

2. 在 SSH 中執行（請把 `YOUR_GITHUB_TOKEN` 換成你的 Personal Access Token，或使用 SSH key）：

```bash
# 安裝 git（若尚未安裝）
sudo apt-get update && sudo apt-get install -y git

# 克隆專案（私人 repo 需授權）
# 方式 A：用 HTTPS + Token（在網址中填入 token）
git clone https://YOUR_GITHUB_TOKEN@github.com/marklin-bit/tx_models.git ~/tx_models

# 方式 B：若已設定 SSH key，可用
# git clone git@github.com:marklin-bit/tx_models.git ~/tx_models

cd ~/tx_models
chmod +x deploy.sh
./deploy.sh
```

3. 建立 GitHub Personal Access Token（若尚未有）：
   - 開啟 https://github.com/settings/tokens
   - Generate new token (classic)
   - 勾選 `repo` 權限
   - 複製 token，在 clone 時替換 `YOUR_GITHUB_TOKEN`

4. 部署完成後啟動服務：
```bash
sudo systemctl start tx-signals
```

5. 開啟 GCP 防火牆 **TCP:8501**（若尚未開放）

6. 瀏覽器開啟：**http://35.212.199.216:8501**

---

## 二、之後程式更新流程

### 在你電腦（本機）

1. 請我修改程式 → 我改完後會 **commit + push** 到 GitHub
2. 或你自己 push：
   ```bash
   git add -A
   git commit -m "說明這次改了什麼"
   git push origin main
   ```

### 在 VM 上

1. SSH 連線到 VM
2. 執行一鍵更新：
   ```bash
   cd ~/tx_models
   ./update_vm.sh
   ```
3. 約 10 秒後服務會自動重啟，重新整理網頁即可看到最新版

---

## 三、常用指令（在 VM SSH 中）

| 操作       | 指令 |
|------------|------|
| 啟動服務   | `sudo systemctl start tx-signals` |
| 停止服務   | `sudo systemctl stop tx-signals` |
| 重啟服務   | `sudo systemctl restart tx-signals` |
| 查看狀態   | `sudo systemctl status tx-signals` |
| 即時看 LOG | `sudo journalctl -u tx-signals -f` |
| 一鍵更新   | `cd ~/tx_models && ./update_vm.sh` |

---

## 四、注意事項

- **資料庫** `database/tx_data.db` 不會放進 Git，每台機器各自保留
- VM 首次部署後若沒有 db，排程器會在 06:00 / 14:00 自動抓資料建立
- 若需要把本機的資料庫複製到 VM，請手動用 SCP 或 GCP 上傳檔案到 `~/tx_models/database/`
