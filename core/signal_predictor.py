# -*- coding: utf-8 -*-
"""
訊號預測模組
負責使用模型進行預測並生成交易訊號
"""

import numpy as np
import pandas as pd
import xgboost as xgb
from typing import Dict, List, Optional, Tuple
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import THRESHOLDS, FEATURE_NAMES
from core.model_loader import ModelLoader, TARGET_NAMES


# =============================================================================
# 特徵名稱映射：程式碼英文名 → 模型訓練時的中文名
# 模型是用中文特徵名訓練的，predict 時必須用相同的名稱
# =============================================================================
MODEL_FEATURE_NAMES = [
    "RSI 14",           # RSI14
    "ADX14",            # ADX14
    "CCI20",            # CCI20
    "OSC",              # OSC
    "ATR14",            # ATR14
    "帕金森波動率",      # Parkinson_Volatility
    "成本乖離力",        # Cost_Deviation
    "RSI標準化",         # RSI_Normalized
    "5MA斜率",           # SMA5_Slope
    "通道位置",          # Channel_Position
    "交易量能",          # Volume_Ratio
    "吞噬強度",          # Engulfing_Strength
    "k棒力道",           # Kbar_Power
    "N型態",             # N_Pattern
    "三兵",              # Three_Soldiers
    "影線反轉",          # Shadow_Reversal
    "3k反轉",            # ThreeK_Reversal
]

# 建立映射字典
CODE_TO_MODEL_NAME = dict(zip(FEATURE_NAMES, MODEL_FEATURE_NAMES))


