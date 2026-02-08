# TX Models - 操作說明

本說明包含五件事：**之後改程式該怎麼做**、**換 LINE 金鑰該怎麼做**、**VM 外部 IP 變動了怎麼辦**、**歷史回顧只有 2～3 天怎麼辦**、**某日沒有早盤怎麼辦**。  
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

**重要：** VM 一鍵更新是從 **GitHub 的 main** 拉程式碼。若你在本機改了程式（例如日期欄、時間排序、早盤說明），**必須先在本機 commit 並 push 到 GitHub**，VM 一鍵更新才會拉到新程式。

```bash
cd ~/tx_models && git fetch origin && git reset --hard origin/main && chmod +x update_vm.sh && ./update_vm.sh
```

- 約 10～30 秒後服務會自動重啟。
- 重新整理網頁即可（網址見下方「三、VM 外部 IP 變動了」一鍵查詢）。
- **若網頁沒變：** 檢查本機是否已 `git push`，VM 拉的是 GitHub 上的 main，不是本機檔案。

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

## 三、VM 外部 IP 變動了怎麼辦

GCP VM 預設使用**臨時外部 IP**，VM 重開或 GCP 回收後，IP 可能改變，舊網址會打不開。  
只要改用**目前 IP** 開網頁即可，不需改程式或防火牆。

### 一鍵查詢目前 IP（在 VM 的 SSH 裡執行）

```bash
cd ~/tx_models && chmod +x get_ip.sh && ./get_ip.sh
```

- 會顯示此 VM **目前的外部 IP** 與完整網址 **http://IP:8501**。  
- 用瀏覽器開顯示的網址即可。

### 若 IP 已變動，該怎麼做

1. **連到 VM**（用 GCP Console，不依賴舊 IP）  
   - 開啟：<https://console.cloud.google.com/compute/instances>  
   - 找到你的 VM，點右邊 **「SSH」** 開啟終端機。

2. **查目前 IP**  
   ```bash
   cd ~/tx_models
   ./get_ip.sh
   ```  
   - 畫面上會印出 **http://新IP:8501**，複製到瀏覽器開啟即可。

3. **（選用）之後想用固定 IP**  
   - 到 GCP：<https://console.cloud.google.com/networking/addresses/list>  
   - 點 **「保留靜態外部 IP 位址」** → 名稱自訂、區域選與 VM 相同 → 建立。  
   - 到 **Compute Engine → VM 執行個體** → 點你的 VM → **編輯** → **網路** → **外部 IP** 改為剛保留的靜態 IP → 儲存。  
   - 之後 IP 就不會變，可一直用同一個網址。

### 相關網址

- **GCP VM 列表（用來連 SSH）**：<https://console.cloud.google.com/compute/instances>  
- **保留靜態 IP**：<https://console.cloud.google.com/networking/addresses/list>

---

## 四、歷史回顧只有 2～3 天怎麼辦（補齊 5 個交易日）

系統設定是**保留最近 5 個交易日**，但 VM 上的歷史回顧若只看到 2026-02-06、2026-02-07，代表 VM 的資料庫裡**只有這 2 個日期的資料**。

### 為什麼會少？

- VM 部署時是**從 GitHub clone**，專案裡的 `database/tx_data.db` **不會**跟著上傳（在 .gitignore），所以 VM 上的資料庫是**從空開始**。
- 排程每天 06:00、14:00 只從 API 抓「**最新約 1000 根 K 棒**」並寫入 DB，所以 VM 上的資料是**從第一次排程開始逐日累積**的。
- 若剛部署沒幾天，或 API 回傳的 1000 根只涵蓋 2 個日曆日，歷史回顧就只會出現 2 個日期；**不是清理掉 3 天**，而是 VM 上從來沒有那 3 天的資料。

### 一鍵補齊 5 個交易日（用本機的資料庫覆蓋 VM）

**前提：** 你本機的 `database/tx_data.db` 裡已有 5 個交易日（例如 2026-02-03～2026-02-07）。

**步驟 1：在本機找到資料庫檔**

- 路徑：`TX_models\database\tx_data.db`  
- 若本機也沒有 5 天，可先在本機跑過一次匯入歷史 CSV 或排程，讓本機 DB 有 5 天再上傳。

**步驟 2：上傳到 VM**

