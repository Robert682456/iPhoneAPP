import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh
import json
import os
import requests
from datetime import datetime, timedelta, timezone

st.set_page_config(page_title="雙指標波段系統", page_icon="📈", layout="wide")

# 自動重整機制：每 5 分鐘自動刷新
st_autorefresh(interval=5 * 60 * 1000, key="auto_refresh")

# ==========================================
# 台灣/香港標準時區 (UTC+8) 輔助函式
# ==========================================
TZ_TW = timezone(timedelta(hours=8))

def get_tw_now():
    return datetime.now(timezone.utc).astimezone(TZ_TW)

# ==========================================
# 本機設定檔存取邏輯
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "user_settings.json")
NOTIFICATION_CACHE_FILE = os.path.join(BASE_DIR, "notified_cache.json")

DEFAULT_LIST_1 = """0050.TW,元大台灣50
2812.TW,台中銀
1101.TW,台泥
2330.TW,台積電
3008.TW,大立光
3362.TWO,先進光
1415.HK,高偉電子
2342.HK,京信通信
1729.HK,匯聚科技
VOO,VOO標普500
QQQM,QQQM納指100
SGOV,SGOV美債
2408.TW,南亞科
2371.TW,大同
6505.TW,台塑化
6147.TWO,頎邦
1504.TW,東元
2006.TW,東和鋼鐵
2633.TW,台灣高鐵
9921.TW,巨大
2610.TW,華航
1402.TW,遠東新
3376.TW,新日興
2912.TW,統一超
1216.TW,統一
3406.TW,玉晶光"""

DEFAULT_LIST_2 = """2330.TW,台積電
2454.TW,聯發科
2317.TW,鴻海
2382.TW,廣達
3231.TW,緯創
2308.TW,台達電
6669.TW,緯穎
3017.TW,奇鋐"""

DEFAULT_LIST_3 = """0050.TW,元大台灣50
0056.TW,元大高股息
00878.TW,國泰永續高股息
VOO,VOO標普500
QQQM,QQQM納指100
SGOV,SGOV美債
00719B.TW,富邦美債1-3"""

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "search_ticker": "",
        "search_name": "",
        "market_ticker": "0050.TW",
        "current_group": "自選股 1",
        "watchlist_1": DEFAULT_LIST_1,
        "watchlist_2": DEFAULT_LIST_2,
        "watchlist_3": DEFAULT_LIST_3,
        "line_token": "",
        "line_user_id": "",
        "enable_line_notify": False,
        "enable_daily_reports": False
    }

def save_settings():
    settings = {
        "search_ticker": st.session_state.search_ticker,
        "search_name": st.session_state.search_name,
        "market_ticker": st.session_state.get("market_ticker_input", "0050.TW"),
        "current_group": st.session_state.get("current_group_choice", "自選股 1"),
        "watchlist_1": st.session_state.get("watchlist_1_text", DEFAULT_LIST_1),
        "watchlist_2": st.session_state.get("watchlist_2_text", DEFAULT_LIST_2),
        "watchlist_3": st.session_state.get("watchlist_3_text", DEFAULT_LIST_3),
        "line_token": st.session_state.get("line_token_input", ""),
        "line_user_id": st.session_state.get("line_user_id_input", ""),
        "enable_line_notify": st.session_state.get("enable_line_notify_input", False),
        "enable_daily_reports": st.session_state.get("enable_daily_reports_input", False)
    }
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False)
    except Exception:
        pass

settings = load_settings()

if 'selected_ticker' not in st.session_state:
    st.session_state.selected_ticker = None
if 'search_ticker' not in st.session_state:
    st.session_state.search_ticker = settings.get("search_ticker", "")
if 'search_name' not in st.session_state:
    st.session_state.search_name = settings.get("search_name", "")
if 'market_ticker_input' not in st.session_state:
    st.session_state.market_ticker_input = settings.get("market_ticker", "0050.TW")
if 'current_group_choice' not in st.session_state:
    st.session_state.current_group_choice = settings.get("current_group", "自選股 1")
if 'watchlist_1_text' not in st.session_state:
    st.session_state.watchlist_1_text = settings.get("watchlist_1", DEFAULT_LIST_1)
if 'watchlist_2_text' not in st.session_state:
    st.session_state.watchlist_2_text = settings.get("watchlist_2", DEFAULT_LIST_2)
if 'watchlist_3_text' not in st.session_state:
    st.session_state.watchlist_3_text = settings.get("watchlist_3", DEFAULT_LIST_3)
if 'line_token_input' not in st.session_state:
    st.session_state.line_token_input = settings.get("line_token", "")
if 'line_user_id_input' not in st.session_state:
    st.session_state.line_user_id_input = settings.get("line_user_id", "")
if 'enable_line_notify_input' not in st.session_state:
    st.session_state.enable_line_notify_input = settings.get("enable_line_notify", False)
if 'enable_daily_reports_input' not in st.session_state:
    st.session_state.enable_daily_reports_input = settings.get("enable_daily_reports", False)

def update_selected_from_search():
    val = st.session_state.search_ticker.strip().upper()
    if val:
        st.session_state.selected_ticker = val
    save_settings()

def update_other_inputs():
    save_settings()

def parse_watchlist(text):
    watchlist = {}
    for line in text.strip().split('\n'):
        if ',' in line:
            ticker, name = line.split(',', 1)
            watchlist[ticker.strip()] = name.strip()
    return watchlist

