# -*- coding: utf-8 -*-
"""
模型載入模組
負責載入和管理 XGBoost 模型
"""

import xgboost as xgb
import os
import sys
from typing import Dict, List, Optional

# 添加父目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MODEL_FILES


class ModelLoader:
    """
    XGBoost 模型載入器
    管理 4 個目標各 5 個模型的集成
    """
    
    def __init__(self, model_files: Dict[str, List[str]] = None):
        """
        初始化模型載入器
        
        Args:
            model_files: 模型檔案路徑字典，格式如 MODEL_FILES
        """
        self.model_files = model_files or MODEL_FILES
        self.models: Dict[str, List[xgb.Booster]] = {
            'long_entry': [],
            'long_exit': [],
            'short_entry': [],
            'short_exit': []
        }
        self.loaded = False
        self.load_errors: List[str] = []
    
    def load_all(self) -> bool:
        """
        載入所有模型
        
        Returns:
            是否全部載入成功
        """
        self.load_errors = []
        success = True
        
        for target, paths in self.model_files.items():
            self.models[target] = []
            for path in paths:
                model = self._load_single_model(path)
                if model is not None:
                    self.models[target].append(model)
                else:
                    success = False
                    self.load_errors.append(f"無法載入: {path}")
        
        self.loaded = success
        return success
    
    def _load_single_model(self, path: str) -> Optional[xgb.Booster]:
        """
        載入單一模型
        
        Args:
            path: 模型檔案路徑
        
        Returns:
            XGBoost Booster 物件，若失敗則返回 None
        """
        if not os.path.exists(path):
            print(f"模型檔案不存在: {path}")
            return None
        
        try:
            model = xgb.Booster()
            model.load_model(path)
            return model
        except Exception as e:
            print(f"載入模型失敗 {path}: {e}")
            return None
    
    def get_models(self, target: str) -> List[xgb.Booster]:
        """
        取得指定目標的模型列表
        
        Args:
            target: 目標名稱 (long_entry, long_exit, short_entry, short_exit)
        
        Returns:
            模型列表
        """
        return self.models.get(target, [])
    
    def get_model_count(self) -> Dict[str, int]:
        """
        取得各目標的模型數量
        
        Returns:
            {target: count} 字典
        """
        return {target: len(models) for target, models in self.models.items()}
    
    def is_ready(self) -> bool:
        """
        檢查所有模型是否已就緒
        
        Returns:
            是否所有目標都有 5 個模型
        """
        for target, models in self.models.items():
            if len(models) != 5:
                return False
        return True
    
    def get_status(self) -> dict:
        """
        取得模型載入狀態
        
        Returns:
            狀態資訊字典
        """
        counts = self.get_model_count()
        total = sum(counts.values())
        
        return {
            'loaded': self.loaded,
            'ready': self.is_ready(),
            'total_models': total,
            'expected': 20,
            'by_target': counts,
            'errors': self.load_errors
        }


# 目標名稱對應中文
TARGET_NAMES = {
    'long_entry': '多單買進',
    'long_exit': '多單賣出',
    'short_entry': '空單買進',
    'short_exit': '空單賣出'
}


if __name__ == "__main__":
    # 測試程式碼
    loader = ModelLoader()
    print("開始載入模型...")
    
    success = loader.load_all()
    status = loader.get_status()
    
    print(f"\n載入結果: {'成功' if success else '失敗'}")
    print(f"總模型數: {status['total_models']}/{status['expected']}")
    print(f"各目標模型數:")
    for target, count in status['by_target'].items():
        print(f"  - {TARGET_NAMES.get(target, target)}: {count}/5")
    
    if status['errors']:
        print(f"\n錯誤訊息:")
        for err in status['errors']:
            print(f"  - {err}")
