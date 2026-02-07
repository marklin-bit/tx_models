# -*- coding: utf-8 -*-
"""
LINE Bot 通知模組
當買進訊號信心度 > 60% 時，推播訊息給所有好友
"""

import requests
from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class LineNotifier:
    """LINE Messaging API 推播通知"""
    
    OAUTH_URL = "https://api.line.me/v2/oauth/accessToken"
    BROADCAST_URL = "https://api.line.me/v2/bot/message/broadcast"
    
    def __init__(self, channel_id: str, channel_secret: str):
        self.channel_id = channel_id
        self.channel_secret = channel_secret
        self._access_token = None
        self._sent_keys = set()  # 避免同一訊號重複發送（key = timestamp_target）
    
    def _get_access_token(self) -> str:
        """用 Channel ID + Secret 取得短期 Access Token"""
        if self._access_token:
            return self._access_token
        
        try:
            resp = requests.post(self.OAUTH_URL, data={
                "grant_type": "client_credentials",
                "client_id": self.channel_id,
                "client_secret": self.channel_secret,
            }, timeout=10)
            
            if resp.status_code == 200:
                self._access_token = resp.json().get("access_token")
                return self._access_token
            else:
                print(f"[LINE] 取得 Token 失敗: {resp.status_code} {resp.text}")
                return None
        except Exception as e:
            print(f"[LINE] Token 請求錯誤: {e}")
            return None
    
    def broadcast(self, message: str) -> bool:
        """推播文字訊息給所有好友"""
        token = self._get_access_token()
        if not token:
            print("[LINE] 無法取得 Access Token，跳過推播")
            return False
        
        try:
            resp = requests.post(
                self.BROADCAST_URL,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                json={
                    "messages": [{"type": "text", "text": message}]
                },
                timeout=10,
            )
            
            if resp.status_code == 200:
                print(f"[LINE] 推播成功")
                return True
            else:
                print(f"[LINE] 推播失敗: {resp.status_code} {resp.text}")
                return False
        except Exception as e:
            print(f"[LINE] 推播錯誤: {e}")
            return False
    
    def format_signal_message(self, time_str: str, close: float,
                               lights: list,
                               long_entry_prob, short_entry_prob) -> str:
        """
        格式化訊號推播訊息
        
        Args:
            time_str: K棒時間 (HH:MM)
            close: 收盤價
            lights: 4個燈號顏色 ['red','gray','green','gray']
            long_entry_prob: 多單買進機率
            short_entry_prob: 空單買進機率
        """
        # 燈號
        light_icons = []
        for c in lights:
            if c == 'red':
                light_icons.append('🔴')
            elif c == 'green':
                light_icons.append('🟢')
            else:
                light_icons.append('⚪')
        lights_str = ''.join(light_icons)
        
        # 多單訊號
        long_str = self._format_prob(long_entry_prob, "多")
        short_str = self._format_prob(short_entry_prob, "空")
        
        lines = [
            "📊 TX 訊號通知",
            f"⏰ {time_str}  |  收盤 {close:.0f}",
            f"🚦 {lights_str}",
            "",
        ]
        
        if long_str:
            lines.append(f"🔺 多單買進: {long_str}")
        if short_str:
            lines.append(f"🔻 空單買進: {short_str}")
        
        return "\n".join(lines)
    
    def _format_prob(self, prob, label: str) -> str:
        """格式化機率文字"""
        if prob is None or prob <= 0.60:
            return ""
        
        if prob > 0.80:
            return f"🔥 {prob:.0%} (強烈)"
        elif prob > 0.70:
            return f"⚡ {prob:.0%} (中等)"
        else:
            return f"💡 {prob:.0%} (一般)"
    
    def check_and_notify(self, time_str: str, close: float,
                          lights: list,
                          long_entry_prob, short_entry_prob,
                          timestamp_key: int = None):
        """
        檢查是否需要發送通知（信心度 > 60%）
        
        Args:
            timestamp_key: 用來避免重複發送的唯一識別碼
        """
        # 檢查是否有 > 60% 的訊號
        has_long = long_entry_prob is not None and long_entry_prob > 0.60
        has_short = short_entry_prob is not None and short_entry_prob > 0.60
        
        if not has_long and not has_short:
            return False
        
        # 避免重複發送
        if timestamp_key:
            sig_type = ""
            if has_long:
                sig_type += "L"
            if has_short:
                sig_type += "S"
            key = f"{timestamp_key}_{sig_type}"
            if key in self._sent_keys:
                return False
            self._sent_keys.add(key)
            # 只保留最近 500 筆
            if len(self._sent_keys) > 500:
                self._sent_keys = set(list(self._sent_keys)[-300:])
        
        # 組合訊息並發送
        msg = self.format_signal_message(
            time_str, close, lights, long_entry_prob, short_entry_prob
        )
        return self.broadcast(msg)
    
    def send_test(self) -> bool:
        """發送測試訊息"""
        now = datetime.now().strftime("%H:%M")
        test_msg = self.format_signal_message(
            time_str=now,
            close=22850,
            lights=['red', 'gray', 'red', 'gray'],
            long_entry_prob=0.73,
            short_entry_prob=None,
        )
        test_msg += "\n\n✅ 這是測試訊息，LINE通知功能正常！"
        return self.broadcast(test_msg)
