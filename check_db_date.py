# -*- coding: utf-8 -*-
"""
診斷腳本：檢查指定日期在 DB 內各時段的筆數（含早盤 08~13 時）
在 VM 執行: ./venv/bin/python check_db_date.py [日期]
例: ./venv/bin/python check_db_date.py 2026-02-06
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.db_manager import DBManager


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "2026-02-06"
    db = DBManager()
    df = db.load_by_date(target, include_features=False)
    if df.empty:
        print(f"DB 內無 {target} 的資料")
        return
    if "datetime" not in df.columns:
        print("無 datetime 欄位")
        return
    df["hour"] = df["datetime"].dt.hour
    print(f"=== {target} 各時段筆數 ===")
    print(f"總筆數: {len(df)}")
    for h in range(24):
        cnt = (df["hour"] == h).sum()
        if cnt > 0:
            label = "早盤" if 8 <= h <= 13 else ("夜盤後" if h >= 15 else "夜盤前")
            print(f"  {h:02d}:00 ~ {h:02d}:55  {cnt:3d} 筆  ({label})")
    day_session = ((df["hour"] >= 8) & (df["hour"] < 14)).sum()
    print(f"\n早盤 08:45~13:40 應約 59~60 筆，實際: {day_session} 筆")
    if day_session < 50:
        print("  → 早盤缺資料，請在 VM 重新執行: ./venv/bin/python import_history.py 與 ./venv/bin/python repair_features.py")


if __name__ == "__main__":
    main()
