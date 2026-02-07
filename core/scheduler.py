# -*- coding: utf-8 -*-
"""
排程模組
每日 06:00（夜盤收盤後）、14:00（日盤收盤後）自動存取並清理資料

台指期交易時段：
  夜盤: 15:00 ~ 隔日 05:00
  日盤: 08:45 ~ 13:30(結算日) / 13:45(一般日)

排程邏輯：
  06:00 → 儲存夜盤資料（夜盤已於 05:00 收盤）
  14:00 → 儲存日盤資料（日盤已於 13:45 收盤）
  啟動時 → 自動檢查是否有錯過的排程，補跑
"""

import threading
import time
import json
import pandas as pd
from datetime import datetime, timedelta
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import FEATURE_NAMES, DATABASE_DIR
from core.db_manager import DBManager
from core.data_fetcher import DataFetcher
from core.feature_calculator import FeatureCalculator


class DataScheduler:
    """定時資料存取排程器"""
    
    # 排程時間 (時, 分, 描述)
    SCHEDULE_TIMES = [
        (6, 0, '夜盤'),   # 夜盤 15:00~05:00 收盤後
        (14, 0, '日盤'),   # 日盤 08:45~13:45 收盤後
    ]
    
    # 記錄檔路徑（追蹤上次執行時間，避免重複/遺漏）
    STATE_FILE = os.path.join(DATABASE_DIR, "scheduler_state.json")
    
    def __init__(self, db_manager: DBManager, data_fetcher: DataFetcher, 
                 feature_calculator: FeatureCalculator):
        self.db = db_manager
        self.fetcher = data_fetcher
        self.fc = feature_calculator
        self._timer = None
        self._running = False
        self.last_run = None
        self.last_status = ""
        self.log_messages = []
        self._state = self._load_state()
    
    # =========================================================================
    # 狀態持久化（記錄每個排程點的最後執行時間）
    # =========================================================================
    
    def _load_state(self) -> dict:
        """載入排程狀態"""
        try:
            if os.path.exists(self.STATE_FILE):
                with open(self.STATE_FILE, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
    
    def _save_state(self):
        """儲存排程狀態"""
        try:
            os.makedirs(os.path.dirname(self.STATE_FILE), exist_ok=True)
            with open(self.STATE_FILE, 'w') as f:
                json.dump(self._state, f)
        except Exception:
            pass
    
    def _get_last_run_key(self, hour, minute):
        """取得排程點的狀態 key"""
        return f"{hour:02d}:{minute:02d}"
    
    def _was_already_run_today(self, hour, minute):
        """檢查今天是否已執行過此排程點"""
        key = self._get_last_run_key(hour, minute)
        last_run_str = self._state.get(key)
        if not last_run_str:
            return False
        try:
            last_run_date = datetime.fromisoformat(last_run_str).date()
            return last_run_date == datetime.now().date()
        except Exception:
            return False
    
    def _mark_as_run(self, hour, minute):
        """標記此排程點今天已執行"""
        key = self._get_last_run_key(hour, minute)
        self._state[key] = datetime.now().isoformat()
        self._save_state()
    
    # =========================================================================
    # 日誌
    # =========================================================================
    
    def _log(self, msg: str):
        """記錄日誌"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {msg}"
        self.log_messages.append(log_entry)
        if len(self.log_messages) > 50:
            self.log_messages = self.log_messages[-50:]
        print(log_entry)
    
    # =========================================================================
    # 核心任務
    # =========================================================================
    
    def run_task(self, session_label: str = "") -> dict:
        """
        執行排程任務：
        1. 清理5個交易日前的資料
        2. 從API抓取最新資料
        3. 串聯歷史資料計算特徵
        4. 只存入新的API資料（不覆寫歷史）
        5. 防呆：檢查並補回缺失時段
        """
        result = {'success': False, 'message': '', 'saved': 0, 'deleted': 0}
        
        try:
            self._log(f"開始執行排程任務{f' ({session_label})' if session_label else ''}...")
            
            # Step 1: 清理舊資料
            deleted = self.db.cleanup_by_trading_days(keep_days=5)
            result['deleted'] = deleted
            self._log(f"清理舊資料: {deleted} 筆")
            
            # Step 2: 抓取API資料
            api_data = self.fetcher.fetch_raw()
            if api_data.empty:
                result['message'] = "API無資料"
                self._log("API無資料，任務結束")
                self.last_status = "API無資料"
                return result
            
            self._log(f"API抓取: {len(api_data)} 筆 "
                      f"({api_data['datetime'].min()} ~ {api_data['datetime'].max()})")
            
            # Step 3: 串聯歷史資料（用於特徵計算的 lookback）
            db_data = self.db.load_ohlcv(days=5)
            
            if not db_data.empty:
                combined = self._merge_data(db_data, api_data)
            else:
                combined = api_data
            
            self._log(f"合併資料: {len(combined)} 筆")
            
            # Step 4: 計算特徵（在完整合併資料上計算以確保連續性）
            if len(combined) >= 20:
                processed = self.fc.calculate_all(combined)
            else:
                processed = combined
                self._log("資料不足20筆，跳過特徵計算")
            
            # Step 5: 只存入「新的 API 資料」，不覆寫已有良好特徵的歷史資料
            api_timestamps = set(api_data['timestamp'].astype(int).values)
            new_data = processed[processed['timestamp'].astype(int).isin(api_timestamps)].copy()
            
            if new_data.empty:
                self._log("無新增資料需儲存")
                saved = 0
            else:
                saved = self.db.save_ohlcv(new_data, include_features=True)
            result['saved'] = saved
            
            # Step 6: 防呆 — 檢查資料缺口並嘗試修復
            gap_result = self.validate_and_fill_gaps(api_data)
            if gap_result['fixed'] > 0:
                result['message'] = f"存入 {saved} 筆, 清理 {deleted} 筆, 修復缺口 {gap_result['fixed']} 個"
            else:
                result['message'] = f"存入 {saved} 筆, 清理 {deleted} 筆"
            
            result['success'] = True
            self.last_run = datetime.now()
            self.last_status = f"成功 ({result['message']})"
            self._log(f"任務完成: {result['message']}")
            
        except Exception as e:
            result['message'] = str(e)
            self.last_status = f"失敗: {e}"
            self._log(f"任務失敗: {e}")
        
        return result
    
    def _merge_data(self, db_data, api_data):
        """合併DB與API資料"""
        combined = pd.concat([db_data, api_data], ignore_index=True)
        combined = combined.drop_duplicates(subset=['timestamp'], keep='last')
        combined = combined.sort_values('timestamp').reset_index(drop=True)
        return combined
    
    # =========================================================================
    # 防呆：資料缺口檢查與修復
    # =========================================================================
    
    def validate_and_fill_gaps(self, api_data: pd.DataFrame = None) -> dict:
        """
        檢查 DB 資料缺口並嘗試從 API 資料補回。
        
        台指期交易規則：
          - 有日盤 (08:45~13:45) → 同日必有夜盤 (15:00~隔日04:55)
          - 無日盤 (休市) → 無該日夜盤
        
        Args:
            api_data: 已抓取的 API 資料（避免重複呼叫 API）
        
        Returns:
            dict: {'gaps_found': N, 'fixed': N, 'remaining': N, 'details': [...]}
        """
        result = {'gaps_found': 0, 'fixed': 0, 'remaining': 0, 'details': []}
        
        # 檢查缺口
        gaps = self.db.check_data_gaps()
        result['gaps_found'] = len(gaps)
        
        if not gaps:
            self._log("資料完整性檢查: 無缺口")
            return result
        
        self._log(f"資料完整性檢查: 發現 {len(gaps)} 個缺口")
        for g in gaps:
            self._log(f"  缺口: {g['date']} {g['session']} "
                      f"(預期~{g['expected']}筆, 實際{g['actual']}筆, {g['status']})")
        
        # 嘗試用 API 資料補回缺口
        if api_data is None or api_data.empty:
            self._log("嘗試從 API 重新抓取資料以補回缺口...")
            api_data = self.fetcher.fetch_raw()
        
        if api_data.empty:
            self._log("API 無資料，無法修復缺口")
            result['remaining'] = len(gaps)
            result['details'] = gaps
            return result
        
        # API 資料加上 date 欄位
        if 'date' not in api_data.columns:
            api_data = api_data.copy()
            api_data['date'] = api_data['datetime'].dt.strftime('%Y-%m-%d')
        
        fixed_count = 0
        remaining_gaps = []
        
        for gap in gaps:
            gap_date = gap['date']
            gap_session = gap['session']
            
            # 根據缺口時段過濾 API 資料
            if gap_session == 'night_early':
                # 00:00~04:55
                mask = (api_data['date'] == gap_date) & (api_data['datetime'].dt.hour < 6)
            elif gap_session == 'day_session':
                # 08:45~13:45
                mask = (api_data['date'] == gap_date) & \
                       (api_data['datetime'].dt.hour >= 8) & \
                       (api_data['datetime'].dt.hour < 14)
            elif gap_session == 'night_late':
                # 15:00~23:55
                mask = (api_data['date'] == gap_date) & (api_data['datetime'].dt.hour >= 15)
            else:
                remaining_gaps.append(gap)
                continue
            
            fill_data = api_data[mask].copy()
            
            if fill_data.empty:
                self._log(f"  {gap_date} {gap_session}: API 中無對應資料，無法修復")
                remaining_gaps.append(gap)
                continue
            
            # 將補回資料與完整歷史合併，重新計算特徵後存入
            db_data = self.db.load_ohlcv(days=5)
            combined = self._merge_data(db_data, fill_data) if not db_data.empty else fill_data
            
            if len(combined) >= 20:
                processed = self.fc.calculate_all(combined)
            else:
                processed = combined
            
            # 只存入補回的資料（用 timestamp 過濾）
            fill_timestamps = set(fill_data['timestamp'].astype(int).values)
            to_save = processed[processed['timestamp'].astype(int).isin(fill_timestamps)].copy()
            
            if not to_save.empty:
                saved = self.db.save_ohlcv(to_save, include_features=True)
                self._log(f"  {gap_date} {gap_session}: 補回 {saved} 筆")
                fixed_count += 1
            else:
                remaining_gaps.append(gap)
        
        # 修復後再次檢查特徵完整性
        feat_issues = self.db.check_feature_completeness()
        if feat_issues:
            self._log(f"發現 {len(feat_issues)} 個特徵 NULL，嘗試重算...")
            self._repair_features()
        
        result['fixed'] = fixed_count
        result['remaining'] = len(remaining_gaps)
        result['details'] = remaining_gaps
        
        if remaining_gaps:
            self._log(f"仍有 {len(remaining_gaps)} 個缺口無法從 API 修復（可能超出 API 範圍）")
        else:
            self._log("所有缺口已修復")
        
        return result
    
    def _repair_features(self):
        """重新計算所有特徵（修復 NULL）"""
        try:
            all_data = self.db.load_ohlcv(days=5)
            if all_data.empty or len(all_data) < 20:
                return
            
            processed = self.fc.calculate_all(all_data)
            
            # fillna(0) 處理 warmup 期的 NaN
            for f in FEATURE_NAMES:
                if f in processed.columns:
                    processed[f] = processed[f].fillna(0)
            
            self.db.save_ohlcv(processed, include_features=True)
            self._log("特徵重算完成")
        except Exception as e:
            self._log(f"特徵重算失敗: {e}")
    
    # =========================================================================
    # 啟動補跑邏輯
    # =========================================================================
    
    def _check_missed_on_startup(self):
        """
        啟動時檢查是否有錯過的排程需要補跑
        
        邏輯：
          現在是 HH:MM，檢查每個排程點 (h, m)：
          - 如果現在已過了排程時間 (HH:MM > h:m)
          - 而且今天還沒執行過
          → 立即補跑
        """
        now = datetime.now()
        
        for hour, minute, label in self.SCHEDULE_TIMES:
            scheduled_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # 只補跑「今天已經過了的」排程時間
            if now >= scheduled_time and not self._was_already_run_today(hour, minute):
                self._log(f"偵測到遺漏的排程: {hour:02d}:{minute:02d} ({label})，立即補跑")
                self.run_task(session_label=label)
                self._mark_as_run(hour, minute)
    
    # =========================================================================
    # 定時檢查
    # =========================================================================
    
    def _check_and_run(self):
        """每分鐘檢查一次是否到排程時間"""
        if not self._running:
            return
        
        now = datetime.now()
        
        for hour, minute, label in self.SCHEDULE_TIMES:
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            diff = abs((now - target).total_seconds())
            
            # 在排程時間的前後 2 分鐘內觸發
            if diff <= 120:
                if not self._was_already_run_today(hour, minute):
                    self._log(f"到達排程時間 {hour:02d}:{minute:02d} ({label})")
                    self.run_task(session_label=label)
                    self._mark_as_run(hour, minute)
                    break
        
        # 排程下一次檢查（60秒後）
        if self._running:
            self._timer = threading.Timer(60, self._check_and_run)
            self._timer.daemon = True
            self._timer.start()
    
    # =========================================================================
    # 啟動 / 停止
    # =========================================================================
    
    def start(self):
        """啟動排程器（含補跑檢查）"""
        if self._running:
            return
        self._running = True
        self._log("排程器已啟動 (每日 06:00 夜盤 / 14:00 日盤)")
        
        # 啟動時先檢查是否有遺漏的排程需要補跑
        self._check_missed_on_startup()
        
        # 開始定時檢查
        self._check_and_run()
    
    def stop(self):
        """停止排程器"""
        self._running = False
        if self._timer:
            self._timer.cancel()
        self._log("排程器已停止")
    
    def is_running(self) -> bool:
        return self._running
    
    def get_next_run_time(self) -> str:
        """取得下一次排程時間"""
        now = datetime.now()
        next_times = []
        
        for hour, minute, label in self.SCHEDULE_TIMES:
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # 如果今天已執行過或已過時間，排到明天
            if self._was_already_run_today(hour, minute) or target <= now:
                target += timedelta(days=1)
            next_times.append((target, label))
        
        next_run, next_label = min(next_times, key=lambda x: x[0])
        return f"{next_run.strftime('%Y-%m-%d %H:%M')} ({next_label})"