# ==========================================
# 🎯 雙重共振背離判定
# ==========================================
def detect_dual_divergence(close_series, macd_dif_series, rsi_series, order=4, lookback=45):
    if len(close_series) < lookback: return False, False
    c = close_series.iloc[-lookback:].values
    m = macd_dif_series.iloc[-lookback:].values
    r = rsi_series.iloc[-lookback:].values
    curr_p = c[-1]
    w_min = np.min(c)
    w_max = np.max(c)
    allow_bear_div = (curr_p >= w_max * 0.96)
    allow_bull_div = (curr_p <= w_min * 1.04)

    troughs, peaks = [], []
    for i in range(order, len(c) - order):
        if c[i] == min(c[i - order:i + order + 1]): troughs.append(i)
        if c[i] == max(c[i - order:i + order + 1]): peaks.append(i)

    is_dual_bull_div, is_dual_bear_div = False, False
    if allow_bull_div and len(troughs) >= 2:
        i1, i2 = troughs[-2], troughs[-1]
        if (len(c) - 1 - i2 <= 6) and (c[i2] < c[i1] * 0.995) and (m[i2] > m[i1]) and (r[i2] > r[i1]):
            is_dual_bull_div = True
    if allow_bear_div and len(peaks) >= 2:
        p1, p2 = peaks[-2], peaks[-1]
        if (len(c) - 1 - p2 <= 6) and (c[p2] > c[p1] * 1.005) and (m[p2] < m[p1]) and (r[p2] < r[p1]):
            is_dual_bear_div = True

    return is_dual_bull_div, is_dual_bear_div

# ==========================================
# LINE Messaging API 推播與狀態快取
# ==========================================
def send_line_message(token, user_id, message_text):
    if not token or not user_id: return False, "缺少 Token 或 User ID"
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token.strip()}"}
    payload = {"to": user_id.strip(), "messages": [{"type": "text", "text": message_text}]}
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=8)
        return (True, "推播成功") if res.status_code == 200 else (False, f"HTTP {res.status_code}")
    except Exception as e:
        return False, str(e)

