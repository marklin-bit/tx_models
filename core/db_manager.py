# -*- coding: utf-8 -*-
"""
資料庫管理模組 V2
支援 OHLCV + 17特徵的儲存、按交易日清理
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_PATH, DATABASE_DIR, DB_CONFIG, FEATURE_NAMES


class DBManager:
    """SQLite 資料庫管理器 V2"""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._ensure_db_dir()
        self._init_db()
    
    def _ensure_db_dir(self):
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
    
    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """初始化資料庫（含17特徵欄位）"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 建立包含特徵的資料表
        feature_cols = ", ".join([f'"{f}" REAL' for f in FEATURE_NAMES])
        
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS ohlcv_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER UNIQUE NOT NULL,
                datetime TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume INTEGER NOT NULL,
                {feature_cols},
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_timestamp ON ohlcv_data(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_date ON ohlcv_data(date)")
        
        # 嘗試添加特徵欄位（如果舊表缺少）
        try:
            existing = [row[1] for row in cursor.execute("PRAGMA table_info(ohlcv_data)").fetchall()]
            for f in FEATURE_NAMES:
                if f not in existing:
                    cursor.execute(f'ALTER TABLE ohlcv_data ADD COLUMN "{f}" REAL')
        except:
            pass
        
        conn.commit()
        conn.close()
    
    def save_ohlcv(self, df: pd.DataFrame, include_features: bool = True) -> int:
        """儲存 OHLCV + 特徵"""
        if df.empty:
            return 0
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        base_cols = ['timestamp', 'datetime', 'date', 'open', 'high', 'low', 'close', 'volume']
        feat_cols = [f for f in FEATURE_NAMES if f in df.columns] if include_features else []
        all_cols = base_cols + feat_cols
        
        placeholders = ", ".join(["?"] * len(all_cols))
        col_names = ", ".join([f'"{c}"' for c in all_cols])
        
        inserted_count = 0
        for _, row in df.iterrows():
            try:
                dt_str = row['datetime']
                if isinstance(dt_str, pd.Timestamp):
                    dt_str = dt_str.strftime('%Y-%m-%d %H:%M:%S')
                # 優先使用明確的 date 欄位（與 import_history 一致），否則從 datetime 取前 10 字
                if 'date' in row and pd.notna(row.get('date')):
                    d = row['date']
                    date_str = d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d)[:10]
                else:
                    date_str = dt_str[:10] if isinstance(dt_str, str) else str(dt_str)[:10]
                
                values = [
                    int(row['timestamp']), dt_str, date_str,
                    float(row['open']), float(row['high']), float(row['low']),
                    float(row['close']), int(row['volume'])
                ]
                
                for f in feat_cols:
                    val = row.get(f)
                    values.append(float(val) if pd.notna(val) else None)
                
                # UPSERT: 如有重複timestamp則更新
                update_cols = ", ".join([f'"{c}"=excluded."{c}"' for c in all_cols if c != 'timestamp'])
                cursor.execute(f"""
                    INSERT INTO ohlcv_data ({col_names})
                    VALUES ({placeholders})
                    ON CONFLICT(timestamp) DO UPDATE SET {update_cols}
                """, values)
                
                inserted_count += 1
            except Exception as e:
                continue
        
        conn.commit()
        conn.close()
        return inserted_count
    
    def load_ohlcv(self, days: Optional[int] = None,
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None,
                   include_features: bool = False) -> pd.DataFrame:
        """載入 OHLCV（可含特徵）"""
        conn = self._get_connection()
        
        if include_features:
            feat_select = ", ".join([f'"{f}"' for f in FEATURE_NAMES])
            cols = f"timestamp, datetime, date, open, high, low, close, volume, {feat_select}"
        else:
            cols = "timestamp, datetime, date, open, high, low, close, volume"
        
        query = f"SELECT {cols} FROM ohlcv_data"
        conditions = []
        params = []
        
        if start_date:
            conditions.append("date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("date <= ?")
            params.append(end_date)
        if days and not start_date:
            # 用交易日邏輯：取最近N個不同日期
            date_query = "SELECT DISTINCT date FROM ohlcv_data ORDER BY date DESC LIMIT ?"
            cursor = conn.cursor()
            cursor.execute(date_query, (days,))
            dates = [r[0] for r in cursor.fetchall()]
            if dates:
                cutoff = min(dates)
                conditions.append("date >= ?")
                params.append(cutoff)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY timestamp ASC"
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if not df.empty:
            df['datetime'] = pd.to_datetime(df['datetime'])
        
        return df
    
    def load_by_date(self, target_date: str, include_features: bool = True) -> pd.DataFrame:
        """載入指定日期資料（依 datetime 範圍查詢，避免 date 欄位格式不一致漏列）"""
        conn = self._get_connection()
        if include_features:
            feat_select = ", ".join([f'"{f}"' for f in FEATURE_NAMES])
            cols = f"timestamp, datetime, date, open, high, low, close, volume, {feat_select}"
        else:
            cols = "timestamp, datetime, date, open, high, low, close, volume"
        # 用 datetime 範圍抓當日 00:00 ~ 隔日 00:00 前，不依賴 date 欄位格式（避免 2026-2-6 漏列）
        start_dt = f"{target_date} 00:00:00"
        end_dt = f"{target_date} 23:59:59"
        query = f"""SELECT {cols} FROM ohlcv_data
                    WHERE datetime >= ? AND datetime <= ?
                    ORDER BY timestamp ASC"""
        df = pd.read_sql_query(query, conn, params=[start_dt, end_dt])
        conn.close()
        if not df.empty:
            df['datetime'] = pd.to_datetime(df['datetime'])
        return df
    
    def get_trading_dates(self) -> List[str]:
        """取得資料庫中所有交易日期"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT date FROM ohlcv_data ORDER BY date DESC")
        dates = [row[0] for row in cursor.fetchall()]
        conn.close()
        return dates
    
    def cleanup_by_trading_days(self, keep_days: int = 5) -> int:
        """按交易日清理（保留最近N個交易日）"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 取得所有交易日
        cursor.execute("SELECT DISTINCT date FROM ohlcv_data ORDER BY date DESC")
        all_dates = [row[0] for row in cursor.fetchall()]
        
        if len(all_dates) <= keep_days:
            conn.close()
            return 0
        
        # 保留最近 keep_days 個交易日
        dates_to_delete = all_dates[keep_days:]
        
        if not dates_to_delete:
            conn.close()
            return 0
        
        placeholders = ",".join(["?"] * len(dates_to_delete))
        cursor.execute(f"SELECT COUNT(*) FROM ohlcv_data WHERE date IN ({placeholders})", dates_to_delete)
        count = cursor.fetchone()[0]
        
        cursor.execute(f"DELETE FROM ohlcv_data WHERE date IN ({placeholders})", dates_to_delete)
        conn.commit()
        conn.close()
        
        return count
    
    # 保留舊方法的兼容性
    def cleanup_old_data(self, max_days: int = None) -> int:
        return self.cleanup_by_trading_days(keep_days=max_days or DB_CONFIG.get('max_days', 5))
    
    def load_today_data(self) -> pd.DataFrame:
        today = datetime.now().strftime('%Y-%m-%d')
        return self.load_ohlcv(start_date=today, end_date=today)
    
    def get_latest_timestamp(self) -> Optional[int]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(timestamp) FROM ohlcv_data")
        result = cursor.fetchone()[0]
        conn.close()
        return result
    
    def get_data_stats(self) -> dict:
        conn = self._get_connection()
        cursor = conn.cursor()
        stats = {}
        cursor.execute("SELECT COUNT(*) FROM ohlcv_data")
        stats['total_records'] = cursor.fetchone()[0]
        cursor.execute("SELECT MIN(date), MAX(date) FROM ohlcv_data")
        row = cursor.fetchone()
        stats['date_range'] = {'min': row[0], 'max': row[1]}
        cursor.execute("SELECT date, COUNT(*) as count FROM ohlcv_data GROUP BY date ORDER BY date DESC")
        stats['daily_counts'] = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return stats
    
    def check_data_gaps(self) -> list:
        """
        檢查資料完整性，回傳缺口清單。
        
        台指期交易時段：
          - 夜盤前段: 00:00~04:55 (約60筆)
          - 日盤:     08:45~13:40/13:45 (約59~60筆)
          - 夜盤後段: 15:00~23:55 (約108筆)
        
        防呆規則：
          R1. 有日盤 → 同日應有夜盤後段，隔日(日曆日)應有夜盤前段
          R2. 有夜盤後段 → 同日應有日盤（反向檢查）
          R3. 有夜盤前段 → 前一日(日曆日)應有日盤+夜盤後段（反向檢查）
              ※ 注意：不要求前一日有夜盤前段！
              ※ 例：2/3(二) 有夜盤前段 → 2/2(一) 須有日盤+夜盤後段即可，
                    2/2(一) 本身沒有夜盤前段是正常的（週一不延續週日）
          R4. 各時段筆數不足也視為缺口
        
        Returns:
            list[dict]: 缺口描述清單
              [{'date': 'YYYY-MM-DD', 'session': 'day_session'|'night_late'|'night_early',
                'expected': int, 'actual': int, 'status': 'missing'|'incomplete'}]
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 取得每個日期各時段的筆數
        cursor.execute("""
            SELECT date,
                   SUM(CASE WHEN CAST(strftime('%H', datetime) AS INT) < 6 THEN 1 ELSE 0 END) as night_early,
                   SUM(CASE WHEN CAST(strftime('%H', datetime) AS INT) BETWEEN 8 AND 13 THEN 1 ELSE 0 END) as day_session,
                   SUM(CASE WHEN CAST(strftime('%H', datetime) AS INT) >= 15 THEN 1 ELSE 0 END) as night_late
            FROM ohlcv_data
            GROUP BY date
            ORDER BY date ASC
        """)
        
        date_sessions = {}
        for row in cursor.fetchall():
            date_sessions[row[0]] = {
                'night_early': row[1],
                'day_session': row[2],
                'night_late': row[3],
            }
        conn.close()
        
        gaps = []
        sorted_dates = sorted(date_sessions.keys())
        today_str = datetime.now().strftime('%Y-%m-%d')
        
        # 最小筆數門檻（低於此值視為 incomplete）
        MIN_NIGHT_EARLY = 55   # 預期 ~60
        MIN_DAY_SESSION = 55   # 預期 ~59-60
        MIN_NIGHT_LATE  = 100  # 預期 ~108
        
        # 已記錄的缺口 (避免重複)
        reported = set()
        
        def _add_gap(date, session, expected, actual, status):
            key = (date, session)
            if key not in reported:
                reported.add(key)
                gaps.append({
                    'date': date, 'session': session,
                    'expected': expected, 'actual': actual, 'status': status
                })
        
        for i, d in enumerate(sorted_dates):
            sessions = date_sessions[d]
            
            # ── R1: 正向檢查 - 有日盤 → 同日應有夜盤後段，隔日應有夜盤前段 ──
            if sessions['day_session'] >= MIN_DAY_SESSION:
                # 同日夜盤後段
                if sessions['night_late'] == 0:
                    _add_gap(d, 'night_late', 108, 0, 'missing')
                elif sessions['night_late'] < MIN_NIGHT_LATE:
                    _add_gap(d, 'night_late', 108, sessions['night_late'], 'incomplete')
                
                # 隔日夜盤前段
                next_date = (datetime.strptime(d, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
                next_sessions = date_sessions.get(next_date, {})
                next_early = next_sessions.get('night_early', 0)
                
                if next_early == 0 and next_date <= today_str:
                    _add_gap(next_date, 'night_early', 60, 0, 'missing')
                elif 0 < next_early < MIN_NIGHT_EARLY:
                    _add_gap(next_date, 'night_early', 60, next_early, 'incomplete')
            
            # ── R2: 反向檢查 - 有夜盤後段 → 同日必須有日盤 ──
            if sessions['night_late'] > 0 and sessions['day_session'] == 0:
                _add_gap(d, 'day_session', 60, 0, 'missing')
            
            # ── R3: 反向檢查 - 有夜盤前段 → 前一日(日曆日)必須有日盤+夜盤後段 ──
            # ※ 只檢查 day_session 和 night_late，不要求前一日有 night_early
            # ※ 例：週二有 00:00~04:55 → 週一須有日盤+夜盤後段（週一本身無夜盤前段是正常的）
            if sessions['night_early'] > 0:
                prev_date = (datetime.strptime(d, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
                prev_sessions = date_sessions.get(prev_date, {})
                
                # 前一日在 DB 中存在才做檢查（不檢查 DB 範圍外的日期）
                if prev_date in date_sessions:
                    if prev_sessions.get('day_session', 0) == 0:
                        _add_gap(prev_date, 'day_session', 60, 0, 'missing')
                    if prev_sessions.get('night_late', 0) == 0:
                        _add_gap(prev_date, 'night_late', 108, 0, 'missing')
            
            # ── R4: 各時段筆數不足 ──
            if 0 < sessions['day_session'] < MIN_DAY_SESSION:
                _add_gap(d, 'day_session', 60, sessions['day_session'], 'incomplete')
            if 0 < sessions['night_early'] < MIN_NIGHT_EARLY:
                _add_gap(d, 'night_early', 60, sessions['night_early'], 'incomplete')
            if 0 < sessions['night_late'] < MIN_NIGHT_LATE:
                _add_gap(d, 'night_late', 108, sessions['night_late'], 'incomplete')
        
        return gaps
    
    def check_feature_completeness(self) -> list:
        """
        檢查每個日期的特徵是否完整（無 NULL）
        
        Returns:
            list[dict]: [{'date': ..., 'feature': ..., 'null_count': ...}]
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        issues = []
        dates = [r[0] for r in cursor.execute(
            "SELECT DISTINCT date FROM ohlcv_data ORDER BY date ASC"
        ).fetchall()]
        
        for d in dates:
            for f in FEATURE_NAMES:
                cursor.execute(f"""
                    SELECT COUNT(*) FROM ohlcv_data
                    WHERE date = ? AND ("{f}" IS NULL)
                """, (d,))
                null_count = cursor.fetchone()[0]
                if null_count > 0:
                    issues.append({
                        'date': d, 'feature': f, 'null_count': null_count
                    })
        
        conn.close()
        return issues
    
    def get_date_session_summary(self) -> dict:
        """
        取得每個日期的時段摘要
        
        Returns:
            dict: {date: {'night_early': N, 'day_session': N, 'night_late': N, 'total': N}}
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT date,
                   SUM(CASE WHEN CAST(strftime('%H', datetime) AS INT) < 6 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN CAST(strftime('%H', datetime) AS INT) BETWEEN 8 AND 13 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN CAST(strftime('%H', datetime) AS INT) >= 15 THEN 1 ELSE 0 END),
                   COUNT(*)
            FROM ohlcv_data
            GROUP BY date
            ORDER BY date ASC
        """)
        
        result = {}
        for row in cursor.fetchall():
            result[row[0]] = {
                'night_early': row[1], 'day_session': row[2],
                'night_late': row[3], 'total': row[4]
            }
        conn.close()
        return result
    
    def vacuum(self):
        conn = self._get_connection()
        conn.execute("VACUUM")
        conn.close()
