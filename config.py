# -*- coding: utf-8 -*-
"""
TX Models 設定檔
台指期當沖交易訊號監控系統
"""

import os

# =============================================================================
# 路徑設定
# =============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_DIR = os.path.join(BASE_DIR, "database")
DATABASE_PATH = os.path.join(DATABASE_DIR, "tx_data.db")

# 模型檔案路徑
MODEL_FILES = {
    "long_entry": [
        os.path.join(BASE_DIR, f"Long Entry ({i}).json") for i in range(1, 6)
    ],
    "long_exit": [
        os.path.join(BASE_DIR, f"Long Exit ({i}).json") for i in range(1, 6)
    ],
    "short_entry": [
        os.path.join(BASE_DIR, f"Short Entry ({i}).json") for i in range(1, 6)
    ],
    "short_exit": [
        os.path.join(BASE_DIR, f"Short Exit ({i}).json") for i in range(1, 6)
    ],
}

# =============================================================================
# API 設定
# =============================================================================
API_CONFIG = {
    "symbol": "TWF:TXF:FUTURES",
    "base_url": "https://ws.api.cnyes.com/ws/api/v1/charting/history",
    "resolution": "5",  # 5分K
    "limit": 1000,
    "timeout": 8,
    "headers": {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://stock.cnyes.com/market/TWF:TXF:FUTURES"
    }
}

# =============================================================================
# 資料庫設定
# =============================================================================
DB_CONFIG = {
    "max_days": 5,  # 最多保留5個交易日的資料
}

# =============================================================================
# 訊號門檻設定
# =============================================================================
THRESHOLDS = {
    # 進場門檻 (Entry) - 三階段
    "entry": {
        "level_1": 0.60,  # 多-勝率26%,RECALL 12% / 空-勝率30%,RECALL 9%
        "level_2": 0.70,  # 多-勝率30%,RECALL 7% / 空-勝率20%,RECALL 3%
        "level_3": 0.80,  # 多-勝率50%,RECALL 5% / 空-勝率40%,RECALL 2%
    },
    # 出場門檻 (Exit)
    "exit": {
        "level_1": 0.85,
    }
}

# =============================================================================
# 技術指標參數
# =============================================================================
INDICATOR_PARAMS = {
    "rsi_period": 14,
    "adx_period": 14,
    "cci_period": 20,
    "atr_period": 14,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "sma_short": 5,
    "sma_long": 20,
    "volume_ma_period": 5,
    "lookback_window": 20,  # 用於成本乖離力、通道位置等
}

# =============================================================================
# LINE Bot 設定（建議用環境變數，避免寫進程式碼）
# =============================================================================
LINE_CONFIG = {
    "channel_id": os.environ.get("LINE_CHANNEL_ID", "2009071761"),
    "channel_secret": os.environ.get("LINE_CHANNEL_SECRET", "08dcb989245efea962fb870961cca995"),
    "enabled": os.environ.get("LINE_ENABLED", "true").lower() in ("1", "true", "yes"),
}

# =============================================================================
# 頁面設定
# =============================================================================
PAGE_CONFIG = {
    "title": "TX 台指期當沖訊號監控",
    "icon": "📈",
    "layout": "wide",
    "refresh_interval": 300,  # 5分鐘 = 300秒
}

# =============================================================================
# 17個特徵名稱 (順序必須與模型訓練時一致)
# =============================================================================
FEATURE_NAMES = [
    "RSI14",
    "ADX14", 
    "CCI20",
    "OSC",
    "ATR14",
    "Parkinson_Volatility",
    "Cost_Deviation",
    "RSI_Normalized",
    "SMA5_Slope",
    "Channel_Position",
    "Volume_Ratio",
    "Engulfing_Strength",
    "Kbar_Power",
    "N_Pattern",
    "Three_Soldiers",
    "Shadow_Reversal",
    "ThreeK_Reversal",
]