def load_notified_cache():
    if os.path.exists(NOTIFICATION_CACHE_FILE):
        try:
            with open(NOTIFICATION_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {}

def save_notified_cache(cache):
    try:
        with open(NOTIFICATION_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
    except: pass

def build_morning_report(df_results, market_trend, group_name):
    now_tw = get_tw_now()
    today_str = now_tw.strftime("%Y-%m-%d")
    m_status = market_trend['status'] if market_trend else "維持觀察"
    m_advice = market_trend['advice'] if market_trend else "無大盤資料"
    up_stocks = df_results[df_results['建議'].str.contains("買進|走勢向上|加碼", na=False)] if not df_results.empty else pd.DataFrame()
    items_text = [f"• {row['代碼']} {row['名稱']}: {row['建議']}" for _, row in up_stocks.head(6).iterrows()] if not up_stocks.empty else ["• 目前無多頭買進標的，多看少做。"]
    return f"🌅【雙指標系統 - 每日盤前早報】\n━━━━━━━━━━━━━━\n📅 日期：{today_str} (08:45 早報)\n📁 組合：{group_name}\n\n🧭 大盤資金水位：\n狀態：{m_status}\n指引：{m_advice}\n\n⭐ 盤前多方焦點標的：\n{chr(10).join(items_text)}\n━━━━━━━━━━━━━━\n💡 提醒：若有觸發日MACD金叉，系統將於盤中即時推播。"

def build_evening_report(df_results, group_name):
    now_tw = get_tw_now()
    today_str = now_tw.strftime("%Y-%m-%d")
    buy_cnt = len(df_results[df_results['建議'].str.contains("買進|走勢向上", na=False)]) if not df_results.empty else 0
    sell_cnt = len(df_results[df_results['建議'].str.contains("賣出|逃命", na=False)]) if not df_results.empty else 0
    hold_cnt = len(df_results[df_results['建議'].str.contains("續抱|核心", na=False)]) if not df_results.empty else 0
    empty_cnt = len(df_results[df_results['建議'].str.contains("空手", na=False)]) if not df_results.empty else 0
    action_items = [f"• {row['代碼']} {row['名稱']}: {row['最新動態']} ({row['建議']})" for _, row in df_results.iterrows() if row['最新動態'] != "-"] if not df_results.empty else ["• 今日無新增 MACD 交叉訊號。"]
    return f"🌆【雙指標系統 - 每日盤後總結】\n━━━━━━━━━━━━━━\n📅 日期：{today_str} (13:45 盤後)\n📁 組合：{group_name}\n\n📊 盤後狀態分佈：\n🟢 買進建倉/向上：{buy_cnt} 檔\n🟢 多頭持股續抱：{hold_cnt} 檔\n🔴 賣出/逃命防守：{sell_cnt} 檔\n⚪ 空手觀望：{empty_cnt} 檔\n\n⚡ 今日關鍵動態事件：\n{chr(10).join(action_items[:6])}\n━━━━━━━━━━━━━━\n📋 完整日誌可至『深度分析』匯出 CSV 進行盤後覆盤。"

def check_and_notify_signals(df_results, market_trend, group_name):
    token = st.session_state.line_token_input.strip()
    user_id = st.session_state.line_user_id_input.strip()
    if not token or not user_id: return
    cache = load_notified_cache()
    now_tw = get_tw_now()
    today_str = now_tw.strftime("%Y-%m-%d")
    now_time_str = now_tw.strftime("%H:%M:%S")

    if st.session_state.enable_line_notify_input and not df_results.empty:
        for _, row in df_results.iterrows():
            ticker, name, curr_rec, actions, price_info, reason = row['代碼'], row['名稱'], row['建議'], row['最新動態'], row['收盤價(漲跌)'], row['詳細判定原因']
            item_cache = cache.get(ticker, {"last_rec": "", "last_gc_date": "", "last_div_date": ""})
            prev_rec = item_cache.get("last_rec", "")
            if "買進" in curr_rec and "買進" not in prev_rec:
                send_line_message(token, user_id, f"🟢【雙指標系統 - 買進警報】\n標的：{ticker} {name}\n現價：{price_info}\n原因：{reason}\n時間：{now_time_str}")
            elif "賣出" in curr_rec and "賣出" not in prev_rec:
                send_line_message(token, user_id, f"🔴【雙指標系統 - 賣出警報】\n標的：{ticker} {name}\n現價：{price_info}\n原因：{reason}\n時間：{now_time_str}")
            elif "逃命" in curr_rec and "逃命" not in prev_rec:
                send_line_message(token, user_id, f"⚠️【雙指標系統 - 假金叉防禦】\n標的：{ticker} {name}\n現價：{price_info}\n原因：{reason}\n時間：{now_time_str}")
            item_cache["last_rec"] = curr_rec
            cache[ticker] = item_cache

    if st.session_state.enable_daily_reports_input and not df_results.empty:
        curr_min = now_tw.hour * 60 + now_tw.minute
        if 525 <= curr_min <= 535 and cache.get("last_morning_report_date") != today_str:
            if send_line_message(token, user_id, build_morning_report(df_results, market_trend, group_name))[0]: cache["last_morning_report_date"] = today_str
        if 820 <= curr_min <= 835 and cache.get("last_evening_report_date") != today_str:
            if send_line_message(token, user_id, build_evening_report(df_results, group_name))[0]: cache["last_evening_report_date"] = today_str
    save_notified_cache(cache)

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .block-container { padding-top: 1rem; padding-bottom: 0rem; }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# ==========================================
# 🎯 核心決策判斷引擎：MACD 搭配 20MA 假金叉濾網
# ==========================================
def evaluate_strategy_signal(
    curr_close, prev_close, c_vol, c_vol_ma5,
    c_ma5, c_ma10, c_ma20, p_close, p_ma20,
    c_hist, p_hist, c_rsi, c_lcl, c_ucl, c_adx,
    is_high_momentum, is_buy_and_hold, stock_profile,
    is_broke_1y_low, low_1y_prev, percentile_1y,
    was_holding=True
):
    if is_buy_and_hold: return "🔵 長期持有 (核心被動)", "【免出場資產】定期定額或逢低續抱，不受短期波動影響。"

    is_macd_bullish = (c_hist > 0)
    is_macd_bearish = (c_hist < 0)
    is_above_20ma = (curr_close > c_ma20)

    if is_macd_bullish and is_above_20ma:
        if was_holding: return "🟢 波段續抱 (多頭格局)", f"日 MACD 維持紅柱且股價在 20MA({c_ma20:.2f}) 之上，安全抱牢。"
        else: return "🟢 買進 (MACD金叉+站上月線)", f"日 MACD 翻紅且股價成功站上 20MA({c_ma20:.2f})，多頭啟動，順勢買進。"

    elif is_macd_bullish and not is_above_20ma:
        if was_holding: return "🔴 賣出 (跌破月線)", f"雖然 MACD 仍是紅柱，但股價已實質跌破 20MA({c_ma20:.2f})，防守紀律賣出。"
        else: return "⚠️ 假金叉排除 (空手觀望)", f"【逃命波陷阱】日 MACD 雖收斂翻紅，但股價受制於下彎的 20MA({c_ma20:.2f}) 之下，判定為弱勢反彈，維持空手不接刀！"

    elif is_macd_bearish:
        if was_holding: return "🔴 賣出 (MACD死叉)", "日 MACD 柱狀翻綠(死亡交叉)，動能轉空，果斷賣出停利/停損。"
        else: return "⚪ 空手觀望 (空頭格局)", "日 MACD 維持綠柱空頭排列，保留現金，耐心等待買點。"

    return "⚪ 狀態未明", "無明確訊號。"


@st.cache_data(ttl=300)
def get_market_trend(ticker):
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if df.empty: return None
        close = df['Close'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['Close']
        close = close.dropna()
        ema12, ema26 = close.ewm(span=12, adjust=False).mean(), close.ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        hist = dif - dea 
        curr_hist, prev_hist = hist.iloc[-1], hist.iloc[-2]
        if curr_hist > 0 and curr_hist > prev_hist: return {"status": "🟢 多頭擴張", "advice": "大盤趨勢向上，部位可適度放大至 80%~100%。", "color": "#e8f5e9"}
        elif curr_hist > 0 and curr_hist <= prev_hist: return {"status": "🟡 高檔震盪 (柱狀收斂)", "advice": "大盤動能減弱，維持現有持股，嚴格挑選帶量標的。", "color": "#fff8e1"}
        elif curr_hist < 0 and curr_hist > prev_hist: return {"status": "🟡 跌深反彈 (水下金叉)", "advice": "大盤有落底跡象，小量試單，嚴設前低停損。", "color": "#fff8e1"}
        else: return {"status": "🔴 空頭發散", "advice": "大盤趨勢向下，總部位降至 30% 以下，保本為主。", "color": "#ffebee"}
    except: return None

@st.cache_data(ttl=300)
def analyze_signals_comprehensive(watchlist):
    results = []
    BUY_AND_HOLD_LIST = {"SGOV", "BIL", "SHV", "00719B.TW", "0050.TW", "VOO", "QQQM", "SPY", "IVV"}
    for ticker, name in watchlist.items():
        try:
            df_d = yf.download(ticker, period="1y", interval="1d", progress=False)
            if df_d.empty or len(df_d) < 35:
                results.append({"代碼": ticker, "名稱": name, "收盤價(漲跌)": "⚠️ 無資料", "股性模式": "⚪ 未知", "股性類別": "未知", "建議": "⚪ 未知", "最新動態": "-", "詳細判定原因": "無足夠日 K 線資料", "Yahoo股市": f"https://finance.yahoo.com/quote/{ticker}"})
                continue
            close_d = df_d['Close'][ticker] if isinstance(df_d.columns, pd.MultiIndex) else df_d['Close']
            high_d = df_d['High'][ticker] if isinstance(df_d.columns, pd.MultiIndex) else df_d['High']
            low_d = df_d['Low'][ticker] if isinstance(df_d.columns, pd.MultiIndex) else df_d['Low']
            volume_d = df_d['Volume'][ticker] if isinstance(df_d.columns, pd.MultiIndex) else df_d['Volume']
            close_d, high_d, low_d, volume_d = close_d.dropna(), high_d.dropna(), low_d.dropna(), volume_d.dropna()

            atr14 = (high_d - low_d).rolling(14).mean().iloc[-1]
            curr_close, prev_close = close_d.iloc[-1], close_d.iloc[-2]
            atr_pct = (atr14 / curr_close) * 100 if curr_close > 0 else 0

            is_buy_and_hold = (ticker in BUY_AND_HOLD_LIST) or ("美債" in name and "0-3" in name)
            if is_buy_and_hold:
                is_high_momentum = False
                stock_profile = "💰 核心·收息存債" if ("SGOV" in ticker or "債" in name) else "🏛️ 核心·指數複利"
                stock_category = "穩健型"
            else:
                is_high_momentum = (atr_pct >= 3.5)
                stock_profile = f"🚀 動能({atr_pct:.1f}%)" if is_high_momentum else f"🏛️ 穩健({atr_pct:.1f}%)"
                stock_category = "高動能型" if is_high_momentum else "穩健型"

            high_1y = high_d.tail(250).max()
            low_1y_prev = low_d.iloc[:-1].tail(249).min() if len(low_d) >= 250 else low_d.iloc[:-1].min()
            low_1y = min(low_1y_prev, low_d.iloc[-1])
            percentile_1y = ((curr_close - low_1y) / (high_1y - low_1y)) * 100 if high_1y > low_1y else 50.0
            is_broke_1y_low = (curr_close <= low_1y_prev * 1.01) or (percentile_1y <= 10.0)

            ma5_d, ma10_d, ma20_d = close_d.rolling(5).mean(), close_d.rolling(10).mean(), close_d.rolling(20).mean()
            vol_ma5_d = volume_d.rolling(5).mean()
            ema12_d, ema26_d = close_d.ewm(span=12, adjust=False).mean(), close_d.ewm(span=26, adjust=False).mean()
            dif_d = ema12_d - ema26_d
            hist_d = dif_d - dif_d.ewm(span=9, adjust=False).mean()
            
            delta_d = close_d.diff()
            g_d = delta_d.clip(lower=0).ewm(com=13, adjust=False).mean()
            l_d = (-1 * delta_d.clip(upper=0)).ewm(com=13, adjust=False).mean()
            rsi_d = 100 - (100 / (1 + (g_d / l_d)))
            curr_rsi_d = rsi_d.iloc[-1]
            
            std20_d = close_d.rolling(20).std()
            curr_ucl_d = (ma20_d + 2 * std20_d).iloc[-1]
            curr_lcl_d = (ma20_d - 2 * std20_d).iloc[-1]
            
            curr_ma5_d, curr_ma10_d, curr_ma20_d = ma5_d.iloc[-1], ma10_d.iloc[-1], ma20_d.iloc[-1]
            prev_ma20_d = ma20_d.iloc[-2]
            curr_hist_d, prev_hist_d = hist_d.iloc[-1], hist_d.iloc[-2]
            curr_vol_d, curr_vol_ma5_d = volume_d.iloc[-1], vol_ma5_d.iloc[-1]

            was_holding_prev = (prev_close >= prev_ma20_d) and (prev_hist_d > 0)

            change_pct = ((curr_close - prev_close) / prev_close) * 100
            price_display = f"🔺 {curr_close:.2f} (+{change_pct:.2f}%)" if change_pct > 0 else f"🔻 {curr_close:.2f} ({change_pct:.2f}%)" if change_pct < 0 else f"➖ {curr_close:.2f} (0.00%)"
            
            last_date_str = close_d.index[-1].strftime('%m/%d')
            actions = []
            if prev_hist_d <= 0 and curr_hist_d > 0: actions.append(f"日MACD剛金叉 ({last_date_str})")
            elif prev_hist_d >= 0 and curr_hist_d < 0: actions.append(f"日MACD剛死叉 ({last_date_str})")

            rec_text, detail_reason = evaluate_strategy_signal(
                curr_close, prev_close, curr_vol_d, curr_vol_ma5_d,
                curr_ma5_d, curr_ma10_d, curr_ma20_d, prev_close, prev_ma20_d,
                curr_hist_d, prev_hist_d, curr_rsi_d, curr_lcl_d, curr_ucl_d, 15.0,
                is_high_momentum, is_buy_and_hold, stock_profile,
                is_broke_1y_low, low_1y_prev, percentile_1y, was_holding=was_holding_prev
            )

            results.append({"代碼": ticker, "名稱": name, "收盤價(漲跌)": price_display, "股性模式": stock_profile, "股性類別": stock_category, "建議": rec_text, "最新動態": " / ".join(actions) if actions else "-", "詳細判定原因": detail_reason, "Yahoo股市": f"https://finance.yahoo.com/quote/{ticker}"})
        except:
            results.append({"代碼": ticker, "名稱": name, "收盤價(漲跌)": "⚠️ 錯誤", "股性模式": "⚪ 異常", "股性類別": "未知", "建議": "⚪ 未知", "最新動態": "-", "詳細判定原因": "抓取異常", "Yahoo股市": f"https://finance.yahoo.com/quote/{ticker}"})
            continue

    df_results = pd.DataFrame(results)
    if not df_results.empty:
        def get_sort_rank(row):
            if "買進" in row['建議']: return 1
            elif "波段續抱" in row['建議']: return 2
            elif "長期持有" in row['建議']: return 3
            elif "賣出" in row['建議']: return 4
            elif "假金叉" in row['建議']: return 5
            elif "空手" in row['建議']: return 6
            else: return 7
        df_results['SortRank'] = df_results.apply(get_sort_rank, axis=1)
        df_results = df_results.sort_values(by=['SortRank', '代碼']).drop(columns=['SortRank']).reset_index(drop=True)
    return df_results

@st.cache_data(ttl=300)
def generate_historical_signals_table(ticker, name, start_date, end_date):
    BUY_AND_HOLD_LIST = {"SGOV", "BIL", "SHV", "00719B.TW", "0050.TW", "VOO", "QQQM", "SPY", "IVV"}
    fetch_start = start_date - timedelta(days=400)
    fetch_end = end_date + timedelta(days=2)
    df_d = yf.download(ticker, start=fetch_start.strftime('%Y-%m-%d'), end=fetch_end.strftime('%Y-%m-%d'), interval="1d", progress=False)
    if df_d.empty or len(df_d) < 35: return pd.DataFrame(), None
    if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
    df_d = df_d.dropna()

    close, high, low, volume = df_d['Close'], df_d['High'], df_d['Low'], df_d['Volume']
    ma5, ma10, ma20 = close.rolling(5).mean(), close.rolling(10).mean(), close.rolling(20).mean()
    vol_ma5 = volume.rolling(5).mean()
    ema12, ema26 = close.ewm(span=12, adjust=False).mean(), close.ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()
    hist = dif - dea
    delta = close.diff()
    g = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
    l = (-1 * delta.clip(upper=0)).ewm(com=13, adjust=False).mean()
    rsi = 100 - (100 / (1 + (g / l)))
    std20 = close.rolling(20).std()
    ucl, lcl = ma20 + 2 * std20, ma20 - 2 * std20

    is_buy_and_hold = (ticker in BUY_AND_HOLD_LIST) or ("美債" in name and "0-3" in name)
    trading_dates_forward = [d for d in df_d.index if d.date() <= end_date]
    trading_dates_forward.sort()

    sim_holding = False
    all_computed_records = []

    for dt in trading_dates_forward:
        loc = df_d.index.get_loc(dt)
        if loc < 35: continue

        c_close, p_close = close.iloc[loc], close.iloc[loc - 1]
        c_vol, c_vol_ma5 = volume.iloc[loc], vol_ma5.iloc[loc]
        c_ma5, c_ma10, c_ma20, p_ma20 = ma5.iloc[loc], ma10.iloc[loc], ma20.iloc[loc], ma20.iloc[loc - 1]
        c_hist, p_hist, c_rsi, c_ucl, c_lcl = hist.iloc[loc], hist.iloc[loc - 1], rsi.iloc[loc], ucl.iloc[loc], lcl.iloc[loc]
        atr14 = (high.iloc[loc-13:loc+1] - low.iloc[loc-13:loc+1]).mean()
        atr_pct = (atr14 / c_close) * 100 if c_close > 0 else 0

        if is_buy_and_hold:
            is_high_momentum = False
            stock_profile = "💰 核心·收息存債" if ("SGOV" in ticker or "債" in name) else "🏛️ 核心·指數複利"
        else:
            is_high_momentum = (atr_pct >= 3.5)
            stock_profile = f"🚀 動能({atr_pct:.1f}%)" if is_high_momentum else f"🏛️ 穩健({atr_pct:.1f}%)"

        lookback_len = min(250, loc)
        h_1y = high.iloc[loc - lookback_len:loc + 1].max()
        l_1y_prev = low.iloc[loc - lookback_len:loc].min() if lookback_len > 1 else low.iloc[loc]
        l_1y = min(l_1y_prev, low.iloc[loc])
        percentile_1y = ((c_close - l_1y) / (h_1y - l_1y)) * 100 if h_1y > l_1y else 50.0
        is_broke_1y_low = (c_close <= l_1y_prev * 1.01) or (percentile_1y <= 10.0)

        change_pct = ((c_close - p_close) / p_close) * 100
        price_display = f"🔺 {c_close:.2f} (+{change_pct:.2f}%)" if change_pct > 0 else f"🔻 {c_close:.2f} ({change_pct:.2f}%)" if change_pct < 0 else f"➖ {c_close:.2f} (0.00%)"
        date_str, date_short = dt.strftime('%Y/%m/%d'), dt.strftime('%m/%d')
        actions = []
        if p_hist <= 0 and c_hist > 0: actions.append(f"日MACD剛金叉 ({date_short})")
        elif p_hist >= 0 and c_hist < 0: actions.append(f"日MACD剛死叉 ({date_short})")

        rec_text, detail_reason = evaluate_strategy_signal(
            c_close, p_close, c_vol, c_vol_ma5,
            c_ma5, c_ma10, c_ma20, p_close, p_ma20,
            c_hist, p_hist, c_rsi, c_lcl, c_ucl, 15.0,
            is_high_momentum, is_buy_and_hold, stock_profile,
            is_broke_1y_low, l_1y_prev, percentile_1y, was_holding=sim_holding
        )

        if "買進" in rec_text or "波段續抱" in rec_text: sim_holding = True
        elif "賣出" in rec_text: sim_holding = False

        if start_date <= dt.date() <= end_date:
            all_computed_records.append({"日期": date_str, "代碼": ticker, "名稱": name, "收盤價(漲跌)": price_display, "股性模式": stock_profile, "建議": rec_text, "最新動態": " / ".join(actions) if actions else "-", "詳細判定原因": detail_reason})

    all_computed_records.reverse()
    ma5_deduction_info = None
    if len(close) >= 5:
        curr_p, deduction_price = close.iloc[-1], close.iloc[-5]
        stand_on_ma5_price = close.iloc[-4:].sum() / 4.0
        ma5_deduction_info = {"current_price": curr_p, "deduction_price": deduction_price, "turn_up_price": deduction_price, "turn_up_diff_pct": ((deduction_price - curr_p) / curr_p) * 100 if curr_p > 0 else 0, "stand_on_ma5_price": stand_on_ma5_price, "stand_diff_pct": ((stand_on_ma5_price - curr_p) / curr_p) * 100 if curr_p > 0 else 0}
    return pd.DataFrame(all_computed_records), ma5_deduction_info

def generate_summary_insight(df_records, ticker, name, ma5_info=None):
    if df_records.empty: return ""
    latest_row = df_records.iloc[0]
    latest_date, latest_rec, latest_reason, latest_profile = latest_row['日期'], latest_row['建議'], latest_row['詳細判定原因'], latest_row['股性模式']
    
    if "買進" in latest_rec or "續抱" in latest_rec: trend_status, box_color, border_color = "🟢 多頭趨勢（持股續抱）", "#e8f5e9", "#81c784"
    elif "賣出" in latest_rec: trend_status, box_color, border_color = "🔴 空頭趨勢（停利/停損出清）", "#ffebee", "#ef9a9a"
    elif "假金叉" in latest_rec: trend_status, box_color, border_color = "⚠️ 逃命波防禦（空手觀望不接刀）", "#fff3e0", "#ffb74d"
    else: trend_status, box_color, border_color = "⚪ 空頭架構（空手等待）", "#f5f5f5", "#e0e0e0"

    return "".join([
        f'<div style="background-color: {box_color}; border: 1.5px solid {border_color}; border-radius: 8px; padding: 16px 20px; margin-top: 20px;">',
        f'<h4 style="margin: 0 0 10px 0; color: #1a1a1a; font-size: 18px;">💡 綜合判斷結論：{ticker} - {name}</h4>',
        f'<div style="margin: 6px 0; font-size: 15px; color: #222;"><b>【當前定調】</b>：<span style="font-weight: bold;">{trend_status}</span></div>',
        f'<div style="margin: 6px 0; font-size: 14px; color: #444;"><b>【最新狀態 ({latest_date})】</b>：<b>{latest_rec}</b> ｜ 股性：<b>{latest_profile}</b></div>',
        f'<div style="margin: 10px 0 0 0; font-size: 15px; font-weight: bold; color: #b71c1c;">🎯 實戰操作建議：{latest_reason}</div></div>'
    ])

def style_dataframe(df):
    def color_trend(val):
        if isinstance(val, str):
            if '🔺' in val: return 'color: #ff4b4b; font-weight: bold;'
            elif '🔻' in val: return 'color: #00c853; font-weight: bold;'
            elif '⚠️' in val: return 'color: #f57c00; font-weight: bold;'
        return ''
    def color_rec(val):
        if isinstance(val, str):
            if '買進' in val or '續抱' in val: return 'color: #1b5e20; font-weight: bold; background-color: #c8e6c9;'
            elif '賣出' in val: return 'color: #b71c1c; font-weight: bold; background-color: #ffcdd2;'
            elif '假金叉' in val: return 'color: #e65100; font-weight: bold; background-color: #ffe0b2;'
            elif '長期持有' in val: return 'color: #0d47a1; font-weight: bold; background-color: #e3f2fd;'
            elif '空手' in val: return 'color: #757575; font-weight: bold; background-color: #fafafa;'
        return ''
    res = df.style
    if hasattr(res, "map"):
        if '收盤價(漲跌)' in df.columns: res = res.map(color_trend, subset=['收盤價(漲跌)'])
        if '建議' in df.columns: res = res.map(color_rec, subset=['建議'])
    else:
        if '收盤價(漲跌)' in df.columns: res = res.applymap(color_trend, subset=['收盤價(漲跌)'])
        if '建議' in df.columns: res = res.applymap(color_rec, subset=['建議'])
    return res

# ==========================================
# 📊 【新版】三竹風格 黑底三區塊 圖表運算
# ==========================================
@st.cache_data(ttl=300)
def get_chart_data(ticker, interval, period):
    df = yf.download(ticker, period=period, interval=interval, progress=False)
    if df.empty: return None
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df = df.dropna()

    # 1. 均線計算
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean() 
    
    # 保留策略必要運算欄位 (不繪製)
    df['Vol_MA5'] = df['Volume'].rolling(window=5).mean()
    df['STD20'] = df['Close'].rolling(window=20).std()
    df['UCL'] = df['MA20'] + 2 * df['STD20']
    df['LCL'] = df['MA20'] - 2 * df['STD20']
    delta = df['Close'].diff()
    df['RSI'] = 100 - (100 / (1 + (delta.clip(lower=0).ewm(com=13, adjust=False).mean() / (-1 * delta.clip(upper=0)).ewm(com=13, adjust=False).mean())))

    # 2. MACD 計算
    df['DIF'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
    df['DEA'] = df['DIF'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['DIF'] - df['DEA']

    # 3. KD 指標計算 (9, 3, 3)
    low_min = df['Low'].rolling(window=9, min_periods=1).min()
    high_max = df['High'].rolling(window=9, min_periods=1).max()
    df['RSV'] = (df['Close'] - low_min) / (high_max - low_min) * 100
    df['K'] = df['RSV'].ewm(com=2, adjust=False).mean() # com=2 等同於 alpha=1/3
    df['D'] = df['K'].ewm(com=2, adjust=False).mean()

    return df

tab_dashboard, tab_rules, tab_settings, tab_war_room, tab_deep_dive = st.tabs(["📊 看盤儀表板", "📖 策略判斷原則", "⚙️ 自選股編輯", "⚔️ 買賣戰情室", "🔬 深度分析"])

if st.session_state.current_group_choice == "自選股 2": ACTIVE_WATCHLIST = parse_watchlist(st.session_state.watchlist_2_text)
elif st.session_state.current_group_choice == "自選股 3": ACTIVE_WATCHLIST = parse_watchlist(st.session_state.watchlist_3_text)
else: ACTIVE_WATCHLIST = parse_watchlist(st.session_state.watchlist_1_text)

display_df = analyze_signals_comprehensive(ACTIVE_WATCHLIST)
market_trend_global = get_market_trend(st.session_state.market_ticker_input)
check_and_notify_signals(display_df, market_trend_global, st.session_state.current_group_choice)

with tab_dashboard:
    col_group, col_empty = st.columns([1, 1])
    with col_group:
        current_group = st.radio("📌 選擇自選股組合：", ["自選股 1", "自選股 2", "自選股 3"], index=["自選股 1", "自選股 2", "自選股 3"].index(st.session_state.current_group_choice), horizontal=True)
        if current_group != st.session_state.current_group_choice:
            st.session_state.current_group_choice = current_group
            save_settings()
            st.rerun()

    st.divider()
    col_temp1, col_temp2, col_temp3 = st.columns([2, 2, 2])
    with col_temp1: st.text_input("輸入代碼 (例：2317.TW)", key="search_ticker", on_change=update_selected_from_search)
    with col_temp2: st.text_input("輸入名稱 (選填)", key="search_name", on_change=update_other_inputs)
    if st.session_state.search_ticker.strip():
        tmp_t, tmp_n = st.session_state.search_ticker.strip().upper(), st.session_state.search_name.strip()
        temp_df = analyze_signals_comprehensive({tmp_t: tmp_n if tmp_n else tmp_t})
        if not temp_df.empty and "⚠️ 無資料" not in temp_df.iloc[0]['收盤價(漲跌)']:
            st.dataframe(style_dataframe(temp_df.drop(columns=['股性類別'])), use_container_width=True)
        else: st.error("無法取得該代碼資料。")
    st.divider()

    if not display_df.empty:
        st.subheader(f"📊 【{st.session_state.current_group_choice}】狀態總覽")
        filter_opt = st.radio("🔍 狀態篩選：", ["👀 顯示全部", "🟢 買進建倉(走勢向上)", "🟢 波段續抱", "🔵 長期持有", "🔴 賣出(空頭成型)", "⚠️ 假金叉排除", "⚪ 空手觀望", "⚡ 剛發生交叉"], index=0, horizontal=True)
        filtered_df = display_df.copy()
        if filter_opt == "🟢 買進建倉(走勢向上)": filtered_df = filtered_df[filtered_df['建議'].str.contains("買進", na=False)]
        elif filter_opt == "🟢 波段續抱": filtered_df = filtered_df[filtered_df['建議'].str.contains("續抱", na=False)]
        elif filter_opt == "🔵 長期持有": filtered_df = filtered_df[filtered_df['建議'].str.contains("長期持有", na=False)]
        elif filter_opt == "🔴 賣出(空頭成型)": filtered_df = filtered_df[filtered_df['建議'].str.contains("賣出", na=False)]
        elif filter_opt == "⚠️ 假金叉排除": filtered_df = filtered_df[filtered_df['建議'].str.contains("假金叉", na=False)]
        elif filter_opt == "⚪ 空手觀望": filtered_df = filtered_df[filtered_df['建議'].str.contains("空手", na=False)]
        elif filter_opt == "⚡ 剛發生交叉": filtered_df = filtered_df[filtered_df['最新動態'] != "-"]

        if filtered_df.empty: st.info("無符合標的。")
        else:
            ev_table = st.dataframe(style_dataframe(filtered_df.drop(columns=['股性類別'])), use_container_width=True, on_select="rerun", selection_mode="single-row", key="table_main")
            if ev_table.selection.rows: st.session_state.selected_ticker = filtered_df.iloc[ev_table.selection.rows[0]]['代碼']

    st.divider()
    col_title, col_toggle = st.columns([3, 2])
    with col_toggle: chart_timeframe = st.radio("📊 線圖顯示週期：", ["日線圖 (Daily)", "週線圖 (Weekly)"], index=0, horizontal=True)
    with col_title: st.subheader(f"📉 價量與指標複合分析圖 ({chart_timeframe})")

    tf_interval = "1wk" if chart_timeframe == "週線圖 (Weekly)" else "1d"
    tf_period = "2y" if chart_timeframe == "週線圖 (Weekly)" else "1y"

    options = [f"{k} - {v}" for k, v in ACTIVE_WATCHLIST.items()]
    if options:
        default_idx = 0
        if st.session_state.selected_ticker:
            for i, opt in enumerate(options):
                if opt.startswith(st.session_state.selected_ticker):
                    default_idx = i
                    break
        selected_option = st.selectbox("請選擇要查看的標的：", options, index=default_idx)
        selected_ticker = selected_option.split(" - ")[0]
        st.session_state.selected_ticker = selected_ticker

        with st.spinner("繪製圖表中..."):
            chart_df = get_chart_data(selected_ticker, tf_interval, tf_period)
            
            if chart_df is not None:
                # 建立三區塊版面： K線與均線(0.55), KD(0.2), MACD(0.25)
                fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                                    vertical_spacing=0.02, row_heights=[0.55, 0.2, 0.25])

                # 【上半部】K線與均線
                fig.add_trace(go.Candlestick(x=chart_df.index, open=chart_df['Open'], high=chart_df['High'],
                                             low=chart_df['Low'], close=chart_df['Close'], 
                                             name='K線', 
                                             increasing_line_color='#FF0000', increasing_fillcolor='#FF0000',
                                             decreasing_line_color='#00FF00', decreasing_fillcolor='#00FF00'), row=1, col=1)
                
                fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['MA5'], line=dict(color='#FFFF00', width=1.5), name='5T'), row=1, col=1)
                fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['MA10'], line=dict(color='#00FFFF', width=1.5), name='10T'), row=1, col=1)
                fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['MA20'], line=dict(color='#FF00FF', width=1.5), name='20T'), row=1, col=1)

                # 【中半部】KD 指標
                fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['K'], line=dict(color='#FFFF00', width=1.2), name='9K'), row=2, col=1)
                fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['D'], line=dict(color='#00FFFF', width=1.2), name='9D'), row=2, col=1)

                # 【下半部】MACD 指標
                macd_colors = ['#FF0000' if val > 0 else '#00FF00' for val in chart_df['MACD_Hist']]
                fig.add_trace(go.Bar(x=chart_df.index, y=chart_df['MACD_Hist'], marker_color=macd_colors, name='MACD柱'), row=3, col=1)
                fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['DIF'], line=dict(color='#FFFF00', width=1.2), name='DIF12-26'), row=3, col=1)
                fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['DEA'], line=dict(color='#00FFFF', width=1.2), name='MACD9'), row=3, col=1)
                fig.add_hline(y=0, line_color='white', line_width=0.5, line_dash="dash", row=3, col=1)

                chart_dates = chart_df.index.strftime('%Y-%m-%d').tolist()
                dt_all = pd.date_range(start=chart_df.index[0], end=chart_df.index[-1])
                dt_breaks = [d.strftime('%Y-%m-%d') for d in dt_all if d.strftime('%Y-%m-%d') not in chart_dates]
                end_date_c = chart_df.index[-1]
                start_date_c = end_date_c - pd.DateOffset(years=1) if tf_interval == "1wk" else end_date_c - pd.DateOffset(months=3)

                # 【整體視覺格式化 (黑底/深色模式)】
                fig.update_layout(
                    plot_bgcolor='#000000',
                    paper_bgcolor='#000000',
                    font=dict(color='#FFFFFF'),
                    height=750, 
                    margin=dict(l=10, r=40, t=10, b=30), 
                    xaxis_rangeslider_visible=False,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(color="white", size=11)), 
                    hovermode="x unified"
                )
                
                # 更新格線顏色與Y軸位置(移至右側)
                fig.update_xaxes(
                    showgrid=True, gridcolor='#333333', gridwidth=0.5, zeroline=False,
                    range=[start_date_c, end_date_c],
                    rangebreaks=[dict(values=dt_breaks)],
                    row=3, col=1 # 日期標籤顯示在最底部
                )
                fig.update_yaxes(showgrid=True, gridcolor='#333333', gridwidth=0.5, side='right', zeroline=False)
                
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            else:
                st.warning("⚠️ 無法取得該標的的 K 線圖資料。")

