# TX Models - VM 部署說明（新手版）

## 第一步：開放 VM 的網頁連線（防火牆）

1. 開啟瀏覽器，進入 **Google Cloud Console**：https://console.cloud.google.com/
2. 左側選單點 **「VPC 網路」** → **「防火牆」**
3. 點上方 **「建立防火牆規則」**
4. 照下面填寫：
   - **名稱**：`allow-streamlit`
   - **流量方向**：選 **輸入 (Ingress)**
   - **目標**：選 **網路中的所有執行個體**
   - **來源 IPv4 範圍**：填 `0.0.0.0/0`
   - **通訊協定和通訊埠**：勾選 **指定的通訊協定和通訊埠**，再勾選 **TCP**，通訊埠填 `8501`
5. 點 **「建立」**

---

## 第二步：連到 VM 並一鍵部署

1. 在 GCP Console 左側選 **「Compute Engine」** → **「VM 執行個體」**
2. 找到你的 VM（外部 IP：35.212.199.216），點右邊的 **「SSH」** 按鈕  
   → 會開一個新視窗，裡面是黑色的終端機（命令列）
3. 在終端機裡 **整段複製下面這一大段**，貼上去，按 **Enter**：

```bash
sudo apt-get update -y && sudo apt-get install -y git && \
git clone https://github.com/marklin-bit/tx_models.git ~/tx_models && \
cd ~/tx_models && chmod +x deploy.sh && ./deploy.sh
```

4. 等待跑完（約 3～5 分鐘），最後會出現「部署完成」
5. 再貼下面這行，按 **Enter** 啟動服務：

```bash
sudo systemctl start tx-signals
```

6. 等約 10 秒，用瀏覽器開啟：**http://35.212.199.216:8501**

---

## 完成後

- 網頁能正常開啟就代表部署成功。
- 之後若程式有更新，在 VM 的 SSH 裡執行下面兩行即可更新並重啟：

```bash
cd ~/tx_models
./update_vm.sh
```

---

## 若想改回私人 repo（選用）

目前專案是 **公開**，方便 VM 直接 clone，不用 Token。  
若你之後想改回私人：

1. 開啟：https://github.com/marklin-bit/tx_models/settings
2. 捲到最下面 **「Danger Zone」**
3. 點 **「Change repository visibility」** → 選 **Private** → 確認

改回私人後，VM 之後要用 **Token** 才能執行 `update_vm.sh` 拉新程式碼；若你暫時不會改回私人，可以維持公開即可。
