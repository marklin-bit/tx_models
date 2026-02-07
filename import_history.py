# -*- coding: utf-8 -*-
"""
歷史資料匯入腳本
讀取 CSV 歷史交易資料，計算17個特徵後存入資料庫
保留最近5個交易日
"""

import pandas as pd
import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import FEATURE_NAMES
from core.db_manager import DBManager
from core.feature_calculator import FeatureCalculator


def import_csv(csv_path: str):
    """匯入 CSV 歷史資料"""
    print(f"[1/5] 讀取 CSV: {csv_path}")
    
    # 嘗試不同編碼
    for enc in ['big5', 'cp950', 'utf-8', 'utf-8-sig']:
        try:
            df = pd.read_csv(csv_path, encoding=enc)
            break
        except:
            continue
    else:
        print("ERROR: 無法讀取 CSV，請確認編碼格式")
        return
    
    print(f"  原始欄位: {list(df.columns)}")
    print(f"  資料筆數: {len(df)}")
    
    # 欄位名稱標準化（支援中英文）
    col_map = {}
    cols = list(df.columns)
    
    # 嘗試依序對應
    expected_zh = ['日期', '時間', '開盤價', '最高價', '最低價', '收盤價', '成交量']
    expected_en = ['date', 'time', 'open', 'high', 'low', 'close', 'volume']
    
    if len(cols) >= 7:
        for i, col in enumerate(cols[:7]):
            col_lower = col.strip().lower()
            if any(zh in col for zh in expected_zh):
                col_map[col] = expected_en[expected_zh.index(next(zh for zh in expected_zh if zh in col))]
            else:
                col_map[col] = expected_en[i]
    
    if col_map:
        df = df.rename(columns=col_map)
    
    print(f"  對應後欄位: {list(df.columns)}")
    
    # 建立 datetime
    print("[2/5] 轉換時間格式...")
    df['datetime'] = pd.to_datetime(df['date'].astype(str) + ' ' + df['time'].astype(str))
    
    # 建立 timestamp（秒級）
    df['timestamp'] = (df['datetime'].astype(np.int64) // 10**9).astype(int)
    
    # 確保數值欄位
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.dropna(subset=['open', 'high', 'low', 'close', 'volume'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    print(f"  有效資料: {len(df)} 筆")
    print(f"  日期範圍: {df['datetime'].min()} ~ {df['datetime'].max()}")
    
    # 顯示交易日
    df['date_str'] = df['datetime'].dt.strftime('%Y-%m-%d')
    trading_dates = sorted(df['date_str'].unique())
    print(f"  交易日數: {len(trading_dates)}")
    for d in trading_dates:
        count = len(df[df['date_str'] == d])
        print(f"    {d}: {count} 筆")
    
    # 計算17個特徵
    print("[3/5] 計算17個特徵...")
    fc = FeatureCalculator()
    processed = fc.calculate_all(df)
    
    # 確認特徵
    missing = [f for f in FEATURE_NAMES if f not in processed.columns]
    if missing:
        print(f"  WARNING: 缺少特徵: {missing}")
    else:
        print(f"  17個特徵計算完成")
    
    # 顯示最後幾筆特徵值
    print("  最新一筆特徵值:")
    last = processed.iloc[-1]
    for f in FEATURE_NAMES:
        if f in processed.columns:
            print(f"    {f}: {last[f]:.6f}")
    
    # 存入資料庫
    print("[4/5] 存入資料庫...")
    db = DBManager()
    count = db.save_ohlcv(processed, include_features=True)
    print(f"  已存入 {count} 筆資料")
    
    # 清理舊資料（保留5個交易日）
    print("[5/5] 清理舊資料（保留5個交易日）...")
    deleted = db.cleanup_by_trading_days(keep_days=5)
    print(f"  已清理 {deleted} 筆舊資料")
    
    # 最終統計
    stats = db.get_data_stats()
    print("\n=== 資料庫統計 ===")
    print(f"  總筆數: {stats['total_records']}")
    print(f"  日期範圍: {stats['date_range']}")
    for date, cnt in stats['daily_counts'].items():
        print(f"    {date}: {cnt} 筆")
    
    print("\n匯入完成!")


if __name__ == "__main__":
    csv_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "260207_history.csv")
    
    if not os.path.exists(csv_file):
        print(f"找不到檔案: {csv_file}")
        sys.exit(1)
    
    import_csv(csv_file)
