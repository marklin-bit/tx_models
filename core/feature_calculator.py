# -*- coding: utf-8 -*-
"""
特徵計算模組
負責計算模型所需的 17 個技術指標特徵
"""

import pandas as pd
import numpy as np
from typing import Optional
import os
import sys

# 添加父目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import INDICATOR_PARAMS, FEATURE_NAMES


class FeatureCalculator:
    """
    特徵計算器
    計算 17 個技術指標特徵，順序與模型訓練時一致
    """
    
    def __init__(self):
        """初始化特徵計算器"""
        self.params = INDICATOR_PARAMS
        self.feature_names = FEATURE_NAMES
    
    def calculate_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        計算所有 17 個特徵
        
        Args:
            df: 包含 OHLCV 資料的 DataFrame
                必須包含欄位: open, high, low, close, volume
        
        Returns:
            包含所有特徵的 DataFrame
        """
        if df.empty or len(df) < self.params['lookback_window']:
            return df
        
        # 複製原始資料避免修改
        result = df.copy()
        
        # 先計算基礎指標 (後續特徵會用到)
        result = self._calc_sma(result)
        result = self._calc_volume_ma(result)
        result = self._calc_atr(result)
        result = self._calc_parkinson_volatility(result)
        
        # 計算 17 個特徵 (順序必須一致)
        # 1. RSI14
        result['RSI14'] = self._calc_rsi(result['close'], self.params['rsi_period'])
        
        # 2. ADX14
        result['ADX14'] = self._calc_adx(result, self.params['adx_period'])
        
        # 3. CCI20
        result['CCI20'] = self._calc_cci(result, self.params['cci_period'])
        
        # 4. OSC (MACD Histogram) - 使用加權收盤價
        result['OSC'] = self._calc_macd_histogram(result)
        
        # 5. ATR14 (已計算，需 fillna 補 warmup 期)
        result['ATR14'] = result['_atr'].fillna(0)
        
        # 6. Parkinson Volatility (已計算，需 fillna 防護)
        result['Parkinson_Volatility'] = result['_parkinson'].fillna(0)
        
        # 7. Cost Deviation (成本乖離力)
        result['Cost_Deviation'] = self._calc_cost_deviation(result)
        
        # 8. RSI Normalized (RSI標準化)
        # 注意：RSI14 已是 0~1 範圍，需乘100再標準化
        result['RSI_Normalized'] = (result['RSI14'] * 100 - 50) / 50
        
        # 9. SMA5 Slope (5MA斜率)
        result['SMA5_Slope'] = self._calc_sma5_slope(result)
        
        # 10. Channel Position (通道位置/布林%B)
        result['Channel_Position'] = self._calc_channel_position(result)
        
        # 11. Volume Ratio (交易量能)
        result['Volume_Ratio'] = self._calc_volume_ratio(result)
        
        # 12. Engulfing Strength (吞噬強度)
        result['Engulfing_Strength'] = self._calc_engulfing_strength(result)
        
        # 13. Kbar Power (K棒力道)
        result['Kbar_Power'] = self._calc_kbar_power(result)
        
        # 14. N Pattern (N型態)
        result['N_Pattern'] = self._calc_n_pattern(result)
        
        # 15. Three Soldiers (三兵)
        result['Three_Soldiers'] = self._calc_three_soldiers(result)
        
        # 16. Shadow Reversal (影線反轉)
        result['Shadow_Reversal'] = self._calc_shadow_reversal(result)
        
        # 17. ThreeK Reversal (3K反轉)
        result['ThreeK_Reversal'] = self._calc_threek_reversal(result)
        
        # 清理輔助欄位
        aux_cols = [col for col in result.columns if col.startswith('_')]
        result = result.drop(columns=aux_cols, errors='ignore')
        
        return result
    
    def get_feature_array(self, df: pd.DataFrame, row_idx: int = -1) -> Optional[np.ndarray]:
        """
        取得指定列的特徵陣列 (用於模型預測)
        
        Args:
            df: 已計算特徵的 DataFrame
            row_idx: 要取得的列索引，預設為最新一列
        
        Returns:
            特徵陣列 (17個特徵)
        """
        try:
            features = df[self.feature_names].iloc[row_idx].values
            return features.reshape(1, -1)
        except Exception as e:
            print(f"取得特徵陣列時發生錯誤: {e}")
            return None
    
    # =========================================================================
    # 基礎指標計算
    # =========================================================================
    
    def _calc_sma(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算 SMA5 和 SMA20"""
        df['_sma5'] = df['close'].rolling(window=self.params['sma_short']).mean()
        df['_sma20'] = df['close'].rolling(window=self.params['sma_long']).mean()
        return df
    
    def _calc_volume_ma(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算成交量 MA5"""
        df['_volume_ma5'] = df['volume'].rolling(window=self.params['volume_ma_period']).mean()
        return df
    
    def _calc_atr(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        計算 ATR14 (Average True Range)
        修正版：使用 SMA(14) 而非 Wilder 平滑
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # 改用 SMA (簡單移動平均)
        period = self.params['atr_period']
        df['_atr'] = tr.rolling(window=period, min_periods=period).mean()
        
        return df
    
    def _calc_parkinson_volatility(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        計算帕金森波動率
        公式: SQRT((LN(High/Low)^2) / (4*LN(2))) * 1000
        """
        df['_parkinson'] = np.sqrt(
            (np.log(df['high'] / df['low']) ** 2) / (4 * np.log(2))
        ) * 1000
        return df
    
    # =========================================================================
    # 17 個特徵計算
    # =========================================================================
    
    def _calc_rsi(self, series: pd.Series, period: int) -> pd.Series:
        """
        計算 RSI (Relative Strength Index)
        使用 Wilder 平滑法
        範圍: 0~1 (除以100以符合訓練資料)
        """
        delta = series.diff()
        
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        
        avg_gain = self._wilder_smooth(gain, period)
        avg_loss = self._wilder_smooth(loss, period)
        
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        
        # 除以100，範圍改為 0~1
        rsi = rsi / 100
        
        return rsi.fillna(0.5)
    
    def _calc_adx(self, df: pd.DataFrame, period: int) -> pd.Series:
        """
        計算 ADX (Average Directional Index)
        使用標準公式 (+DI/-DI → DX → ADX)，Wilder 平滑
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        # +DM and -DM
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
        
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Smoothed values
        atr = self._wilder_smooth(tr, period)
        plus_di = 100 * self._wilder_smooth(plus_dm, period) / atr
        minus_di = 100 * self._wilder_smooth(minus_dm, period) / atr
        
        # DX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)
        
        # ADX (smoothed DX)
        adx = self._wilder_smooth(dx, period)
        
        return adx.fillna(0)
    
    def _calc_cci(self, df: pd.DataFrame, period: int) -> pd.Series:
        """
        計算 CCI (Commodity Channel Index)
        使用 Lambert 標準定義，常數 = 0.015
        
        修正版 MAD 計算：
        1. 單日偏差 = ABS(TP - TP_SMA20)
        2. MAD20 = AVERAGE(單日偏差, 20期)
        """
        # 計算 Typical Price
        tp = (df['high'] + df['low'] + df['close']) / 3
        
        # SMA of TP
        sma_tp = tp.rolling(window=period, min_periods=period).mean()
        
        # 計算每日偏差 = ABS(TP - TP_SMA)
        daily_deviation = abs(tp - sma_tp)
        
        # MAD = 偏差的移動平均
        mad = daily_deviation.rolling(window=period, min_periods=period).mean()
        
        # 避免除以零
        mad = mad.replace(0, np.nan)
        
        # CCI 計算
        cci = (tp - sma_tp) / (0.015 * mad)
        
        return cci.fillna(0)
    
    def _calc_macd_histogram(self, df: pd.DataFrame) -> pd.Series:
        """
        計算 MACD Histogram (OSC)
        參數: (12, 26, 9)
        
        使用加權收盤價 WClose = (High + Low + 2 * Close) / 4
        """
        fast = self.params['macd_fast']
        slow = self.params['macd_slow']
        signal = self.params['macd_signal']
        
        # 計算加權收盤價
        wclose = (df['high'] + df['low'] + 2 * df['close']) / 4
        
        # 使用 WClose 計算 MACD
        ema_fast = wclose.ewm(span=fast, adjust=False).mean()
        ema_slow = wclose.ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        
        histogram = macd_line - signal_line
        
        return histogram.fillna(0)
    
    def _calc_cost_deviation(self, df: pd.DataFrame) -> pd.Series:
        """
        計算成本乖離力
        平均成本 = SUMPRODUCT(Close[近20], Volume[近20]) / SUM(Volume[近20])
        成本乖離力 = MAX(MIN((((Close-平均成本)/Close*1000)/MAX(Parkinson, 0.5))/3, 10), -10)
        """
        window = self.params['lookback_window']
        result = pd.Series(index=df.index, dtype=float)
        
        for i in range(window - 1, len(df)):
            close_window = df['close'].iloc[i - window + 1:i + 1]
            volume_window = df['volume'].iloc[i - window + 1:i + 1]
            
            vol_sum = volume_window.sum()
            if vol_sum == 0:
                result.iloc[i] = 0
                continue
            
            avg_cost = (close_window * volume_window).sum() / vol_sum
            close_now = df['close'].iloc[i]
            parkinson = df['_parkinson'].iloc[i]
            
            # 避免除以零
            parkinson = max(parkinson, 0.5)
            
            deviation = (((close_now - avg_cost) / close_now * 1000) / parkinson) / 3
            deviation = max(min(deviation, 10), -10)
            
            result.iloc[i] = deviation
        
        return result.fillna(0)
    
    def _calc_sma5_slope(self, df: pd.DataFrame) -> pd.Series:
        """
        計算 5MA 斜率
        公式: ((SMA5[今] - SMA5[前1]) / MAX(ATR, 0.01)) / (1 + ABS(...))
        """
        sma5 = df['_sma5']
        atr = df['_atr'].clip(lower=0.01)
        
        diff = sma5 - sma5.shift(1)
        raw_slope = diff / atr
        slope = raw_slope / (1 + abs(raw_slope))
        
        return slope.fillna(0)
    
    def _calc_channel_position(self, df: pd.DataFrame) -> pd.Series:
        """
        計算通道位置 (布林通道 %B)
        公式: (Close - (SMA20 - 2*STD)) / MAX(4*STD, 0.01)
        """
        window = self.params['lookback_window']
        result = pd.Series(index=df.index, dtype=float)
        
        for i in range(window - 1, len(df)):
            close_window = df['close'].iloc[i - window + 1:i + 1]
            sma20 = close_window.mean()
            std = close_window.std()
            
            close_now = df['close'].iloc[i]
            lower_band = sma20 - 2 * std
            band_width = max(4 * std, 0.01)
            
            position = (close_now - lower_band) / band_width
            result.iloc[i] = position
        
        return result.fillna(0.5)
    
    def _calc_volume_ratio(self, df: pd.DataFrame) -> pd.Series:
        """
        計算交易量能 (相對成交量)
        公式: IF(VolumeMA5=0, 0, Volume/VolumeMA5)
        """
        vol_ma = df['_volume_ma5'].replace(0, np.nan)
        ratio = df['volume'] / vol_ma
        return ratio.fillna(0)
    
    def _calc_engulfing_strength(self, df: pd.DataFrame) -> pd.Series:
        """
        計算吞噬強度
        複雜的 K 棒型態指標
        """
        window = self.params['lookback_window']
        result = pd.Series(index=df.index, dtype=float)
        
        for i in range(4, len(df)):
            # 索引對應: 最新=i, 前1=i-1, 前2=i-2, 前3=i-3
            # Excel: F5=最新, F4=前1, F3=前2, F2=前3
            c_now = df['close'].iloc[i]      # F5 (最新)
            o_now = df['open'].iloc[i]       # C5
            c_prev = df['close'].iloc[i-1]   # F4
            o_prev = df['open'].iloc[i-1]    # C4
            
            atr = max(df['_atr'].iloc[i], 1)
            
            # 計算近20期平均收盤價
            if i >= window - 1:
                avg_close = df['close'].iloc[i - window + 1:i + 1].mean()
            else:
                avg_close = df['close'].iloc[:i + 1].mean()
            
            body_prev = abs(c_prev - o_prev)
            body_now = abs(c_now - o_now)
            
            # 條件檢查
            if body_prev < 5 or np.sign(c_now - o_now) == np.sign(c_prev - o_prev):
                result.iloc[i] = 0
                continue
            
            # 吞噬強度計算
            if body_prev == 0:
                result.iloc[i] = 0
                continue
            
            ratio = body_now / body_prev
            deviation = 1 + abs(c_now - avg_close) / atr
            body_atr_ratio = 1 + body_prev / atr
            
            # 判斷前3根平均實體/ATR是否<0.6
            if i >= 3:
                avg_body = (abs(df['close'].iloc[i-1] - df['open'].iloc[i-1]) +
                           abs(df['close'].iloc[i-2] - df['open'].iloc[i-2]) +
                           abs(df['close'].iloc[i-3] - df['open'].iloc[i-3])) / 3
                multiplier = 0.5 if (avg_body / atr) < 0.6 else 1
            else:
                multiplier = 1
            
            strength = np.sign(c_now - o_now) * np.log(1 + ratio * deviation * body_atr_ratio * multiplier)
            result.iloc[i] = strength
        
        return result.fillna(0)
    
    def _calc_kbar_power(self, df: pd.DataFrame) -> pd.Series:
        """
        計算 K 棒力道
        公式: ((Close-Open)/Open*100 * 過均線加成) / (1 + ABS(...))
        """
        close = df['close']
        open_ = df['open']
        sma20 = df['_sma20']
        
        result = pd.Series(index=df.index, dtype=float)
        
        for i in range(len(df)):
            if pd.isna(sma20.iloc[i]):
                result.iloc[i] = 0
                continue
            
            c = close.iloc[i]
            o = open_.iloc[i]
            s = sma20.iloc[i]
            
            if o == 0:
                result.iloc[i] = 0
                continue
            
            # 基礎力道
            base_power = (c - o) / o * 100
            
            # 過均線加成
            cross_sma = (o - s) * (c - s)
            if cross_sma < 0:
                # 穿越均線
                body = max(abs(c - o), 1)
                multiplier = 1 + abs(c - s) / body
            else:
                multiplier = 1
            
            raw_power = base_power * multiplier
            power = raw_power / (1 + abs(raw_power))
            result.iloc[i] = power
        
        return result.fillna(0)
    
    def _calc_n_pattern(self, df: pd.DataFrame) -> pd.Series:
        """
        計算 N 型態
        修正版：參照位置與 Excel 公式完全對齊
        
        Excel公式邏輯（第21列）：
        - 當前: D21, E21, F21, C21
        - 前1根: D20, E20, F20, C20
        - 當前近20期: AVERAGE(F2:F21)
        - 前1根近20期: AVERAGE(F1:F20)
        """
        result = pd.Series(index=df.index, dtype=float)
        
        # 從第20列開始（Python索引19，因為需要近20期數據）
        for i in range(19, len(df)):
            # 當前列（對應 Excel 的 row）
            d_now = df['high'].iloc[i]
            e_now = df['low'].iloc[i]
            f_now = df['close'].iloc[i]
            c_now = df['open'].iloc[i]
            
            # 前1根
            d_prev = df['high'].iloc[i-1]
            e_prev = df['low'].iloc[i-1]
            f_prev = df['close'].iloc[i-1]
            c_prev = df['open'].iloc[i-1]
            
            atr = max(df['_atr'].iloc[i], 10)
            body_now = abs(f_now - c_now)
            
            # 當前近20期平均（含當前）
            avg_close_now = df['close'].iloc[i-19:i+1].mean()
            
            # 前1根近20期平均（不含當前）
            avg_close_prev = df['close'].iloc[i-20:i].mean() if i >= 20 else df['close'].iloc[:i].mean()
            
            # 條件過濾
            if (d_now - e_now) == 0 or body_now < atr * 0.5:
                result.iloc[i] = 0
                continue
            
            n_value = 0
            
            # 看多 N 型態
            if f_now > avg_close_now:
                if (f_prev < c_prev and           # 前1根是陰線
                    f_now > d_prev and             # 今收 > 前高
                    c_prev > avg_close_prev):      # 前開 > 前1根均線
                    n_value = 2 * (body_now / atr)
            
            # 看空 N 型態
            elif f_now < avg_close_now:
                if (f_prev > c_prev and           # 前1根是陽線
                    f_now < e_prev and             # 今收 < 前低
                    c_prev < avg_close_prev):      # 前開 < 前1根均線
                    n_value = -2 * (body_now / atr)
            
            result.iloc[i] = n_value
        
        return result.fillna(0)
    
    def _calc_three_soldiers(self, df: pd.DataFrame) -> pd.Series:
        """
        計算三兵型態
        連續三根同向 K 棒
        """
        result = pd.Series(index=df.index, dtype=float)
        
        for i in range(3, len(df)):
            c0 = df['close'].iloc[i]      # 最新
            o0 = df['open'].iloc[i]
            c1 = df['close'].iloc[i-1]    # 前1
            o1 = df['open'].iloc[i-1]
            c2 = df['close'].iloc[i-2]    # 前2
            o2 = df['open'].iloc[i-2]
            
            atr = max(df['_atr'].iloc[i], 1)
            
            # 三陽兵
            if c0 > o0 and c1 > o1 and c2 > o2 and c0 > c2:
                result.iloc[i] = (c0 - o2) / atr
            # 三陰兵
            elif c0 < o0 and c1 < o1 and c2 < o2 and c0 < c2:
                result.iloc[i] = (c0 - o2) / atr
            else:
                result.iloc[i] = 0
        
        return result.fillna(0)
    
    def _calc_shadow_reversal(self, df: pd.DataFrame) -> pd.Series:
        """
        計算影線反轉 (長上影線/長下影線)
        修正版：完整6條件公式，與 Excel 完全對齊
        
        對於 Excel 第21列（Python i=20）：
        - F21=當前, F20=前1, F19=前2
        - 條件1: F20 下影線反轉
        - 條件2: F19 下影線反轉
        - 條件3: F21 下影線反轉
        - 條件4: F20 上影線反轉
        - 條件5: F19 上影線反轉
        - 條件6: F21 上影線反轉
        """
        result = pd.Series(index=df.index, dtype=float)
        
        # 從第20列開始（需要前2根+當前）
        for i in range(19, len(df)):
            # 當前 (對應 Excel F{row})
            f_now = df['close'].iloc[i]
            c_now = df['open'].iloc[i]
            d_now = df['high'].iloc[i]
            e_now = df['low'].iloc[i]
            sma20_now = df['_sma20'].iloc[i] if pd.notna(df['_sma20'].iloc[i]) else f_now
            atr_now = max(df['_atr'].iloc[i], 1)
            
            # 前1根 (對應 Excel F{row-1})
            f_prev1 = df['close'].iloc[i-1]
            c_prev1 = df['open'].iloc[i-1]
            d_prev1 = df['high'].iloc[i-1]
            e_prev1 = df['low'].iloc[i-1]
            sma20_prev1 = df['_sma20'].iloc[i-1] if pd.notna(df['_sma20'].iloc[i-1]) else f_prev1
            atr_prev1 = max(df['_atr'].iloc[i-1], 1)
            
            # 前2根 (對應 Excel F{row-2})
            f_prev2 = df['close'].iloc[i-2]
            c_prev2 = df['open'].iloc[i-2]
            d_prev2 = df['high'].iloc[i-2]
            e_prev2 = df['low'].iloc[i-2]
            sma20_prev2 = df['_sma20'].iloc[i-2] if pd.notna(df['_sma20'].iloc[i-2]) else f_prev2
            atr_prev2 = max(df['_atr'].iloc[i-2], 1)
            
            value = 0
            
            # === 下影線反轉（看多） ===
            # 條件1: 前1根下影線 (F{row-1})
            body_prev1 = abs(f_prev1 - c_prev1)
            lower_shadow_prev1 = min(c_prev1, f_prev1) - e_prev1
            if (f_prev1 < sma20_prev1 and 
                lower_shadow_prev1 > body_prev1 and 
                e_now >= e_prev1):
                value = ((lower_shadow_prev1) + (sma20_prev1 - f_prev1) + (f_now - c_prev1)) / atr_prev1
            
            # 條件2: 前2根下影線 (F{row-2})
            elif i >= 20:
                body_prev2 = abs(f_prev2 - c_prev2)
                lower_shadow_prev2 = min(c_prev2, f_prev2) - e_prev2
                if (f_prev2 < sma20_prev2 and 
                    lower_shadow_prev2 > body_prev2 and 
                    e_prev1 >= e_prev2 and 
                    e_now >= e_prev2):
                    value = ((lower_shadow_prev2) + (sma20_prev2 - f_prev2) + (f_now - c_prev2)) / atr_prev2
            
            # 條件3: 當前下影線 (F{row})
            if value == 0:
                body_now = abs(f_now - c_now)
                lower_shadow_now = min(c_now, f_now) - e_now
                if (f_now < sma20_now and 
                    lower_shadow_now > body_now):
                    value = ((lower_shadow_now) + (sma20_now - f_now)) / atr_now
            
            # === 上影線反轉（看空） ===
            if value == 0:
                # 條件4: 前1根上影線 (F{row-1})
                upper_shadow_prev1 = d_prev1 - max(c_prev1, f_prev1)
                if (f_prev1 > sma20_prev1 and 
                    upper_shadow_prev1 > body_prev1 and 
                    d_now <= d_prev1):
                    value = ((-1 * (upper_shadow_prev1 + (f_prev1 - sma20_prev1))) + (f_now - c_prev1)) / atr_prev1
                
                # 條件5: 前2根上影線 (F{row-2})
                elif i >= 20:
                    upper_shadow_prev2 = d_prev2 - max(c_prev2, f_prev2)
                    if (f_prev2 > sma20_prev2 and 
                        upper_shadow_prev2 > body_prev2 and 
                        d_prev1 <= d_prev2 and 
                        d_now <= d_prev2):
                        value = ((-1 * (upper_shadow_prev2 + (f_prev2 - sma20_prev2))) + (f_now - c_prev2)) / atr_prev2
                
                # 條件6: 當前上影線 (F{row})
                if value == 0:
                    upper_shadow_now = d_now - max(c_now, f_now)
                    if (f_now > sma20_now and 
                        upper_shadow_now > body_now):
                        value = -1 * ((upper_shadow_now) + (f_now - sma20_now)) / atr_now
            
            result.iloc[i] = value
        
        return result.fillna(0)
    
    def _calc_threek_reversal(self, df: pd.DataFrame) -> pd.Series:
        """
        計算 3K 反轉型態
        3 根 K 棒的反轉訊號
        """
        result = pd.Series(index=df.index, dtype=float)
        
        for i in range(3, len(df)):
            c0 = df['close'].iloc[i]      # 最新 (F4)
            o0 = df['open'].iloc[i]
            c2 = df['close'].iloc[i-2]    # 前2 (F2)
            o2 = df['open'].iloc[i-2]
            
            sma20 = df['_sma20'].iloc[i] if pd.notna(df['_sma20'].iloc[i]) else c0
            atr = max(df['_atr'].iloc[i], 1)
            
            mid_price = (c2 + o2) / 2
            
            value = 0
            
            # 看多反轉
            if o2 > c2 and (o2 - c2) > 5:  # F2 是陰線且實體>5
                if c0 > o0 and c0 < sma20:  # F4 是陽線且在均線下
                    if c0 > mid_price:  # F4 收在 F2 中點以上
                        up_ratio = (c0 - c2) / (o2 - c2) if (o2 - c2) != 0 else 0
                        deviation = abs(sma20 - c0) / atr
                        value = up_ratio + deviation
            
            # 看空反轉
            elif c2 > o2 and (c2 - o2) > 5:  # F2 是陽線且實體>5
                if c0 < o0 and c0 > sma20:  # F4 是陰線且在均線上
                    if c0 < mid_price:  # F4 收在 F2 中點以下
                        down_ratio = (c2 - c0) / (c2 - o2) if (c2 - o2) != 0 else 0
                        deviation = abs(c0 - sma20) / atr
                        value = -1 * (down_ratio + deviation)
            
            result.iloc[i] = value
        
        return result.fillna(0)
    
    # =========================================================================
    # 輔助函數
    # =========================================================================
    
    def _wilder_smooth(self, series: pd.Series, period: int) -> pd.Series:
        """
        Wilder 平滑法 (RMA)
        等同於 EWM with alpha = 1/period
        """
        return series.ewm(alpha=1/period, adjust=False).mean()


if __name__ == "__main__":
    # 測試程式碼
    print("特徵計算器測試")
    print(f"特徵數量: {len(FEATURE_NAMES)}")
    print(f"特徵名稱: {FEATURE_NAMES}")
