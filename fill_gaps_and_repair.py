# -*- coding: utf-8 -*-
"""
一鍵修復：檢查資料缺口（含缺早盤）、從 API 補回、重算 17 個特徵。
VM 或本機若出現「某日沒有早盤」時可執行此腳本，無需手動匯入 CSV。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.db_manager import DBManager
from core.data_fetcher import DataFetcher
from core.feature_calculator import FeatureCalculator
from core.scheduler import DataScheduler
from repair_features import repair


def main():
    print("=" * 60)
    print("一鍵修復：缺口檢查 + 補早盤/夜盤 + 特徵重算")
    print("=" * 60)
    
    db = DBManager()
    fetcher = DataFetcher()
    fc = FeatureCalculator()
    sched = DataScheduler(db, fetcher, fc)
    
    # 1. 檢查缺口
    gaps = db.check_data_gaps()
    if gaps:
        print(f"\n[1/2] 發現 {len(gaps)} 個缺口:")
        for g in gaps:
            print(f"  - {g['date']} {g['session']} (預期~{g['expected']}筆, 實際{g['actual']}筆)")
    else:
        print("\n[1/2] 無缺口。")
    
    # 2. 嘗試從 API 補回（含「指定結束時間」重抓，可補到早盤）
    result = sched.validate_and_fill_gaps(api_data=None)
    print(f"\n缺口修復結果: 發現 {result['gaps_found']} 個, 已補 {result['fixed']} 個, 剩 {result['remaining']} 個")
    
    if result['remaining'] > 0:
        for g in result.get('details', []):
            print(f"  未修復: {g['date']} {g['session']}")
    
    # 3. 特徵重算（補齊 NULL、確保 17 特徵一致）
    print("\n[2/2] 重算 17 個特徵並寫回 DB...")
    repair()
    
    print("\n一鍵修復完成。")


if __name__ == "__main__":
    main()