1. 開啟 GCP VM 的 SSH：<https://console.cloud.google.com/compute/instances> → 點你的 VM 右側 **「SSH」**。
2. 在 SSH 視窗**右上角**點 **齒輪圖示** → **「上傳檔案」**。
3. 選你本機的 `tx_data.db`（例如 `C:\Users\你的帳號\Desktop\數據分析\TX_models\database\tx_data.db`）上傳。
4. 上傳後檔案會在 VM 的**家目錄**，檔名為 `tx_data.db`。

**步驟 3：在 VM 執行還原**

**方式 A（有 restore_db.sh 時）**：先一鍵更新程式碼取得腳本，再執行  
`cd ~/tx_models && git fetch origin && git reset --hard origin/main && chmod +x restore_db.sh && ./restore_db.sh`

**方式 B（若出現 `No such file or directory`，不用腳本直接做）**：在 SSH 終端機依序執行：

```bash
mkdir -p ~/tx_models/database
cp ~/tx_data.db ~/tx_models/database/tx_data.db
sudo systemctl restart tx-signals
```

- 上傳的 `tx_data.db` 若在你家目錄以外，請把上面第二行的 `~/tx_data.db` 改成實際路徑（例如 `~/tx_models/tx_data.db`）。
- 執行完重新整理網頁，歷史回顧的下拉選單應會出現 5 個交易日。

### 若本機也沒有 5 天資料

- 在本機專案目錄執行 `import_history.py`（若有 `260207_history.csv`），會匯入歷史並保留最近 5 個交易日，再照上面步驟 2、3 把本機的 `tx_data.db` 上傳到 VM 並執行 `restore_db.sh`。

### 相關網址

- **GCP VM 列表（連 SSH）**：<https://console.cloud.google.com/compute/instances>

---

## 五、若某日沒有早盤（缺日盤資料）

若歷史回顧或排程發現「某日有夜盤但沒有早盤」（例如 2026-02-06 缺日盤），**免費 API 只能抓當下往前約 1000 根，已收盤的早盤抓不到**，只能靠 **CSV 歷史檔** 補早盤。

### 用 CSV 補早盤（建議作法）

**前提：** 你有 `260207_history.csv`（或同格式的歷史 CSV，含該日早盤 08:45～13:40 的 5 分 K）。  
**注意：** 此 CSV **只到 2026-02-06 早盤**，**夜盤（15:00～隔日 05:00）需由鉅亨網 API 補齊**。匯入後既有 DB 的夜盤會保留（與 CSV 合併）；若該日尚無夜盤，可等排程自動抓或執行 `fill_gaps_and_repair.py` 從 API 補。

**步驟 1：上傳 CSV 到 VM**

1. 開啟 GCP VM 的 SSH：<https://console.cloud.google.com/compute/instances> → 點你的 VM 右側 **「SSH」**。
2. 在 SSH 視窗**右上角**點 **齒輪** → **「上傳檔案」**。
3. 選本機的 `260207_history.csv`（路徑例如 `TX_models\260207_history.csv`）上傳。
4. 上傳後檔案會在 VM 的**家目錄**，檔名可能是 `260207_history.csv`。請**移到專案目錄**：
   ```bash
   mv ~/260207_history.csv ~/tx_models/
   ```
   （若上傳時已選到 `~/tx_models/` 則可略過）

**步驟 2：匯入 CSV 並補早盤**

在 VM 的 SSH 裡執行（請用 **venv 的 Python**，否則會出現 `python: command not found`）：

```bash
cd ~/tx_models && ./venv/bin/python import_history.py
```

- 若 CSV 不在專案目錄，可指定路徑：`./venv/bin/python import_history.py ~/260207_history.csv`
- 腳本會：讀取 CSV → 計算 17 個特徵 → **寫入 DB（與既有資料合併，同 timestamp 會更新）** → 保留最近 5 個交易日。  
  **CSV 只有早盤**：缺的 2026-02-06 早盤會從 CSV 補上；**2026-02-06 夜盤、2026-02-07 等**若 DB 已有（排程抓的）會保留，若沒有可等排程或執行 `./venv/bin/python fill_gaps_and_repair.py` 從 API 補夜盤。

**步驟 3：重算特徵並寫回**

匯入後務必重算一次全部特徵，讓整段 5 日資料的 lookback 一致（例如 RSI、MACD）：

```bash
cd ~/tx_models && ./venv/bin/python repair_features.py
```

