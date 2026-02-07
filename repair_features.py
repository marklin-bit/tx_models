# -*- coding: utf-8 -*-
"""
一次性修復腳本：重新計算 DB 中所有資料的 17 個特徵值
解決因 warmup NaN / scheduler 覆寫 導致的 NULL 特徵問題
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from config import FEATURE_NAMES
from core.db_manager import DBManager
from core.feature_calculator import FeatureCalculator


def repair():
    db = DBManager()
    fc = FeatureCalculator()
    
    print("=" * 60)
    print("DB 特徵修復工具")
    print("=" * 60)
    
    # Step 1: 載入所有 OHLCV 資料（不含特徵）
    all_data = db.load_ohlcv(days=999)
    
    if all_data.empty:
        print("DB 無資料，無需修復")
        return
    
    print(f"載入 {len(all_data)} 筆 OHLCV 資料")
    
    # 檢查修復前狀態
    all_with_feat = db.load_ohlcv(days=999, include_features=True)
    null_before = 0
    for f in FEATURE_NAMES:
        if f in all_with_feat.columns:
            nc = all_with_feat[f].isna().sum()
            null_before += nc
    print(f"修復前: 共 {null_before} 個 NULL 特徵值")
    
    # Step 2: 重新計算全部特徵
    print("重新計算 17 個特徵...")
    processed = fc.calculate_all(all_data)
    
    # 檢查計算後的 NaN
    nan_count = 0
    for f in FEATURE_NAMES:
        if f in processed.columns:
            nc = processed[f].isna().sum()
            if nc > 0:
                print(f"  警告: {f} 仍有 {nc} 個 NaN（warmup 前幾列，已填 0）")
                # 強制補零
                processed[f] = processed[f].fillna(0)
                nan_count += nc
    
    if nan_count > 0:
        print(f"  已將 {nan_count} 個殘餘 NaN 強制填 0")
    else:
        print("  所有特徵計算完成，無 NaN")
    
    # Step 3: 按交易日分批存入（避免覆寫問題）
    print("存入修復後的特徵...")
    
    processed['_date'] = processed['datetime'].dt.strftime('%Y-%m-%d')
    dates = sorted(processed['_date'].unique())
    
    total_saved = 0
    for d in dates:
        day_data = processed[processed['_date'] == d].copy()
        day_data = day_data.drop(columns=['_date'], errors='ignore')
        saved = db.save_ohlcv(day_data, include_features=True)
        total_saved += saved
        
        # 驗證
        verify = db.load_by_date(d, include_features=True)
        null_count = sum(verify[f].isna().sum() for f in FEATURE_NAMES if f in verify.columns)
        status = "OK" if null_count == 0 else f"!! {null_count} NULL"
        print(f"  {d}: {saved} 筆 saved, 驗證: {status}")
    
    # Step 4: 最終驗證
    print()
    print("=" * 60)
    print("最終驗證")
    print("=" * 60)
    
    all_final = db.load_ohlcv(days=999, include_features=True)
    null_after = 0
    for f in FEATURE_NAMES:
        if f in all_final.columns:
            nc = all_final[f].isna().sum()
            if nc > 0:
                print(f"  {f}: {nc} NULL (未修復)")
            null_after += nc
    
    print(f"\n修復前: {null_before} NULL → 修復後: {null_after} NULL")
    
    if null_after == 0:
        print("修復完成! 所有特徵值均已填入。")
    else:
        print(f"警告: 仍有 {null_after} 個 NULL，請檢查資料完整性。")


if __name__ == "__main__":
    repair()