with tab_rules:
    st.header("📖 雙指標波段系統 - 策略判斷原則 (MACD+20MA 濾網版)")
    st.markdown("""
    本策略將判斷核心大幅簡化，完全以**「日 MACD 金叉/死叉」**與**「收盤價相對於 20MA 的位置」**來進行無雜訊判斷：
    
    ---
    
    ### 🧭 核心交易法則
    
    1. **🟢 買進 / 續抱法則**
       * **觸發條件**：日 MACD 柱狀由綠翻紅（黃金交叉），**且** 股價站上日 20MA (月線)。
       * **動作**：多頭趨勢確立，果斷買進或安心續抱。
    2. **🔴 賣出 / 出清法則**
       * **觸發條件**：日 MACD 柱狀由紅翻綠（死亡交叉）。
       * **動作**：不論位階高低，動能一旦轉空，立即獲利了結或停損。
    3. **⚠️ 逃命波防禦濾網 (假金叉排除)**
       * **觸發條件**：日 MACD 柱狀雖翻紅，**但股價被壓在 20MA (月線) 之下**。
       * **動作**：此為空頭排列下的「弱勢反彈」或「逃命波」，**判定買進訊號無效，維持空手觀望，堅決不接刀！**
    """)

with tab_settings:
    st.subheader("⚙️ 編輯自選股清單")
    # ... (保持原樣)

with tab_war_room:
    st.subheader(f"⚔️ 買賣戰情室【{st.session_state.current_group_choice}】 (MACD 搭配 20MA 濾網版)")
    # ... (保持原樣)

with tab_deep_dive:
    st.subheader("🔬 個股走勢深度分析")
    # ... (保持原樣)

st.divider()
st.markdown("<div style='text-align: center; color: #888888; font-size: 14px; padding: 10px;'>本系統由 Robert 開發，僅供技術分析研究，非投資買賣建議</div>", unsafe_allow_html=True)