- 完成後重新整理網頁，歷史回顧中 2026-02-06 應會顯示完整日盤。  
- **若 2026-02-06 夜盤或 2026-02-07 仍缺**：CSV 不含夜盤，需由 API 補。可等排程 06:00/14:00 自動抓，或手動執行 `./venv/bin/python fill_gaps_and_repair.py` 從鉅亨網補缺口並重算特徵。

**若補完後 2026-02-06 仍沒有早盤（08:45~13:40）**

1. 先在 VM 診斷 DB 內該日各時段筆數：  
   `cd ~/tx_models && ./venv/bin/python check_db_date.py 2026-02-06`  
   - 若「早盤 08:45~13:40 實際」遠小於 59 筆，代表 DB 裡缺早盤。
2. 再在 VM 重新跑一次「步驟 2 + 步驟 3」：  
   確保 `260207_history.csv` 仍在 `~/tx_models/`，然後執行  
   `./venv/bin/python import_history.py` 與  
   `./venv/bin/python repair_features.py`。  
   - 匯入腳本會明確寫入 `date` 欄位（YYYY-MM-DD），並與既有資料合併（同 timestamp 會更新），早盤會補上。
3. 重新整理網頁。

**為什麼補完後早盤又被清掉？**

- 若 DB 裡同一日有兩種 date 寫法（例如 `2026-02-06` 與 `2026-2-6`），舊版「清理 5 天外資料」是用**原始 date 字串**排序，`2026-2-6` 會被排到後面、被當成「舊日期」而整批刪除，所以 08:45~12:55 那批列會不見。
- 已改為依**正規化日期（YYYY-MM-DD）**判斷要保留的交易日，`2026-2-6` 與 `2026-02-06` 會視為同一天，不再誤刪早盤。

**補完後資料會存進 DB 嗎？要不要每次重傳？**

- **會存入。** `import_history.py` 與 `repair_features.py` 都是寫入 VM 上的 **`~/tx_models/database/tx_data.db`**，補完的早盤資料會一直留在裡面。
- **排程不會清掉已匯入的早盤。** 排程只會：(1) 刪除「超過 5 個交易日」的舊日期；(2) 從 API 抓新資料並**新增**進 DB（同 timestamp 才覆寫）。免費 API 抓不到已收盤的早盤，所以不會有那批 timestamp，也就不會覆寫或刪除你已匯入的早盤。
- **不用每次重傳。** 只要在 VM 上成功跑過一次「步驟 2 + 步驟 3」，之後不用再上傳 CSV，早盤資料會一直保留在 DB 裡。
- **只有在這些情況才需要再補一次**：VM 重裝、`tx_data.db` 被覆蓋或還原、或當初只在「本機」跑過匯入、從未在 VM 上跑過。若你發現補完後早盤又不見，多半是 VM 上的 DB 被換過或從未在 VM 上跑過匯入，此時再執行一次「步驟 2 + 步驟 3」即可。

### 若 API 能抓到該日資料（較少見）

若你的環境能抓到已收盤的歷史（例如付費 API 或 to_ts 仍在範圍內），可改執行：

```bash
cd ~/tx_models && ./venv/bin/python fill_gaps_and_repair.py
```

- 腳本會從 API 補缺口並重算特徵；**多數免費 API 抓不到已收盤早盤**，此時請用上面「用 CSV 補早盤」。

---

## 快速對照

| 要做的事       | 一鍵作法 |
|----------------|----------|
| 更新程式       | `cd ~/tx_models && git fetch origin && git reset --hard origin/main && chmod +x update_vm.sh && ./update_vm.sh` |
| 換 LINE 金鑰   | `cd ~/tx_models && chmod +x setup_line_env.sh && ./setup_line_env.sh` |
| 測試 LINE      | `cd ~/tx_models && chmod +x test_line.sh && ./test_line.sh` |
| 查目前網址 (IP 變動時) | `cd ~/tx_models && chmod +x get_ip.sh && ./get_ip.sh` |
| 補齊 5 天歷史（上傳 tx_data.db 後，無腳本時） | `mkdir -p ~/tx_models/database && cp ~/tx_data.db ~/tx_models/database/tx_data.db && sudo systemctl restart tx-signals` |
| 某日缺早盤（用 CSV） | 上傳 `260207_history.csv` 到 `~/tx_models/`，再執行 `./venv/bin/python import_history.py` 與 `./venv/bin/python repair_features.py` |
