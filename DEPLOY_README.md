# TX Models - 操作說明

本說明只保留兩件事：**之後改程式該怎麼做**、**換 LINE 金鑰該怎麼做**。  
每一步都寫詳細，並提供一鍵作法。

---

## 一、之後改程式該怎麼做

### 流程說明

| 步驟 | 誰做 | 做什麼 |
|------|------|--------|
| 1 | 你 | 跟我說要改什麼功能（例如：加一個欄位、改門檻） |
| 2 | 我 | 在本機改程式 → `git commit` → `git push` 到 GitHub |
| 3 | 你 | 在 VM 的 SSH 裡執行「一鍵更新」指令（見下方） |

### 一鍵更新（在 VM 的 SSH 裡整段複製貼上）

```bash
cd ~/tx_models && git fetch origin && git reset --hard origin/main && chmod +x update_vm.sh && ./update_vm.sh
```

- 約 10～30 秒後服務會自動重啟。
- 重新整理網頁 **http://35.212.199.216:8501** 即可看到新版本。

### 若一鍵更新失敗時的手動步驟

1. **連到 VM**  
   - 開啟：<https://console.cloud.google.com/compute/instances>  
   - 找到你的 VM，點右邊 **「SSH」** 開啟終端機。

2. **進入專案目錄**  
   ```bash
   cd ~/tx_models
   ```

3. **取得最新程式碼**  
   ```bash
   git fetch origin
   git reset --hard origin/main
   ```  
   - 若出現「本地有修改」被擋，`git reset --hard origin/main` 會強制跟 GitHub 一致。

4. **執行更新腳本**  
   ```bash
   chmod +x update_vm.sh
   ./update_vm.sh
   ```

5. **確認**  
   - 重新整理網頁即可。

### 相關網址

- **GitHub 專案**：<https://github.com/marklin-bit/tx_models>  
- **GCP VM 列表**：<https://console.cloud.google.com/compute/instances>  
- **網頁入口**：<http://35.212.199.216:8501>

---

## 二、換 LINE 金鑰該怎麼做

### 流程說明

1. 到 LINE Developers 取得新的 **Channel ID** 與 **Channel secret**（或沿用舊的）。
2. 在 VM 上執行「一鍵設定」腳本，或手動編輯 `/etc/tx_signals/env`。
3. 重啟服務後，可選擇執行「測試 LINE」腳本確認是否成功。

### 一鍵設定 LINE 金鑰（在 VM 的 SSH 裡執行）

**方式 A：互動輸入（推薦）**

```bash
cd ~/tx_models
chmod +x setup_line_env.sh
./setup_line_env.sh
```

- 腳本會提示你貼上 **Channel ID**、**Channel secret**。
- 貼上後按 Enter，腳本會寫入 `/etc/tx_signals/env` 並自動重啟服務。

**方式 B：參數一次帶入**

```bash
cd ~/tx_models
chmod +x setup_line_env.sh
./setup_line_env.sh 你的Channel_ID 你的Channel_Secret
```

- 把 `你的Channel_ID`、`你的Channel_Secret` 換成實際值，中間用空格隔開。

### 取得 LINE 金鑰的詳細步驟

1. **開啟 LINE Developers Console**  
   - 網址：<https://developers.line.biz/console/>

2. **登入**  
   - 使用你的 LINE 帳號登入。

3. **選 Provider 與 Channel**  
   - 點選你的 **Provider**（若沒有就先建一個）。  
   - 點選要用的 **Channel**（Messaging API）。

4. **開啟 Basic settings**  
   - 在該 Channel 頁面點 **「Basic settings」** 分頁。

5. **複製金鑰**  
   - **Channel ID**：頁面上會顯示，直接複製。  
   - **Channel secret**：點 **「Issue」** 可重新發行，複製顯示的 secret（舊的會失效）。

6. **（選用）發行 Channel secret**  
   - 若曾外洩或要換新金鑰：同頁 **「Channel secret」** 旁點 **「Issue」**，再複製新的 secret。

### 手動編輯金鑰檔（不用一鍵腳本時）

1. 在 VM 的 SSH 裡執行：  
   ```bash
   sudo nano /etc/tx_signals/env
   ```

2. 內容設成（替換成你的實際值）：  
   ```
   LINE_CHANNEL_ID=你的Channel_ID
   LINE_CHANNEL_SECRET=你的Channel_Secret
   LINE_ENABLED=true
   ```

3. 存檔：`Ctrl+O` → `Enter` → `Ctrl+X`。

4. 重啟服務：  
   ```bash
   sudo systemctl restart tx-signals
   ```

### 測試 LINE 是否成功

在 VM 的 SSH 裡執行：

```bash
cd ~/tx_models
chmod +x test_line.sh
./test_line.sh
```

- 成功：會顯示「LINE 測試成功」，並在手機收到測試訊息。  
- 失敗：會顯示錯誤，請檢查金鑰是否正確、網路是否正常。

### 相關網址

- **LINE Developers Console**：<https://developers.line.biz/console/>  
- **Messaging API 說明**：<https://developers.line.biz/zh-hant/docs/messaging-api/>

---

## 快速對照

| 要做的事       | 一鍵作法 |
|----------------|----------|
| 更新程式       | `cd ~/tx_models && git fetch origin && git reset --hard origin/main && chmod +x update_vm.sh && ./update_vm.sh` |
| 換 LINE 金鑰   | `cd ~/tx_models && chmod +x setup_line_env.sh && ./setup_line_env.sh` |
| 測試 LINE      | `cd ~/tx_models && chmod +x test_line.sh && ./test_line.sh` |
