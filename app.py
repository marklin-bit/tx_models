# -*- coding: utf-8 -*-
"""
TX 台指期當沖訊號監控系統 V2
Streamlit Web Application - 完整改版
"""

import streamlit as st
import streamlit.components.v1 as st_components
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time as dtime
import time
import os
import sys
import plotly.graph_objects as go

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    PAGE_CONFIG, THRESHOLDS, FEATURE_NAMES,
    DATABASE_PATH, DATABASE_DIR, LINE_CONFIG
)
from core.db_manager import DBManager
from core.data_fetcher import DataFetcher
from core.feature_calculator import FeatureCalculator
from core.model_loader import ModelLoader, TARGET_NAMES
from core.signal_predictor import SignalPredictor
from core.scheduler import DataScheduler
from core.line_notifier import LineNotifier

# =============================================================================
# Page Config
# =============================================================================
st.set_page_config(
    page_title="TX 訊號監控",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =============================================================================
# CSS
# =============================================================================
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    }
    .main .block-container {
        padding-top: 0.5rem;
        padding-bottom: 1rem;
        max-width: 100%;
    }
    
    /* 訊號卡片 */
    .signal-card {
        background: rgba(255,255,255,0.05);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 1.2rem;
        margin: 0.3rem;
        border: 1px solid rgba(255,255,255,0.1);
        transition: all 0.3s ease;
        text-align: center;
    }
    .signal-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.3);
    }
    .card-long-entry { background: linear-gradient(135deg, rgba(244,67,54,0.2), rgba(244,67,54,0.1)); border-left: 4px solid #f44336; }
    .card-long-entry.active { background: linear-gradient(135deg, rgba(244,67,54,0.4), rgba(244,67,54,0.2)); box-shadow: 0 0 30px rgba(244,67,54,0.3); animation: pulse-red 2s infinite; }
    .card-short-entry { background: linear-gradient(135deg, rgba(76,175,80,0.2), rgba(76,175,80,0.1)); border-left: 4px solid #4caf50; }
    .card-short-entry.active { background: linear-gradient(135deg, rgba(76,175,80,0.4), rgba(76,175,80,0.2)); box-shadow: 0 0 30px rgba(76,175,80,0.3); animation: pulse-green 2s infinite; }
    .card-exit { background: linear-gradient(135deg, rgba(255,152,0,0.2), rgba(255,152,0,0.1)); border-left: 4px solid #ff9800; }
    .card-exit.active { background: linear-gradient(135deg, rgba(255,152,0,0.4), rgba(255,152,0,0.2)); box-shadow: 0 0 30px rgba(255,152,0,0.3); animation: pulse-orange 2s infinite; }
    .card-disabled { opacity: 0.4; }
    
    @keyframes pulse-red { 0%,100% { box-shadow: 0 0 20px rgba(244,67,54,0.3); } 50% { box-shadow: 0 0 40px rgba(244,67,54,0.5); } }
    @keyframes pulse-green { 0%,100% { box-shadow: 0 0 20px rgba(76,175,80,0.3); } 50% { box-shadow: 0 0 40px rgba(76,175,80,0.5); } }
    @keyframes pulse-orange { 0%,100% { box-shadow: 0 0 20px rgba(255,152,0,0.3); } 50% { box-shadow: 0 0 40px rgba(255,152,0,0.5); } }
    
    .card-title { color: rgba(255,255,255,0.7); font-size: 0.85rem; font-weight: 500; margin-bottom: 0.3rem; text-transform: uppercase; letter-spacing: 1px; }
    .card-value { color: #fff; font-size: 2.2rem; font-weight: 700; margin: 0.3rem 0; text-shadow: 0 2px 10px rgba(0,0,0,0.3); }
    .card-level { font-size: 0.9rem; font-weight: 600; padding: 3px 10px; border-radius: 20px; display: inline-block; }
    .level-strong { background: #f44336; color: white; }
    .level-medium { background: #ff9800; color: white; }
    .level-weak { background: #ffc107; color: #333; }
    .level-exit { background: #4caf50; color: white; }
    .level-none { background: rgba(255,255,255,0.1); color: rgba(255,255,255,0.5); }
    
    /* 表格內指示燈 */
    .tbl-dot {
        display: inline-block;
        width: 10px; height: 10px;
        border-radius: 50%;
        background: #3a3a4a;
        margin: 0 2px;
        vertical-align: middle;
    }
    .tbl-dot-red { background: #ff4444; box-shadow: 0 0 5px rgba(255,68,68,0.7); }
    .tbl-dot-green { background: #44cc44; box-shadow: 0 0 5px rgba(68,204,68,0.7); }
    
    /* 訊號表格 */
    .signal-table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
    .signal-table th {
        background: rgba(255,255,255,0.1);
        color: rgba(255,255,255,0.8);
        padding: 8px 10px;
        text-align: center;
        border-bottom: 2px solid rgba(255,255,255,0.15);
        font-weight: 600;
        position: sticky; top: 0; z-index: 1;
    }
    .signal-table td {
        padding: 6px 10px;
        text-align: center;
        border-bottom: 1px solid rgba(255,255,255,0.05);
        color: rgba(255,255,255,0.85);
    }
    .signal-table tr:hover td { background: rgba(255,255,255,0.05) !important; }
    .table-container { max-height: 450px; overflow-y: auto; border-radius: 12px; border: 1px solid rgba(255,255,255,0.08); }
    
    .time-pink { background-color: rgba(255,120,150,0.2); }
    .time-yellow { background-color: rgba(255,220,100,0.15); }
    .time-gray { background-color: rgba(180,180,200,0.06); }
    
    .sig-fire { color: #ff4444; font-weight: 700; }
    .sig-bolt { color: #ff8800; font-weight: 600; }
    .sig-bulb { color: #ffcc00; font-weight: 500; }
    .sig-exit-red { color: #ff6666; font-weight: 700; }
    .sig-exit-green { color: #66cc66; font-weight: 700; }
    .sig-dim { color: rgba(255,255,255,0.35); }
    
    /* 按鈕 */
    .stButton > button {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white; border: none; border-radius: 25px;
        padding: 0.4rem 1.5rem; font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton > button:hover { transform: scale(1.05); box-shadow: 0 5px 20px rgba(102,126,234,0.4); }
    
    /* 狀態列 */
    .status-bar {
        display: flex; justify-content: space-between; align-items: center;
        padding: 0.5rem 1rem; background: rgba(255,255,255,0.03);
        border-radius: 10px; margin-top: 0.5rem;
    }
    .status-bar span { color: rgba(255,255,255,0.6); font-size: 0.85rem; }
    
    /* Tab 頁籤 */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background: rgba(255,255,255,0.05);
        border-radius: 12px 12px 0 0;
        padding: 10px 24px;
        color: rgba(255,255,255,0.6);
    }
    .stTabs [aria-selected="true"] {
        background: rgba(255,255,255,0.12);
        color: #fff;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# Helper Functions
# =============================================================================

def is_us_dst(date_val):
    """判斷是否為美國夏令時間"""
    year = date_val.year if hasattr(date_val, 'year') else datetime.now().year
    
    # Second Sunday of March
    march_1 = datetime(year, 3, 1)
    days_to_sun = (6 - march_1.weekday()) % 7
    first_sun_march = march_1 + timedelta(days=days_to_sun)
    second_sun_march = first_sun_march + timedelta(days=7)
    
    # First Sunday of November
    nov_1 = datetime(year, 11, 1)
    days_to_sun = (6 - nov_1.weekday()) % 7
    first_sun_nov = nov_1 + timedelta(days=days_to_sun)
    
    d = date_val if isinstance(date_val, datetime) else datetime.combine(date_val, dtime())
    d = d.replace(hour=0, minute=0, second=0, microsecond=0)
    return second_sun_march <= d < first_sun_nov


def get_time_period_class(dt_val):
    """根據日期時間取得時段CSS class"""
    if not isinstance(dt_val, (datetime, pd.Timestamp)):
        return 'time-gray'
    
    t_min = dt_val.hour * 60 + dt_val.minute
    us_open_min = (21 * 60 + 30) if is_us_dst(dt_val) else (22 * 60 + 30)
    diff_us = t_min - us_open_min
    
    # Pink: 開收盤波動時段
    if 8*60+45 <= t_min <= 9*60+5:
        return 'time-pink'
    if 15*60 <= t_min <= 15*60+20:
        return 'time-pink'
    if 0 <= diff_us <= 20:
        return 'time-pink'
    
    # Yellow: 主要交易時段
    if 9*60+10 <= t_min <= 12*60+45:
        return 'time-yellow'
    if 15*60+25 <= t_min <= 17*60:
        return 'time-yellow'
    if 0 <= diff_us <= 120:
        return 'time-yellow'
    if -60 <= diff_us < 0:
        return 'time-yellow'
    
    return 'time-gray'


# 指示燈閾值設定 (A-F 個別指標)
INDICATOR_CHECKS = [
    ('Engulfing_Strength', 1.3, 'both'),   # A
    ('Kbar_Power', 0.17, 'both'),           # B
    ('N_Pattern', 0, 'sign'),               # C: >0 red, <0 green
    ('Three_Soldiers', 3.3, 'red'),         # D: red only
    ('Shadow_Reversal', 3.5, 'both'),       # E
    ('ThreeK_Reversal', 1.5, 'both'),       # F
]


def _count_signals(features_dict, multiplier=1.0):
    """計算指定閾值倍率下的多空觸發數"""
    bull, bear = 0, 0
    for feat, th, mode in INDICATOR_CHECKS:
        val = features_dict.get(feat, 0)
        if val is None or (isinstance(val, float) and (np.isnan(val) or pd.isna(val))):
            val = 0
        scaled = th * multiplier
        if mode == 'sign':
            if val > 0: bull += 1
            elif val < 0: bear += 1
        elif mode == 'red':
            if val >= max(scaled, 0.01): bull += 1
        else:
            if val >= max(scaled, 0.001): bull += 1
            if val <= -max(scaled, 0.001): bear += 1
    return bull, bear


def calc_row_lights(features_dict):
    """
    計算每列4個指示燈顏色（多空分離）
    燈1: 多單個別訊號 — A-F 任一觸發多單（全閾值）→ 紅燈
    燈2: 空單個別訊號 — A-F 任一觸發空單（全閾值）→ 綠燈
    燈3: 綜合多單 — H/I/J 任一達標 → 紅燈
    燈4: 綜合空單 — H/I/J 任一達標 → 綠燈
    """
    # 個別指標 (full threshold)
    b1, g1 = _count_signals(features_dict, 1.0)
    
    # 綜合訊號：任一層級達標即亮燈
    # H: 2項以上 ×0.6 | I: 3項以上 ×0.3 | J: 4項以上 ×0.2
    composite_bull = False
    composite_bear = False
    for mult, min_n in [(0.6, 2), (0.3, 3), (0.2, 4)]:
        bc, gc = _count_signals(features_dict, mult)
        if bc >= min_n:
            composite_bull = True
        if gc >= min_n:
            composite_bear = True
    
    return [
        'red' if b1 > 0 else 'gray',           # 燈1: 多單個別
        'green' if g1 > 0 else 'gray',          # 燈2: 空單個別
        'red' if composite_bull else 'gray',     # 燈3: 綜合多單
        'green' if composite_bear else 'gray',   # 燈4: 綜合空單
    ]


def render_row_lights_html(lights):
    """渲染單列的4個指示燈"""
    dots = ''
    for color in lights:
        cls = f' tbl-dot-{color}' if color != 'gray' else ''
        dots += f'<span class="tbl-dot{cls}"></span>'
    return dots


def calc_predictions_for_day(day_df, predictor):
    """計算一天的所有預測"""
    results = []
    targets = ['long_entry', 'short_entry', 'long_exit', 'short_exit']
    for idx in day_df.index:
        row_result = {'_idx': idx}
        try:
            feat_vals = day_df.loc[idx, FEATURE_NAMES].values
            if not np.any(pd.isna(feat_vals)):
                features = feat_vals.astype(float).reshape(1, -1)
                for target in targets:
                    prob = predictor.predict_single(features, target)
                    # 確保回傳值有效（非 NaN）
                    if prob is None or (isinstance(prob, float) and np.isnan(prob)):
                        row_result[target] = None
                    else:
                        row_result[target] = prob
            else:
                for t in targets:
                    row_result[t] = None
        except Exception:
            for t in targets:
                row_result[t] = None
        results.append(row_result)
    
    return pd.DataFrame(results).set_index('_idx')


def format_signal_cell(prob, sig_type='entry'):
    """格式化訊號儲存格"""
    if prob is None or (isinstance(prob, float) and np.isnan(prob)):
        return '<span class="sig-dim">-</span>'
    
    if sig_type == 'entry':
        if prob > THRESHOLDS['entry']['level_3']:
            return f'<span class="sig-fire">&#x1F525; {prob:.0%}</span>'
        elif prob > THRESHOLDS['entry']['level_2']:
            return f'<span class="sig-bolt">&#x26A1; {prob:.0%}</span>'
        elif prob > THRESHOLDS['entry']['level_1']:
            return f'<span class="sig-bulb">&#x1F4A1; {prob:.0%}</span>'
        else:
            return f'<span class="sig-dim">{prob:.0%}</span>'
    else:  # exit
        if prob > THRESHOLDS['exit']['level_1']:
            return f'<span class="sig-exit-red">&#x1F6A8; {prob:.0%}</span>'
        else:
            return f'<span class="sig-dim">{prob:.0%}</span>'


def build_signal_table_html(day_df, preds_df, show_exit_long=False, show_exit_short=False):
    """建構訊號表格 HTML（含每列4個指示燈）"""
    html = '<div class="table-container"><table class="signal-table">'
    html += '<thead><tr><th>時間</th><th>收盤</th><th>燈號</th><th>多買進</th><th>空買進</th><th>多賣出</th><th>空賣出</th></tr></thead>'
    html += '<tbody>'
    
    # 反轉順序（最新在上）
    indices = list(day_df.index)[::-1]
    
    for idx in indices:
        row = day_df.loc[idx]
        dt_val = row.get('datetime')
        time_str = dt_val.strftime('%H:%M') if pd.notna(dt_val) else '--:--'
        close_val = f"{row['close']:.0f}" if pd.notna(row.get('close')) else '-'
        
        time_class = get_time_period_class(dt_val) if pd.notna(dt_val) else 'time-gray'
        
        # 計算該列的指示燈
        feat_dict = {}
        for f in FEATURE_NAMES:
            v = row.get(f)
            feat_dict[f] = float(v) if pd.notna(v) else 0.0
        lights = calc_row_lights(feat_dict)
        lights_html = render_row_lights_html(lights)
        
        # 取得預測值
        pred_row = preds_df.loc[idx] if idx in preds_df.index else {}
        
        le = pred_row.get('long_entry')
        se = pred_row.get('short_entry')
        lx = pred_row.get('long_exit') if show_exit_long else None
        sx = pred_row.get('short_exit') if show_exit_short else None
        
        no_sig = '<span class="sig-dim">-</span>'
        lx_cell = format_signal_cell(lx, "exit") if show_exit_long else no_sig
        sx_cell = format_signal_cell(sx, "exit") if show_exit_short else no_sig
        
        html += f'<tr class="{time_class}">'
        html += f'<td>{time_str}</td>'
        html += f'<td>{close_val}</td>'
        html += f'<td>{lights_html}</td>'
        html += f'<td>{format_signal_cell(le, "entry")}</td>'
        html += f'<td>{format_signal_cell(se, "entry")}</td>'
        html += f'<td>{lx_cell}</td>'
        html += f'<td>{sx_cell}</td>'
        html += '</tr>'
    
    html += '</tbody></table></div>'
    return html


def build_price_chart(day_df, preds_df):
    """建構收盤價圖表（含訊號標記）"""
    fig = go.Figure()
    
    times = day_df['datetime'].dt.strftime('%H:%M')
    closes = day_df['close']
    
    # 收盤價折線
    fig.add_trace(go.Scatter(
        x=times, y=closes,
        mode='lines',
        name='收盤價',
        line=dict(color='#00e5ff', width=2),
        hovertemplate='%{x}<br>收盤: %{y:.0f}<extra></extra>'
    ))
    
    # 進場訊號標記 — 圖示與表格一致（🔥80% ⚡70% 💡60%）
    # 多單=紅色系(上方) / 空單=綠色系(下方)，用 markers+text 雙層顯示
    # (target, threshold, name, emoji, marker_color, marker_symbol, marker_size, font_size, text_pos)
    signal_configs = [
        ('long_entry',  0.80, '多 🔥80%', '\U0001F525', '#ff4444', 'triangle-up',   20, 16, 'top center'),
        ('long_entry',  0.70, '多 ⚡70%', '\u26A1',     '#ff8800', 'triangle-up',   15, 13, 'top center'),
        ('long_entry',  0.60, '多 💡60%', '\U0001F4A1', '#ffcc00', 'triangle-up',   11, 10, 'top center'),
        ('short_entry', 0.80, '空 🔥80%', '\U0001F525', '#22cc22', 'triangle-down', 20, 16, 'bottom center'),
        ('short_entry', 0.70, '空 ⚡70%', '\u26A1',     '#44bb44', 'triangle-down', 15, 13, 'bottom center'),
        ('short_entry', 0.60, '空 💡60%', '\U0001F4A1', '#77cc77', 'triangle-down', 11, 10, 'bottom center'),
    ]
    
    for target, threshold, name, emoji, mcolor, msymbol, msize, fsize, tpos in signal_configs:
        mask_indices = []
        for idx in day_df.index:
            if idx in preds_df.index:
                prob = preds_df.loc[idx].get(target)
                if prob is not None and not (isinstance(prob, float) and np.isnan(prob)) and prob > threshold:
                    if threshold == 0.80 or (threshold == 0.70 and prob <= 0.80) or (threshold == 0.60 and prob <= 0.70):
                        mask_indices.append(idx)
        
        if mask_indices:
            mask_df = day_df.loc[mask_indices]
            # 底層：彩色三角形 marker（紅=多單 / 綠=空單）
            fig.add_trace(go.Scatter(
                x=mask_df['datetime'].dt.strftime('%H:%M'),
                y=mask_df['close'],
                mode='markers+text',
                name=name,
                marker=dict(symbol=msymbol, size=msize, color=mcolor,
                           line=dict(width=1, color='white'), opacity=0.85),
                text=[emoji] * len(mask_df),
                textposition=tpos,
                textfont=dict(size=fsize),
                hovertemplate=f'{name}<br>%{{x}}<br>收盤: %{{y:.0f}}<extra></extra>'
            ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=380,
        margin=dict(l=50, r=20, t=30, b=40),
        legend=dict(
            orientation='h', yanchor='bottom', y=1.02,
            xanchor='right', x=1, font=dict(size=10)
        ),
        xaxis=dict(
            showgrid=True, gridcolor='rgba(255,255,255,0.05)',
            title=None
        ),
        yaxis=dict(
            showgrid=True, gridcolor='rgba(255,255,255,0.05)',
            title='收盤價'
        ),
        hovermode='x unified'
    )
    
    return fig


# =============================================================================
# Session State & Components
# =============================================================================

def get_last_kbar_boundary():
    """取得最近一根已收盤的 5 分 K 時間邊界"""
    now = datetime.now()
    return now.replace(minute=(now.minute // 5) * 5, second=0, microsecond=0)


def get_next_kbar_boundary():
    """取得下一根 5 分 K 的收盤時間"""
    return get_last_kbar_boundary() + timedelta(minutes=5)


def is_data_stale():
    """
    檢查資料是否過期（是否有新的 5 分 K 收盤了但尚未刷新）
    例：上次刷新 08:06，現在 08:10:03 → 08:10 已收盤 → 需要刷新
    例：上次刷新 08:10:02，現在 08:13 → 08:10 邊界已更新過 → 不需要
    """
    if st.session_state.last_refresh is None:
        return True
    last_boundary = get_last_kbar_boundary()
    return st.session_state.last_refresh < last_boundary


def inject_kbar_auto_refresh():
    """
    注入 JavaScript 計時器，在下一根 5 分 K 收盤後自動刷新頁面
    
    例：現在 08:06:30
      → 下一根 K 棒收盤 = 08:10:00
      → 加 5 秒緩衝（等 API 出新資料）= 08:10:05
      → 等待 = 3 分 35 秒 = 215 秒
      → JavaScript: setTimeout(reload, 215000)
    """
    now = datetime.now()
    next_boundary = get_next_kbar_boundary()
    buffer_seconds = 5  # 等 API 更新
    wait_seconds = (next_boundary - now).total_seconds() + buffer_seconds
    wait_ms = int(max(wait_seconds, 5) * 1000)
    
    st_components.html(
        f'<script>setTimeout(function(){{window.parent.location.reload()}},{wait_ms})</script>',
        height=0,
    )


def init_session_state():
    defaults = {
        'initialized': False,
        'data': pd.DataFrame(),
        'last_refresh': None,
        'position_long': False,
        'position_short': False,
        'long_entry_time': None,
        'short_entry_time': None,
        'auto_refresh': True,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


@st.cache_resource
def load_components():
    if not os.path.exists(DATABASE_DIR):
        os.makedirs(DATABASE_DIR)
    
    db_manager = DBManager()
    data_fetcher = DataFetcher()
    feature_calculator = FeatureCalculator()
    model_loader = ModelLoader()
    model_loader.load_all()
    signal_predictor = SignalPredictor(model_loader)
    
    # 啟動排程器
    scheduler = DataScheduler(db_manager, data_fetcher, feature_calculator)
    scheduler.start()
    
    # 啟動時資料完整性檢查（僅首次）
    if 'integrity_checked' not in st.session_state:
        _startup_integrity_check(db_manager, scheduler)
        st.session_state.integrity_checked = True
    
    # LINE 通知
    line_notifier = None
    if LINE_CONFIG.get('enabled'):
        line_notifier = LineNotifier(
            channel_id=LINE_CONFIG['channel_id'],
            channel_secret=LINE_CONFIG['channel_secret'],
        )
    
    return {
        'db_manager': db_manager,
        'data_fetcher': data_fetcher,
        'feature_calculator': feature_calculator,
        'model_loader': model_loader,
        'signal_predictor': signal_predictor,
        'scheduler': scheduler,
        'line_notifier': line_notifier,
    }


def _startup_integrity_check(db_manager, scheduler):
    """
    應用啟動時的資料完整性防呆檢查。
    
    檢查項目：
      1. 資料缺口（時段缺失）：有日盤→必有夜盤
      2. 特徵完整性（NULL 特徵）
    若發現問題，嘗試從 API 補回。
    """
    try:
        # 檢查資料缺口
        gaps = db_manager.check_data_gaps()
        feat_issues = db_manager.check_feature_completeness()
        
        if gaps or feat_issues:
            print(f"[啟動檢查] 發現 {len(gaps)} 個資料缺口, {len(feat_issues)} 個特徵問題")
            # 觸發排程器的修復流程
            scheduler.validate_and_fill_gaps()
        else:
            print("[啟動檢查] 資料完整性OK")
    except Exception as e:
        print(f"[啟動檢查] 發生錯誤: {e}")


def fetch_and_process_data(components):
    """抓取並處理資料（串聯歷史確保指標連續性）"""
    db = components['db_manager']
    fetcher = components['data_fetcher']
    fc = components['feature_calculator']
    
    # 載入歷史資料（5個交易日）
    db_data = db.load_ohlcv(days=5)
    
    # 從API抓取最新
    api_data = fetcher.fetch_raw()
    
    # 合併
    if not api_data.empty and not db_data.empty:
        combined = pd.concat([db_data, api_data], ignore_index=True)
        combined = combined.drop_duplicates(subset=['timestamp'], keep='last')
        combined = combined.sort_values('timestamp').reset_index(drop=True)
    elif not api_data.empty:
        combined = api_data
    elif not db_data.empty:
        combined = db_data
    else:
        return pd.DataFrame()
    
    # 計算特徵（使用完整歷史資料確保連續性）
    if len(combined) >= 20:
        processed = fc.calculate_all(combined)
    else:
        processed = combined
    
    return processed


def get_day_data(full_df, target_date_str):
    """從完整資料中篩選指定日期"""
    if full_df.empty or 'datetime' not in full_df.columns:
        return pd.DataFrame()
    
    full_df_copy = full_df.copy()
    full_df_copy['_date'] = full_df_copy['datetime'].dt.strftime('%Y-%m-%d')
    day_df = full_df_copy[full_df_copy['_date'] == target_date_str].copy()
    day_df = day_df.drop(columns=['_date'], errors='ignore')
    return day_df


def load_history_data(components, target_date):
    """載入歷史日期資料（確保所有列的特徵都完整）"""
    db = components['db_manager']
    fc = components['feature_calculator']
    
    # 先嘗試載入已存特徵的資料
    day_data = db.load_by_date(target_date, include_features=True)
    
    if not day_data.empty:
        # 檢查「所有列」的「所有特徵」都完整（用 .all() 而非 .any()）
        features_complete = all(
            f in day_data.columns and day_data[f].notna().all()
            for f in FEATURE_NAMES
        )
        if features_complete:
            return day_data
    
    # 若有任何特徵 NULL，載入完整歷史重新計算
    # 使用 5 天完整資料確保 lookback 足夠（SMA20, CCI20, ADX14 等需要）
    all_data = db.load_ohlcv(days=5)
    if all_data.empty:
        return pd.DataFrame()
    
    processed = fc.calculate_all(all_data)
    processed['_date'] = processed['datetime'].dt.strftime('%Y-%m-%d')
    result = processed[processed['_date'] == target_date].copy()
    result = result.drop(columns=['_date'], errors='ignore')
    
    # 重算後存回 DB，修復 NULL 特徵（只存該日期的資料，避免覆寫其他日期）
    if not result.empty:
        db.save_ohlcv(result, include_features=True)
    
    return result


# =============================================================================
# Display Functions
# =============================================================================

def render_signal_card(title, probability, level_text, card_class, is_active, is_disabled=False):
    active_class = "active" if is_active else ""
    disabled_class = "card-disabled" if is_disabled else ""
    
    if is_disabled:
        level_html = '<span class="card-level level-none">未持單</span>'
        prob_display = "--%"
    elif level_text:
        level_map = {'強烈': 'level-strong', '中等': 'level-medium', '一般': 'level-weak', '出場': 'level-exit'}
        level_class = level_map.get(level_text, 'level-none')
        level_html = f'<span class="card-level {level_class}">{level_text}</span>'
        prob_display = f"{probability:.0%}"
    else:
        level_html = '<span class="card-level level-none">無訊號</span>'
        prob_display = f"{probability:.0%}"
    
    return f"""
    <div class="signal-card {card_class} {active_class} {disabled_class}">
        <div class="card-title">{title}</div>
        <div class="card-value">{prob_display}</div>
        {level_html}
    </div>
    """


def display_main_signals(components):
    """顯示訊號卡片"""
    if st.session_state.data.empty or len(st.session_state.data) < 20:
        st.warning("資料載入中或資料不足...")
        return
    
    predictor = components['signal_predictor']
    predictor.set_position('long', st.session_state.position_long)
    predictor.set_position('short', st.session_state.position_short)
    
    try:
        features = st.session_state.data[FEATURE_NAMES].iloc[-1].values.reshape(1, -1)
        if np.any(np.isnan(features)):
            st.error("特徵值包含無效數據")
            return
        predictions = predictor.predict_all(features)
    except Exception as e:
        st.error(f"預測錯誤: {e}")
        return
    
    cols = st.columns(4)
    
    # 多單買進
    prob = predictions.get('long_entry', 0)
    level = '強烈' if prob > 0.8 else '中等' if prob > 0.7 else '一般' if prob > 0.6 else ''
    with cols[0]:
        st.markdown(render_signal_card("多單買進", prob, level, "card-long-entry", bool(level)), unsafe_allow_html=True)
    
    # 多單賣出
    prob = predictions.get('long_exit', 0)
    level = '出場' if prob > 0.85 else ''
    with cols[1]:
        st.markdown(render_signal_card("多單賣出", prob, level, "card-exit", bool(level), not st.session_state.position_long), unsafe_allow_html=True)
    
    # 空單買進
    prob = predictions.get('short_entry', 0)
    level = '強烈' if prob > 0.8 else '中等' if prob > 0.7 else '一般' if prob > 0.6 else ''
    with cols[2]:
        st.markdown(render_signal_card("空單買進", prob, level, "card-short-entry", bool(level)), unsafe_allow_html=True)
    
    # 空單賣出
    prob = predictions.get('short_exit', 0)
    level = '出場' if prob > 0.85 else ''
    with cols[3]:
        st.markdown(render_signal_card("空單賣出", prob, level, "card-exit", bool(level), not st.session_state.position_short), unsafe_allow_html=True)


def display_control_panel(components):
    """控制面板"""
    time_options = ["--:--"]
    if not st.session_state.data.empty and 'datetime' in st.session_state.data.columns:
        today = datetime.now().strftime('%Y-%m-%d')
        today_df = st.session_state.data[
            st.session_state.data['datetime'].dt.strftime('%Y-%m-%d') == today
        ]
        if not today_df.empty:
            time_options = today_df['datetime'].dt.strftime('%H:%M').tolist()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        long_on = st.toggle("持有多單", value=st.session_state.position_long, key="toggle_long")
        if long_on != st.session_state.position_long:
            st.session_state.position_long = long_on
            if not long_on:
                st.session_state.long_entry_time = None
            st.rerun()
    
    with col2:
        if st.session_state.position_long:
            cur = st.session_state.long_entry_time or (time_options[-1] if time_options else "--:--")
            try:
                idx = time_options.index(cur)
            except:
                idx = len(time_options) - 1
            sel = st.selectbox("多單進場時間", time_options, index=idx, key="long_time")
            if sel != st.session_state.long_entry_time:
                st.session_state.long_entry_time = sel
        else:
            st.markdown("<span style='color:rgba(255,255,255,0.3);font-size:0.85rem'>未持多單</span>", unsafe_allow_html=True)
    
    with col3:
        short_on = st.toggle("持有空單", value=st.session_state.position_short, key="toggle_short")
        if short_on != st.session_state.position_short:
            st.session_state.position_short = short_on
            if not short_on:
                st.session_state.short_entry_time = None
            st.rerun()
    
    with col4:
        if st.session_state.position_short:
            cur = st.session_state.short_entry_time or (time_options[-1] if time_options else "--:--")
            try:
                idx = time_options.index(cur)
            except:
                idx = len(time_options) - 1
            sel = st.selectbox("空單進場時間", time_options, index=idx, key="short_time")
            if sel != st.session_state.short_entry_time:
                st.session_state.short_entry_time = sel
        else:
            st.markdown("<span style='color:rgba(255,255,255,0.3);font-size:0.85rem'>未持空單</span>", unsafe_allow_html=True)
    
    # 操作列
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("刷新資料", use_container_width=True):
            with st.spinner("更新中..."):
                st.session_state.data = fetch_and_process_data(components)
                st.session_state.last_refresh = datetime.now()
            st.rerun()
    with col2:
        st.session_state.auto_refresh = st.checkbox("自動刷新", value=st.session_state.auto_refresh)
    with col3:
        # 狀態列
        parts = []
        if st.session_state.position_long:
            parts.append(f"多單 @ {st.session_state.long_entry_time or '?'}")
        if st.session_state.position_short:
            parts.append(f"空單 @ {st.session_state.short_entry_time or '?'}")
        if not parts:
            parts.append("空手觀望")
        
        model_status = components['model_loader'].get_status()
        refresh_time = st.session_state.last_refresh.strftime('%H:%M:%S') if st.session_state.last_refresh else '--:--:--'
        scheduler = components['scheduler']
        next_run = scheduler.get_next_run_time()
        
        st.markdown(f"""
        <div class="status-bar">
            <span>{'  |  '.join(parts)}</span>
            <span>模型: {'OK' if model_status['ready'] else 'X'} {model_status['total_models']}/20 | 
                  更新: {refresh_time} | 
                  排程: {next_run}</span>
        </div>
        """, unsafe_allow_html=True)


def display_signal_section(day_df, components, section_key="today"):
    """顯示完整訊號區塊（表格+指示燈+圖表）"""
    if day_df.empty:
        st.info("尚無資料")
        return
    
    # 檢查是否有特徵
    has_features = all(f in day_df.columns for f in FEATURE_NAMES)
    
    if not has_features:
        st.warning("資料缺少特徵值，無法計算訊號")
        return
    
    # 快速統計
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("K棒數", f"{len(day_df)} 根")
    with col2:
        st.metric("最高", f"{day_df['high'].max():.0f}" if 'high' in day_df.columns else '-')
    with col3:
        st.metric("最低", f"{day_df['low'].min():.0f}" if 'low' in day_df.columns else '-')
    with col4:
        if len(day_df) > 0 and 'close' in day_df.columns and 'open' in day_df.columns:
            change = day_df['close'].iloc[-1] - day_df['open'].iloc[0]
            st.metric("漲跌", f"{change:+.0f}")
    
    # 計算預測
    predictor = components['signal_predictor']
    preds_df = calc_predictions_for_day(day_df, predictor)
    
    # LINE 通知 — 只對「已確認收盤」的 K 棒發送
    # 
    # 防呆邏輯：
    #   5分K 標記為 08:00 → 覆蓋 08:00~08:04:59 → 08:05:00 才確認收盤
    #   在 08:03 手動刷新 → 08:00 K棒尚未收盤 → 不發送
    #   在 08:05:05 自動刷新 → 08:00 已收盤(確認) → 發送 08:00 的訊號
    #                        → 08:05 剛開盤(未確認) → 不發送
    #
    if section_key == "today" and not preds_df.empty:
        line_notifier = components.get('line_notifier')
        if line_notifier:
            now = datetime.now()
            # 從最新往回找，找到第一根「已確認收盤」的 K 棒
            confirmed_idx = None
            for idx in reversed(list(day_df.index)):
                row = day_df.loc[idx]
                kbar_dt = row.get('datetime')
                if pd.notna(kbar_dt):
                    # K棒收盤時間 = K棒時間 + 5分鐘
                    kbar_close_time = kbar_dt + timedelta(minutes=5)
                    if now >= kbar_close_time:
                        confirmed_idx = idx
                        break
            
            if confirmed_idx is not None and confirmed_idx in preds_df.index:
                conf_row = day_df.loc[confirmed_idx]
                conf_pred = preds_df.loc[confirmed_idx]
                le_prob = conf_pred.get('long_entry')
                se_prob = conf_pred.get('short_entry')
                dt_val = conf_row.get('datetime')
                t_str = dt_val.strftime('%H:%M') if pd.notna(dt_val) else '--:--'
                close_val = float(conf_row['close']) if pd.notna(conf_row.get('close')) else 0
                feat_dict = {f: float(conf_row.get(f, 0)) if pd.notna(conf_row.get(f)) else 0.0 for f in FEATURE_NAMES}
                row_lights = calc_row_lights(feat_dict)
                ts_key = int(conf_row['timestamp']) if pd.notna(conf_row.get('timestamp')) else None
                line_notifier.check_and_notify(
                    time_str=t_str, close=close_val,
                    lights=row_lights,
                    long_entry_prob=le_prob, short_entry_prob=se_prob,
                    timestamp_key=ts_key,
                )
    
    # 訊號表格（含每列指示燈）
    st.markdown("#### 訊號紀錄")
    table_html = build_signal_table_html(
        day_df, preds_df,
        show_exit_long=st.session_state.position_long,
        show_exit_short=st.session_state.position_short
    )
    st.markdown(table_html, unsafe_allow_html=True)
    
    # 收盤價圖表
    st.markdown("#### 收盤價走勢與訊號")
    fig = build_price_chart(day_df, preds_df)
    st.plotly_chart(fig, use_container_width=True, key=f"chart_{section_key}")


def display_history_section(components):
    """歷史訊號回顧"""
    db = components['db_manager']
    
    # 取得可選日期
    trading_dates = db.get_trading_dates()
    
    if not trading_dates:
        st.info("資料庫中無歷史資料，請先匯入歷史資料")
        return
    
    # 日期選擇
    selected_date = st.selectbox(
        "選擇日期",
        options=trading_dates,
        index=0,
        key="history_date"
    )
    
    if selected_date:
        with st.spinner("載入歷史資料..."):
            hist_data = load_history_data(components, selected_date)
        
        if hist_data.empty:
            st.warning(f"{selected_date} 無資料")
        else:
            display_signal_section(hist_data, components, section_key=f"hist_{selected_date}")


# =============================================================================
# Main
# =============================================================================

def main():
    init_session_state()
    components = load_components()
    
    # 載入資料：首次 或 有新 K 棒收盤時自動更新
    if st.session_state.data.empty or is_data_stale():
        with st.spinner("正在載入資料..."):
            st.session_state.data = fetch_and_process_data(components)
            st.session_state.last_refresh = datetime.now()
    
    # 訊號卡片
    display_main_signals(components)
    
    # 信心度參考說明
    st.markdown("""
    <div style="display:flex; justify-content:center; gap:2rem; flex-wrap:wrap;
                padding:0.4rem 1rem; margin:-0.3rem 0 0.3rem 0;
                background:rgba(255,255,255,0.03); border-radius:8px;">
        <span style="color:rgba(255,255,255,0.45); font-size:0.78rem;">
            💡 &gt;60% — 勝率25%, RECALL 10%
        </span>
        <span style="color:rgba(255,255,255,0.45); font-size:0.78rem;">
            ⚡ &gt;70% — 勝率30%, RECALL 5%
        </span>
        <span style="color:rgba(255,255,255,0.45); font-size:0.78rem;">
            🔥 &gt;80% — 勝率45%, RECALL 3%
        </span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 控制面板
    display_control_panel(components)
    
    st.markdown("---")
    
    # 分頁：今日 / 歷史
    tab_today, tab_history = st.tabs(["今日訊號", "歷史回顧"])
    
    with tab_today:
        today_str = datetime.now().strftime('%Y-%m-%d')
        today_df = get_day_data(st.session_state.data, today_str)
        display_signal_section(today_df, components, section_key="today")
    
    with tab_history:
        display_history_section(components)
    
    # 自動刷新：對齊 5 分 K 收盤時間
    # 注入 JavaScript 計時器，精準在下一根 K 棒收盤後觸發頁面刷新
    if st.session_state.auto_refresh:
        inject_kbar_auto_refresh()


if __name__ == "__main__":
    main()