class SignalPredictor:
    """
    訊號預測器
    使用集成模型進行 Soft Voting 預測
    """
    
    def __init__(self, model_loader: ModelLoader = None):
        self.model_loader = model_loader or ModelLoader()
        self.thresholds = THRESHOLDS
        self.feature_names = FEATURE_NAMES
        self.model_feature_names = MODEL_FEATURE_NAMES
        
        # 持單狀態
        self.position_state = {
            'long': False,
            'short': False,
            'long_entry_time': None,
            'short_entry_time': None,
        }
    
    def load_models(self) -> bool:
        return self.model_loader.load_all()
    
    def set_position(self, position_type: str, is_holding: bool, 
                     entry_time: Optional[str] = None):
        if position_type in ['long', 'short']:
            self.position_state[position_type] = is_holding
            self.position_state[f'{position_type}_entry_time'] = entry_time if is_holding else None
    
    def get_position_state(self) -> dict:
        return self.position_state.copy()
    
    def predict_single(self, features: np.ndarray, target: str) -> float:
        """
        對單一目標進行預測
        
        Args:
            features: 特徵陣列 (1, 17)
            target: 目標名稱
        
        Returns:
            Soft Voting 後的信心分數 (0.0 ~ 1.0)
        """
        models = self.model_loader.get_models(target)
        
        if not models:
            return 0.0
        
        # 使用模型訓練時的中文特徵名稱建立 DMatrix
        dmatrix = xgb.DMatrix(features, feature_names=self.model_feature_names)
        
        probabilities = []
        for model in models:
            try:
                prob = model.predict(dmatrix)[0]
                probabilities.append(prob)
            except Exception as e:
                print(f"預測錯誤 ({target}): {e}")
                continue
        
        if not probabilities:
            return 0.0
        
        avg_prob = sum(probabilities) / len(probabilities)
        return float(avg_prob)
    
    def predict_all(self, features: np.ndarray) -> Dict[str, float]:
        """對所有目標進行預測"""
        results = {}
        
        results['long_entry'] = self.predict_single(features, 'long_entry')
        results['short_entry'] = self.predict_single(features, 'short_entry')
        
        if self.position_state['long']:
            results['long_exit'] = self.predict_single(features, 'long_exit')
        else:
            results['long_exit'] = 0.0
        
        if self.position_state['short']:
            results['short_exit'] = self.predict_single(features, 'short_exit')
        else:
            results['short_exit'] = 0.0
        
        return results
    
    def get_signals(self, predictions: Dict[str, float]) -> Dict[str, dict]:
        """根據預測結果生成交易訊號"""
        signals = {}
        
        for target in ['long_entry', 'short_entry']:
            prob = predictions.get(target, 0.0)
            signal_info = {
                'probability': prob,
                'signal': False,
                'level': 0,
                'level_text': '',
            }
            
            if prob > self.thresholds['entry']['level_3']:
                signal_info['signal'] = True
                signal_info['level'] = 3
                signal_info['level_text'] = '強烈'
            elif prob > self.thresholds['entry']['level_2']:
                signal_info['signal'] = True
                signal_info['level'] = 2
                signal_info['level_text'] = '中等'
            elif prob > self.thresholds['entry']['level_1']:
                signal_info['signal'] = True
                signal_info['level'] = 1
                signal_info['level_text'] = '一般'
            
            signals[target] = signal_info
        
        for target in ['long_exit', 'short_exit']:
            prob = predictions.get(target, 0.0)
            signal_info = {
                'probability': prob,
                'signal': False,
                'level': 0,
                'level_text': '',
            }
            
            if prob > self.thresholds['exit']['level_1']:
                signal_info['signal'] = True
                signal_info['level'] = 1
                signal_info['level_text'] = '出場'
            
            signals[target] = signal_info
        
        return signals
    
    def predict_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """對整個 DataFrame 進行預測並添加訊號欄位"""
        result = df.copy()
        
        for target in ['long_entry', 'long_exit', 'short_entry', 'short_exit']:
            result[f'{target}_prob'] = 0.0
            result[f'{target}_signal'] = ''
        
        for idx in range(len(result)):
            try:
                if pd.isna(result[self.feature_names].iloc[idx]).any():
                    continue
                
                features = result[self.feature_names].iloc[idx].values.reshape(1, -1)
                
                for target in ['long_entry', 'short_entry']:
                    prob = self.predict_single(features, target)
                    result.loc[result.index[idx], f'{target}_prob'] = prob
                    
                    if prob > self.thresholds['entry']['level_3']:
                        result.loc[result.index[idx], f'{target}_signal'] = '強烈'
                    elif prob > self.thresholds['entry']['level_2']:
                        result.loc[result.index[idx], f'{target}_signal'] = '中等'
                    elif prob > self.thresholds['entry']['level_1']:
                        result.loc[result.index[idx], f'{target}_signal'] = '一般'
                
                if self.position_state['long']:
                    prob = self.predict_single(features, 'long_exit')
                    result.loc[result.index[idx], 'long_exit_prob'] = prob
                    if prob > self.thresholds['exit']['level_1']:
                        result.loc[result.index[idx], 'long_exit_signal'] = '出場'
                
                if self.position_state['short']:
                    prob = self.predict_single(features, 'short_exit')
                    result.loc[result.index[idx], 'short_exit_prob'] = prob
                    if prob > self.thresholds['exit']['level_1']:
                        result.loc[result.index[idx], 'short_exit_signal'] = '出場'
                        
            except Exception as e:
                print(f"預測第 {idx} 列時發生錯誤: {e}")
                continue
        
        return result
    
    def get_latest_signals(self, df: pd.DataFrame) -> dict:
        """取得最新一列的訊號摘要"""
        if df.empty:
            return {'error': '無資料'}
        
        try:
            features = df[self.feature_names].iloc[-1].values.reshape(1, -1)
            
            if np.any(np.isnan(features)):
                return {'error': '特徵值包含 NaN'}
            
            predictions = self.predict_all(features)
            signals = self.get_signals(predictions)
            
            summary = {
                'datetime': df['datetime'].iloc[-1] if 'datetime' in df.columns else None,
                'close': df['close'].iloc[-1] if 'close' in df.columns else None,
                'predictions': predictions,
                'signals': signals,
                'position_state': self.position_state.copy(),
            }
            
            active_signals = []
            for target, info in signals.items():
                if info['signal']:
                    active_signals.append({
                        'target': target,
                        'name': TARGET_NAMES.get(target, target),
                        'probability': info['probability'],
                        'level_text': info['level_text']
                    })
            
            summary['active_signals'] = active_signals
            return summary
            
        except Exception as e:
            return {'error': str(e)}


SIGNAL_COLORS = {
    'long_entry': {'強烈': '#FF0000', '中等': '#FF6600', '一般': '#FFCC00'},
    'long_exit': {'出場': '#00AA00'},
    'short_entry': {'強烈': '#00FF00', '中等': '#00CC66', '一般': '#009999'},
    'short_exit': {'出場': '#AA0000'}
}


if __name__ == "__main__":
    print("訊號預測器測試")
    print(f"程式碼特徵名: {FEATURE_NAMES}")
    print(f"模型特徵名:   {MODEL_FEATURE_NAMES}")
    print(f"名稱映射:")
    for code_name, model_name in CODE_TO_MODEL_NAME.items():
        marker = " *" if code_name != model_name else ""
        print(f"  {code_name} -> {model_name}{marker}")
