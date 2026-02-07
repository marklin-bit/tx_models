# -*- coding: utf-8 -*-
"""
資料抓取模組
負責從鉅亨網 API 抓取台指期即時資料
"""

import requests
import pandas as pd
from datetime import datetime
from typing import Optional
import os
import sys

# 添加父目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import API_CONFIG


class DataFetcher:
    """鉅亨網 API 資料抓取器"""
    
    def __init__(self):
        """初始化資料抓取器"""
        self.symbol = API_CONFIG['symbol']
        self.base_url = API_CONFIG['base_url']
        self.resolution = API_CONFIG['resolution']
        self.limit = API_CONFIG['limit']
        self.timeout = API_CONFIG['timeout']
        self.headers = API_CONFIG['headers']
    
    def fetch_raw(self) -> pd.DataFrame:
        """
        從鉅亨網 API 抓取原始 OHLCV 資料
        
        Returns:
            包含 OHLCV 資料的 DataFrame
        """
        to_ts = int(datetime.now().timestamp())
        params = {
            "symbol": self.symbol,
            "resolution": self.resolution,
            "to": to_ts,
            "limit": self.limit
        }
        
        try:
            res = requests.get(
                self.base_url, 
                params=params, 
                headers=self.headers, 
                timeout=self.timeout
            )
            
            if res.status_code == 200:
                data = res.json().get('data', {})
                return self._parse_response(data)
            else:
                print(f"API 回應錯誤: HTTP {res.status_code}")
                return pd.DataFrame()
                
        except requests.exceptions.Timeout:
            print("API 連線逾時")
            return pd.DataFrame()
        except requests.exceptions.ConnectionError:
            print("API 連線失敗")
            return pd.DataFrame()
        except Exception as e:
            print(f"鉅亨網連線錯誤: {e}")
            return pd.DataFrame()
    
    def _parse_response(self, data: dict) -> pd.DataFrame:
        """
        解析 API 回應資料
        
        Args:
            data: API 回應的 data 欄位
        
        Returns:
            整理後的 OHLCV DataFrame
        """
        if not data:
            return pd.DataFrame()
        
        try:
            # 鉅亨網 API 回傳格式
            timestamps = data.get('t', [])
            opens = data.get('o', [])
            highs = data.get('h', [])
            lows = data.get('l', [])
            closes = data.get('c', [])
            volumes = data.get('v', [])
            
            if not timestamps:
                return pd.DataFrame()
            
            df = pd.DataFrame({
                'timestamp': timestamps,
                'open': opens,
                'high': highs,
                'low': lows,
                'close': closes,
                'volume': volumes
            })
            
            # 轉換時間戳為日期時間
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
            # 轉換為台灣時區 (UTC+8)
            df['datetime'] = df['datetime'] + pd.Timedelta(hours=8)
            
            # 排序 (由舊到新)
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            return df
            
        except Exception as e:
            print(f"解析資料時發生錯誤: {e}")
            return pd.DataFrame()
    
    def fetch_and_filter_today(self) -> pd.DataFrame:
        """
        抓取並過濾出今日交易時段的資料
        
        Returns:
            今日交易時段的 OHLCV DataFrame
        """
        df = self.fetch_raw()
        
        if df.empty:
            return df
        
        # 過濾今日資料
        today = datetime.now().strftime('%Y-%m-%d')
        df['date'] = df['datetime'].dt.strftime('%Y-%m-%d')
        today_df = df[df['date'] == today].copy()
        
        return today_df
    
    def get_latest_bar(self, df: Optional[pd.DataFrame] = None) -> Optional[dict]:
        """
        取得最新一根 K 棒資料
        
        Args:
            df: 可選的 DataFrame，若未提供則重新抓取
        
        Returns:
            最新 K 棒的字典，若無資料則返回 None
        """
        if df is None:
            df = self.fetch_raw()
        
        if df.empty:
            return None
        
        latest = df.iloc[-1]
        return {
            'timestamp': latest['timestamp'],
            'datetime': latest['datetime'],
            'open': latest['open'],
            'high': latest['high'],
            'low': latest['low'],
            'close': latest['close'],
            'volume': latest['volume']
        }


if __name__ == "__main__":
    # 測試程式碼
    fetcher = DataFetcher()
    print("開始抓取資料...")
    
    df = fetcher.fetch_raw()
    if not df.empty:
        print(f"成功抓取 {len(df)} 筆資料")
        print(f"時間範圍: {df['datetime'].min()} ~ {df['datetime'].max()}")
        print("\n最新 5 筆資料:")
        print(df.tail())
    else:
        print("抓取資料失敗")
