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

# 自動重整機制：每 5 分鐘 (300,000 毫秒) 自動重新載入網頁並掃描訊號與定時報表
st_autorefresh(interval=5 * 60 * 1000, key="auto_refresh")

# ==========================================
# 台灣/香港標準時區 (UTC+8) 輔助函式
# ==========================================
TZ_TW = timezone(timedelta(hours=8))

def get_tw_now():
    """取得台灣標準時間 (UTC+8)"""
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
# 🎯 徹底修正：MACD + RSI 雙重共振背離判定 (排除假背離)
# ==========================================
def detect_dual_divergence(close_series, macd_dif_series, rsi_series, order=4, lookback=45):
    """
    絕對條件：
    1. 頂背離：當前收盤價必須『實質接近近 60 日最高點 (>= 97%)』且站穩 20MA，嚴禁在跌深低檔觸發
    2. 底背離：當前收盤價必須『實質接近近 60 日最低點 (<= 103%)』
    """
    if len(close_series) < lookback:
        return False, False

    c = close_series.iloc[-lookback:].values
    m = macd_dif_series.iloc[-lookback:].values
    r = rsi_series.iloc[-lookback:].values

    curr_p = c[-1]
    w_min = np.min(c)
    w_max = np.max(c)

    # 若現價離近 45 天最高點還有 5% 以上差距，直接封鎖頂背離！(徹底解決 202 元低檔喊頂背離的 Bug)
    allow_bear_div = (curr_p >= w_max * 0.96)
    # 若現價離近 45 天最低點高出 5% 以上，直接封鎖底背離！
    allow_bull_div = (curr_p <= w_min * 1.04)

    troughs = []
    peaks = []

    for i in range(order, len(c) - order):
        if c[i] == min(c[i - order:i + order + 1]):
            troughs.append(i)
        if c[i] == max(c[i - order:i + order + 1]):
            peaks.append(i)

    # 1. 雙重底背離
    is_dual_bull_div = False
    if allow_bull_div and len(troughs) >= 2:
        i1, i2 = troughs[-2], troughs[-1]
        if (len(c) - 1 - i2 <= 6) and (c[i2] < c[i1] * 0.995):
            if (m[i2] > m[i1]) and (r[i2] > r[i1]):
                is_dual_bull_div = True

    # 2. 雙重頂背離
    is_dual_bear_div = False
    if allow_bear_div and len(peaks) >= 2:
        p1, p2 = peaks[-2], peaks[-1]
        if (len(c) - 1 - p2 <= 6) and (c[p2] > c[p1] * 1.005):
            if (m[p2] < m[p1]) and (r[p2] < r[p1]):
                is_dual_bear_div = True

    return is_dual_bull_div, is_dual_bear_div

# ==========================================
# LINE Messaging API 推播與狀態快取
# ==========================================
def send_line_message(token, user_id, message_text):
    if not token or not user_id:
        return False, "缺少 Token 或 User ID"
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token.strip()}"
    }
    payload = {
        "to": user_id.strip(),
        "messages": [{"type": "text", "text": message_text}]
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=8)
        if res.status_code == 200:
            return True, "推播發送成功"
        else:
            return False, f"推播失敗: HTTP {res.status_code} - {res.text}"
    except Exception as e:
        return False, f"連線異常: {str(e)}"

def load_notified_cache():
    if os.path.exists(NOTIFICATION_CACHE_FILE):
        try:
            with open(NOTIFICATION_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_notified_cache(cache):
    try:
        with open(NOTIFICATION_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
    except Exception:
        pass

def build_morning_report(df_results, market_trend, group_name):
    now_tw = get_tw_now()
    today_str = now_tw.strftime("%Y-%m-%d")
    m_status = market_trend['status'] if market_trend else "維持觀察"
    m_advice = market_trend['advice'] if market_trend else "無大盤資料"

    up_stocks = df_results[df_results['建議'].str.contains("走勢向上|醞釀向上|破底分批加碼|底背離", na=False)] if not df_results.empty else pd.DataFrame()
    items_text = []
    if not up_stocks.empty:
        for _, row in up_stocks.head(6).iterrows():
            items_text.append(f"• {row['代碼']} {row['名稱']}: {row['建議']}")

    stocks_summary = "\n".join(items_text) if items_text else "• 目前無多頭轉強標的，多看少做。"

    msg = (
        f"🌅【雙指標系統 - 每日盤前早報】\n"
        f"━━━━━━━━━━━━━━\n"
        f"📅 日期：{today_str} (08:45 早報)\n"
        f"📁 組合：{group_name}\n\n"
        f"🧭 大盤資金水位：\n"
        f"狀態：{m_status}\n"
        f"指引：{m_advice}\n\n"
        f"⭐ 盤前多方焦點標的：\n"
        f"{stocks_summary}\n"
        f"━━━━━━━━━━━━━━\n"
        f"💡 提醒：若有觸發雙底背離或金叉，系統將於盤中即時推播。"
    )
    return msg

def build_evening_report(df_results, group_name):
    now_tw = get_tw_now()
    today_str = now_tw.strftime("%Y-%m-%d")
    total_count = len(df_results)
    up_cnt = len(df_results[df_results['建議'].str.contains("走勢向上", na=False)]) if not df_results.empty else 0
    prep_up_cnt = len(df_results[df_results['建議'].str.contains("醞釀向上", na=False)]) if not df_results.empty else 0
    dip_buy_cnt = len(df_results[df_results['建議'].str.contains("加碼|底背離", na=False)]) if not df_results.empty else 0
    trim_cnt = len(df_results[df_results['建議'].str.contains("減碼", na=False)]) if not df_results.empty else 0
    sell_cnt = len(df_results[df_results['建議'].str.contains("出清|破位", na=False)]) if not df_results.empty else 0

    action_items = []
    if not df_results.empty:
        for _, row in df_results.iterrows():
            if row['最新動態'] != "-":
                action_items.append(f"• {row['代碼']} {row['名稱']}: {row['最新動態']} ({row['建議']})")

    action_text = "\n".join(action_items[:6]) if action_items else "• 今日無新增均線/MACD/背離交叉訊號。"

    msg = (
        f"🌆【雙指標系統 - 每日盤後總結】\n"
        f"━━━━━━━━━━━━━━\n"
        f"📅 日期：{today_str} (13:45 盤後)\n"
        f"📁 組合：{group_name} (共 {total_count} 檔)\n\n"
        f"📊 盤後狀態分佈：\n"
        f"🟢 走勢向上：{up_cnt} 檔\n"
        f"💡 醞釀向上：{prep_up_cnt} 檔\n"
        f"🎯 破底加碼/底背離：{dip_buy_cnt} 檔\n"
        f"🟠 敏捷減碼(破10MA)：{trim_cnt} 檔\n"
        f"🔴 破位出清(破20MA)：{sell_cnt} 檔\n\n"
        f"⚡ 今日關鍵動態事件：\n"
        f"{action_text}\n"
        f"━━━━━━━━━━━━━━\n"
        f"📋 完整日誌可至『深度分析』匯出 CSV 進行盤後覆盤。"
    )
    return msg

def check_and_notify_signals(df_results, market_trend, group_name):
    token = st.session_state.line_token_input.strip()
    user_id = st.session_state.line_user_id_input.strip()
    if not token or not user_id:
        return

    cache = load_notified_cache()
    now_tw = get_tw_now()
    today_str = now_tw.strftime("%Y-%m-%d")
    now_time_str = now_tw.strftime("%H:%M:%S")

    if st.session_state.enable_line_notify_input and not df_results.empty:
        for _, row in df_results.iterrows():
            ticker = row['代碼']
            name = row['名稱']
            curr_rec = row['建議']
            actions = row['最新動態']
            price_info = row['收盤價(漲跌)']
            reason = row['詳細判定原因']

            item_cache = cache.get(ticker, {"last_rec": "", "last_gc_date": "", "last_div_date": ""})
            prev_rec = item_cache.get("last_rec", "")
            last_gc_date = item_cache.get("last_gc_date", "")
            last_div_date = item_cache.get("last_div_date", "")

            # 雙重底背離
            if "🔥 雙重底背離" in actions and last_div_date != today_str:
                msg = (
                    f"🔥【雙指標系統 - 雙重底背離大轉折】\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"標的：{ticker} {name}\n"
                    f"現價：{price_info}\n"
                    f"訊號：價格破底，但 MACD 與 RSI 同時低點抬高！\n"
                    f"建議：{curr_rec}\n"
                    f"時間：{now_time_str}\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"提示：空方推殺動能完全衰竭，雙指標強烈共振，大波段轉折爆發點！"
                )
                success, _ = send_line_message(token, user_id, msg)
                if success:
                    item_cache["last_div_date"] = today_str

            # 敏捷出場警報 (首次觸發才發送)
            elif "出清保本" in curr_rec and "出清保本" not in prev_rec and "空手" not in prev_rec:
                msg = (
                    f"🔴【雙指標系統 - 趨勢破位出場警報】\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"標的：{ticker} {name}\n"
                    f"現價：{price_info}\n"
                    f"建議：{curr_rec}\n"
                    f"原因：{reason}\n"
                    f"時間：{now_time_str}\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"提示：實質跌破 20MA 月線，多頭結構瓦解，紀律出清剩餘部位保本！"
                )
                send_line_message(token, user_id, msg)

            if "破底分批加碼" in curr_rec and "破底打底觀察" in prev_rec:
                msg = (
                    f"🚨【雙指標系統 - 破底加碼警報】\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"標的：{ticker} {name}\n"
                    f"現價：{price_info}\n"
                    f"狀態轉換：破底觀察 ➔ 🟢 破底分批加碼\n"
                    f"動態：{actions}\n"
                    f"原因：{reason}\n"
                    f"時間：{now_time_str}\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"提示：日線指標已正式轉強站穩 5MA，確認止跌，啟動左側金字塔分批加碼！"
                )
                success, _ = send_line_message(token, user_id, msg)
                if success:
                    item_cache["last_rec"] = curr_rec

            if "日MACD剛金叉" in actions and last_gc_date != today_str:
                msg = (
                    f"⚡【雙指標系統 - 日線金叉快訊】\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"標的：{ticker} {name}\n"
                    f"現價：{price_info}\n"
                    f"建議：{curr_rec}\n"
                    f"訊號：日線 MACD 正式黃金交叉翻多！\n"
                    f"原因：{reason}\n"
                    f"時間：{now_time_str}\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"提示：短期動能已由空翻多，請至戰情室檢視進場規劃。"
                )
                success, _ = send_line_message(token, user_id, msg)
                if success:
                    item_cache["last_gc_date"] = today_str

            item_cache["last_rec"] = curr_rec
            cache[ticker] = item_cache

    if st.session_state.enable_daily_reports_input and not df_results.empty:
        current_minute = now_tw.hour * 60 + now_tw.minute
        if 525 <= current_minute <= 535 and cache.get("last_morning_report_date") != today_str:
            morning_msg = build_morning_report(df_results, market_trend, group_name)
            ok, _ = send_line_message(token, user_id, morning_msg)
            if ok:
                cache["last_morning_report_date"] = today_str

        if 820 <= current_minute <= 835 and cache.get("last_evening_report_date") != today_str:
            evening_msg = build_evening_report(df_results, group_name)
            ok, _ = send_line_message(token, user_id, evening_msg)
            if ok:
                cache["last_evening_report_date"] = today_str

    save_notified_cache(cache)

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .block-container {
                padding-top: 1rem;
                padding-bottom: 0rem;
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# ==========================================
# 🎯 核心決策判斷引擎 (加入真實持倉狀態機)
# ==========================================
def evaluate_strategy_signal(
    curr_close, prev_close, c_vol, c_vol_ma5,
    c_ma5, c_ma10, c_ma20, p_close, p_ma20,
    c_hist, p_hist, c_rsi, c_lcl,
    is_high_momentum, is_buy_and_hold, stock_profile,
    is_broke_1y_low, low_1y_prev, percentile_1y,
    weekly_dif_decreasing, weekly_ma_dead, weekly_macd_dead,
    is_weekly_bullish, is_weekly_bottom_forming,
    is_dual_bull_div=False, is_dual_bear_div=False,
    was_holding=True, just_exited=False
):
    change_pct = ((curr_close - prev_close) / prev_close) * 100 if prev_close > 0 else 0

    # 1. 核心被動資產免出場
    if is_buy_and_hold:
        rec_text = "🔵 長期持有 (核心被動)"
        if "債" in stock_profile:
            detail_reason = "【免出場核心資產】純收息超短債，波動極低且穩定配息，免受技術指標干擾，建議長期續抱。"
        else:
            detail_reason = "【免出場核心資產】大盤原型指數，隨經濟成長滾動長期複利，不執行技術面停損停利，建議定期定額或逢低續抱。"
        return rec_text, detail_reason

    # 2. 雙重底背離 (最高優先起漲點)
    if is_dual_bull_div:
        rec_text = "🟢 雙重底背離 (爆發起漲點)"
        detail_reason = "【雙重底背離共振】價格創波段新低，但日線 MACD 與 RSI 同時低點抬高！空方動能耗盡，大轉折起漲在即，重注重點關注！"
        return rec_text, detail_reason

    # 3. 雙重頂背離 (必須有持股且在 20MA 上方的高檔才准觸發)
    if is_dual_bear_div and was_holding and curr_close > c_ma20:
        rec_text = "🟠 雙重頂背離 (強制減碼50%)"
        detail_reason = "【雙重頂背離共振】價格創波段新高，但 MACD 與 RSI 雙雙滑落，量價動能嚴重脫鉤，頭部成型風險極大，建議先行減碼 50% 鎖利！"
        return rec_text, detail_reason

    # 4. 破底處理 (方案 A 嚴格確認型)
    is_daily_golden_cross = (c_hist > 0) or (c_ma5 > c_ma10)
    is_above_ma5 = (curr_close > c_ma5)
    is_daily_stopping_drop = is_above_ma5 and is_daily_golden_cross

    if is_broke_1y_low:
        if is_daily_stopping_drop:
            rec_text = "🟢 破底分批加碼"
            detail_reason = f"【破底確認翻多】跌破近1年低點({low_1y_prev:.2f})後，日線已正式金叉(MACD或5MA翻多)且站上5MA，確認止跌轉強，啟動左側金字塔分批加碼！"
        else:
            rec_text = "🟡 破底打底觀察"
            detail_reason = f"【破底未止跌】跌破近1年低點({low_1y_prev:.2f})，但日線 MA/MACD 尚未金叉轉強，空方慣性未改，暫緩攤平、耐心等待翻多信號！"
        return rec_text, detail_reason

    # 5. SPC 極端超跌
    if curr_close <= c_lcl and c_vol > c_vol_ma5 * 2 and c_rsi < 30:
        rec_text = "🟢 逢低買入"
        detail_reason = f"【SPC極端超跌】跌破LCL、爆出2倍均量且RSI超賣({c_rsi:.1f})，籌碼換手醞釀強彈！"
        return rec_text, detail_reason

    # 🛡️ 6. 低檔超賣禁止追殺防護
    is_severely_oversold = (curr_close <= c_lcl) or (c_rsi <= 32.0)
    if is_severely_oversold:
        rec_text = "🟡 負乖離超賣 (暫緩追殺等待反彈)"
        detail_reason = f"【禁止殺跌防護】股價跌破布林下軌或 RSI 進入極度超賣({c_rsi:.1f})，隨時醞釀技術反彈，嚴禁在阿呆谷殺出持股，等待反彈再行處置。"
        return rec_text, detail_reason

    # 7. 判斷多頭進場條件 (要求連續 2 天站穩 20MA，過濾一日假突破！)
    is_standing_on_ma20_2days = (curr_close > c_ma20) and (p_close > p_ma20)
    target_pos_d = (50 if c_hist > 0 else 0) + (50 if c_ma5 > c_ma10 else 0)
    vol_condition_d = c_vol > c_vol_ma5

    # 8. 走勢向上 (標準右側多頭，必須連續站穩月線)
    if is_standing_on_ma20_2days and target_pos_d == 100 and vol_condition_d:
        if is_weekly_bullish:
            rec_text = "🟢 走勢向上"
            detail_reason = "【長短線共振帶量】週線維持長多，日線連續2日站穩月線且成交量超越5均量，波段強烈攻擊！"
        else:
            rec_text = "🟡 觀察 (短多長空)"
            detail_reason = "【短多長空】日線翻多帶量站穩月線，但週線長線格局尚未同步，暫作短線觀察。"
        return rec_text, detail_reason

    # 🎯 9. 高動能股專用：持倉狀態機 (終結天天重複叫人出清)
    if is_high_momentum:
        # A. 如果當前在月線 (20MA) 之下
        if curr_close < c_ma20:
            if was_holding or just_exited:
                # 剛剛跌破第一天：叫你出清！
                rec_text = "🔴 趨勢破位 (出清保本)"
                detail_reason = f"【動能型月線破位】收盤價({curr_close:.2f})實質跌破日 20MA 月線({c_ma20:.2f})，多頭防線瓦解，紀律出清剩餘部位保本！"
            else:
                # 已經跌破很多天：你手上根本沒股票，冷靜觀望即可！
                if is_weekly_bottom_forming:
                    rec_text = "💡 醞釀向上 (大底打底)"
                    detail_reason = "【月線下築底】目前無持股。週線MACD綠柱收斂，耐心等待日線連續2日站穩月線再行進場。"
                else:
                    rec_text = "⚪ 空手觀望 (破線無持股)"
                    detail_reason = f"【月線下空頭慣性】目前空手無部位。股價處於日 20MA({c_ma20:.2f}) 之下，空方主導，多看少做不接刀。"
            return rec_text, detail_reason

        # B. 如果在月線之上，但跌破 10MA：敏捷減碼 50%
        if curr_close < c_ma10 or (c_hist <= 0 and p_hist > 0):
            if was_holding:
                rec_text = "🟠 敏捷減碼 50% (跌破10MA)"
                detail_reason = f"【動能型第一防線】收盤價跌破日 10MA({c_ma10:.2f})或MACD翻空，短期動能衰退，先行減碼 50% 鎖住高檔獲利，其餘以 20MA 防守。"
            else:
                rec_text = "⚪ 空手觀望 (均線糾結)"
                detail_reason = "【未達進場標準】股價跌破 10MA 且尚未確立多頭慣性，空手者請勿躁進。"
            return rec_text, detail_reason

        # C. 突破第一天 (單日站上 20MA，但未滿 2 天)：警示防假突破
        if curr_close >= c_ma20 and p_close < p_ma20:
            rec_text = "🟡 突破月線觀察 (待站穩第2日)"
            detail_reason = f"【防假突破過濾】單日強彈突破月線({c_ma20:.2f})，需待明日收盤再次確認站穩月線方准正式進場，切勿盲目追高！"
            return rec_text, detail_reason

        # D. 月線上正常持股中
        if was_holding:
            rec_text = "🟡 抱牢主升 (高檔震盪)"
            detail_reason = "【動能型持股續抱】股價仍維持在 10MA 與 20MA 之上，多頭格局完好，抱牢主升段。"
        else:
            if is_standing_on_ma20_2days and (curr_close > c_ma5):
                rec_text = "🌟 醞釀向上 (週大底+日發動)"
                detail_reason = "【日線連續2天站穩20MA】波段起跑確認，可開始分批建倉佈局！"
            else:
                rec_text = "🟡 觀察 (盤整震盪)"
                detail_reason = "【盤整無方向】指標未完全共振，空手觀望。"
        return rec_text, detail_reason

    # 10. 穩健型股票常規防守規則
    else:
        if curr_close < c_ma20 and weekly_dif_decreasing:
            rec_text = "🔴 賣出 (日線敏捷)" if was_holding else "⚪ 空手觀望 (破線)"
            detail_reason = "【穩健型防守】跌破月線且週線 DIF 下降，保護獲利果斷全出。"
            return rec_text, detail_reason
        elif curr_close < c_ma10:
            rec_text = "🟠 建議減碼 (破10MA)" if was_holding else "⚪ 空手觀望"
            detail_reason = "【穩健型減碼】跌破 10MA，動能減弱，分批減碼 30%~50%。"
            return rec_text, detail_reason
        elif is_weekly_bottom_forming:
            rec_text = "💡 醞釀向上 (穩健築底)"
            detail_reason = "【週線大底沉澱】週MACD綠柱收斂，適合穩健買盤分批布局。"
            return rec_text, detail_reason
        else:
            rec_text = "🟡 觀察"
            detail_reason = "【方向分歧】指標未完全同步，維持觀望。"
            return rec_text, detail_reason

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
        
        if curr_hist > 0 and curr_hist > prev_hist:
            return {"status": "🟢 多頭擴張", "advice": "大盤趨勢向上，操作部位可適度放大至 80%~100%。", "color": "#e8f5e9"}
        elif curr_hist > 0 and curr_hist <= prev_hist:
            return {"status": "🟡 高檔震盪 (柱狀收斂)", "advice": "大盤動能減弱，維持現有持股，新部位需嚴格挑選帶量突破標的。", "color": "#fff8e1"}
        elif curr_hist < 0 and curr_hist > prev_hist:
            return {"status": "🟡 跌深反彈 (水下金叉)", "advice": "大盤有落底跡象，可以 30%~50% 資金小量試單，嚴設前低停損。", "color": "#fff8e1"}
        else:
            return {"status": "🔴 空頭發散", "advice": "大盤趨勢向下，建議縮小操作部位至 30% 以下，多看少做保本為主。", "color": "#ffebee"}
    except Exception:
        return None

@st.cache_data(ttl=300)
def analyze_signals_comprehensive(watchlist):
    results = []
    BUY_AND_HOLD_LIST = {
        "SGOV", "BIL", "SHV", "00719B.TW",
        "0050.TW", "VOO", "QQQM", "SPY", "IVV"
    }

    for ticker, name in watchlist.items():
        try:
            df_d = yf.download(ticker, period="1y", interval="1d", progress=False)
            if df_d.empty or len(df_d) < 35:
                results.append({
                    "代碼": ticker, "名稱": name, "收盤價(漲跌)": "⚠️ 無資料",
                    "股性模式": "⚪ 未知", "股性類別": "未知",
                    "建議": "⚪ 未知", "最新動態": "-",
                    "詳細判定原因": "無足夠日 K 線資料，請檢查代碼格式",
                    "Yahoo股市": f"https://finance.yahoo.com/quote/{ticker}"
                })
                continue

            close_d = df_d['Close'][ticker] if isinstance(df_d.columns, pd.MultiIndex) else df_d['Close']
            high_d = df_d['High'][ticker] if isinstance(df_d.columns, pd.MultiIndex) else df_d['High']
            low_d = df_d['Low'][ticker] if isinstance(df_d.columns, pd.MultiIndex) else df_d['Low']
            volume_d = df_d['Volume'][ticker] if isinstance(df_d.columns, pd.MultiIndex) else df_d['Volume']
            close_d, high_d, low_d, volume_d = close_d.dropna(), high_d.dropna(), low_d.dropna(), volume_d.dropna()

            df_w = yf.download(ticker, period="2y", interval="1wk", progress=False)
            close_w = df_w['Close'][ticker] if isinstance(df_w.columns, pd.MultiIndex) else df_w['Close']
            close_w = close_w.dropna()
            
            tr1 = high_d - low_d
            tr2 = (high_d - close_d.shift(1)).abs()
            tr3 = (low_d - close_d.shift(1)).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr14 = tr.rolling(14).mean().iloc[-1]
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
            lcl_d = ma20_d - 2 * std20_d
            curr_lcl_d = lcl_d.iloc[-1]
            
            curr_ma5_d, curr_ma10_d, curr_ma20_d = ma5_d.iloc[-1], ma10_d.iloc[-1], ma20_d.iloc[-1]
            prev_ma20_d = ma20_d.iloc[-2]
            curr_hist_d, prev_hist_d = hist_d.iloc[-1], hist_d.iloc[-2]
            curr_vol_d, curr_vol_ma5_d = volume_d.iloc[-1], vol_ma5_d.iloc[-1]

            # 判斷是否在前一交易日仍在月線上 (判斷持倉狀態)
            was_holding_prev = (prev_close >= prev_ma20_d)
            just_exited = (prev_close >= prev_ma20_d and curr_close < curr_ma20_d)

            is_dual_bull_div, is_dual_bear_div = detect_dual_divergence(close_d, dif_d, rsi_d)

            if len(close_w) >= 35:
                ma5_w, ma10_w = close_w.rolling(5).mean(), close_w.rolling(10).mean()
                ema12_w, ema26_w = close_w.ewm(span=12, adjust=False).mean(), close_w.ewm(span=26, adjust=False).mean()
                dif_w = ema12_w - ema26_w
                hist_w = dif_w - dif_w.ewm(span=9, adjust=False).mean()
                
                curr_dif_w, prev_dif_w = dif_w.iloc[-1], dif_w.iloc[-2]
                weekly_dif_decreasing = curr_dif_w < prev_dif_w
                weekly_ma_dead = (ma5_w.iloc[-1] < ma10_w.iloc[-1])
                weekly_macd_dead = (hist_w.iloc[-1] <= 0)
                is_weekly_bullish = (hist_w.iloc[-1] > 0 and ma5_w.iloc[-1] > ma10_w.iloc[-1])
                is_weekly_bottom_forming = (hist_w.iloc[-1] < 0 and hist_w.iloc[-1] > hist_w.iloc[-2]) or (close_w.iloc[-1] > ma5_w.iloc[-1] and hist_w.iloc[-1] < 0)
            else:
                weekly_dif_decreasing = False
                weekly_ma_dead = False
                weekly_macd_dead = False
                is_weekly_bullish = True
                is_weekly_bottom_forming = False

            change_pct = ((curr_close - prev_close) / prev_close) * 100
            if change_pct > 0: price_display = f"🔺 {curr_close:.2f} (+{change_pct:.2f}%)"
            elif change_pct < 0: price_display = f"🔻 {curr_close:.2f} ({change_pct:.2f}%)"
            else: price_display = f"➖ {curr_close:.2f} (0.00%)"
            
            last_date_str = close_d.index[-1].strftime('%m/%d')
            actions = []
            if is_dual_bull_div:
                actions.append(f"🔥雙重底背離({last_date_str})")
            elif is_dual_bear_div:
                actions.append(f"⚠️雙重頂背離({last_date_str})")

            if prev_close <= prev_ma20_d and curr_close > curr_ma20_d:
                actions.append(f"日線突破20MA ({last_date_str})")
            if prev_hist_d <= 0 and curr_hist_d > 0:
                actions.append(f"日MACD剛金叉 ({last_date_str})")
            elif prev_hist_d >= 0 and curr_hist_d < 0:
                actions.append(f"日MACD剛死叉 ({last_date_str})")

            rec_text, detail_reason = evaluate_strategy_signal(
                curr_close, prev_close, curr_vol_d, curr_vol_ma5_d,
                curr_ma5_d, curr_ma10_d, curr_ma20_d, prev_close, prev_ma20_d,
                curr_hist_d, prev_hist_d, curr_rsi_d, curr_lcl_d,
                is_high_momentum, is_buy_and_hold, stock_profile,
                is_broke_1y_low, low_1y_prev, percentile_1y,
                weekly_dif_decreasing, weekly_ma_dead, weekly_macd_dead,
                is_weekly_bullish, is_weekly_bottom_forming,
                is_dual_bull_div, is_dual_bear_div,
                was_holding_prev, just_exited
            )

            results.append({
                "代碼": ticker, 
                "名稱": name, 
                "收盤價(漲跌)": price_display,
                "股性模式": stock_profile,
                "股性類別": stock_category,
                "建議": rec_text,
                "最新動態": " / ".join(actions) if actions else "-",
                "詳細判定原因": detail_reason,
                "Yahoo股市": f"https://finance.yahoo.com/quote/{ticker}"
            })
        except Exception:
            results.append({
                "代碼": ticker, "名稱": name, "收盤價(漲跌)": "⚠️ 錯誤",
                "股性模式": "⚪ 異常", "股性類別": "未知",
                "建議": "⚪ 未知", "最新動態": "-",
                "詳細判定原因": "抓取過程發生異常，請稍後刷新",
                "Yahoo股市": f"https://finance.yahoo.com/quote/{ticker}"
            })
            continue

    df_results = pd.DataFrame(results)
    if not df_results.empty:
        def get_sort_rank(row):
            if "底背離" in row['建議']: return 0
            elif "破底分批加碼" in row['建議']: return 1
            elif "走勢向上" in row['建議']: return 2  
            elif "週大底+日發動" in row['建議']: return 3
            elif "週大底打底" in row['建議']: return 4
            elif "長期持有" in row['建議']: return 5
            elif "破底打底觀察" in row['建議']: return 6
            elif "歷史低檔打底" in row['建議']: return 7
            elif "頂背離" in row['建議']: return 8
            elif "敏捷減碼" in row['建議']: return 9
            elif "負乖離超賣" in row['建議']: return 10
            elif "趨勢破位" in row['建議']: return 11
            elif "突破月線觀察" in row['建議']: return 12
            elif "空手觀望" in row['建議']: return 13
            elif "觀察" in row['建議']: return 14
            else: return 15
        df_results['SortRank'] = df_results.apply(get_sort_rank, axis=1)
        df_results = df_results.sort_values(by=['SortRank', '代碼']).drop(columns=['SortRank']).reset_index(drop=True)
        
    return df_results

# ==========================================
# 歷史逐日狀態回溯引擎 (專門按時間順序維護真實持倉狀態)
# ==========================================
@st.cache_data(ttl=300)
def generate_historical_signals_table(ticker, name, start_date, end_date):
    BUY_AND_HOLD_LIST = {
        "SGOV", "BIL", "SHV", "00719B.TW",
        "0050.TW", "VOO", "QQQM", "SPY", "IVV"
    }

    fetch_start = start_date - timedelta(days=400)
    fetch_end = end_date + timedelta(days=2)
    df_d = yf.download(ticker, start=fetch_start.strftime('%Y-%m-%d'), end=fetch_end.strftime('%Y-%m-%d'), interval="1d", progress=False)
    if df_d.empty or len(df_d) < 35:
        return pd.DataFrame(), None

    if isinstance(df_d.columns, pd.MultiIndex):
        df_d.columns = df_d.columns.get_level_values(0)
    df_d = df_d.dropna()

    close = df_d['Close']
    high = df_d['High']
    low = df_d['Low']
    volume = df_d['Volume']

    ma5 = close.rolling(5).mean()
    ma10 = close.rolling(10).mean()
    ma20 = close.rolling(20).mean()
    vol_ma5 = volume.rolling(5).mean()

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr14 = tr.rolling(14).mean()

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()
    hist = dif - dea

    delta = close.diff()
    g = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
    l = (-1 * delta.clip(upper=0)).ewm(com=13, adjust=False).mean()
    rsi = 100 - (100 / (1 + (g / l)))

    std20 = close.rolling(20).std()
    lcl = ma20 - 2 * std20

    df_w = yf.download(ticker, period="3y", interval="1wk", progress=False)
    if not df_w.empty and len(df_w) >= 35:
        if isinstance(df_w.columns, pd.MultiIndex): df_w.columns = df_w.columns.get_level_values(0)
        close_w = df_w['Close'].dropna()
        ema12_w = close_w.ewm(span=12, adjust=False).mean()
        ema26_w = close_w.ewm(span=26, adjust=False).mean()
        dif_w = ema12_w - ema26_w
        hist_w = dif_w - dif_w.ewm(span=9, adjust=False).mean()
        ma5_w = close_w.rolling(5).mean()
        ma10_w = close_w.rolling(10).mean()
    else:
        dif_w = pd.Series(dtype=float)
        hist_w = pd.Series(dtype=float)
        ma5_w = pd.Series(dtype=float)
        ma10_w = pd.Series(dtype=float)

    is_buy_and_hold = (ticker in BUY_AND_HOLD_LIST) or ("美債" in name and "0-3" in name)

    # 必須依【時間由舊到新】正向模擬持倉狀態機，最後再倒序呈現！
    trading_dates_forward = [d for d in df_d.index if d.date() <= end_date]
    trading_dates_forward.sort()

    sim_holding = False
    all_computed_records = []

    for dt in trading_dates_forward:
        loc = df_d.index.get_loc(dt)
        if loc < 35: continue

        c_close = close.iloc[loc]
        p_close = close.iloc[loc - 1]
        c_high = high.iloc[loc]
        c_low = low.iloc[loc]
        c_vol = volume.iloc[loc]
        c_vol_ma5 = vol_ma5.iloc[loc]

        c_ma5 = ma5.iloc[loc]
        c_ma10 = ma10.iloc[loc]
        c_ma20 = ma20.iloc[loc]
        p_ma20 = ma20.iloc[loc - 1]

        c_hist = hist.iloc[loc]
        p_hist = hist.iloc[loc - 1]
        c_rsi = rsi.iloc[loc]
        c_lcl = lcl.iloc[loc]

        c_atr14 = atr14.iloc[loc]
        atr_pct = (c_atr14 / c_close) * 100 if c_close > 0 else 0

        if is_buy_and_hold:
            is_high_momentum = False
            stock_profile = "💰 核心·收息存債" if ("SGOV" in ticker or "債" in name) else "🏛️ 核心·指數複利"
        else:
            is_high_momentum = (atr_pct >= 3.5)
            stock_profile = f"🚀 動能({atr_pct:.1f}%)" if is_high_momentum else f"🏛️ 穩健({atr_pct:.1f}%)"

        lookback_len = min(250, loc)
        h_1y = high.iloc[loc - lookback_len:loc + 1].max()
        l_1y_prev = low.iloc[loc - lookback_len:loc].min() if lookback_len > 1 else low.iloc[loc]
        l_1y = min(l_1y_prev, c_low)
        percentile_1y = ((c_close - l_1y) / (h_1y - l_1y)) * 100 if h_1y > l_1y else 50.0

        is_broke_1y_low = (c_close <= l_1y_prev * 1.01) or (percentile_1y <= 10.0)

        # 背離計算
        sub_c = close.iloc[:loc+1]
        sub_m = dif.iloc[:loc+1]
        sub_r = rsi.iloc[:loc+1]
        h_dual_bull, h_dual_bear = detect_dual_divergence(sub_c, sub_m, sub_r)

        weekly_dif_decreasing = False
        is_weekly_bullish = True
        weekly_macd_dead = False
        weekly_ma_dead = False
        is_weekly_bottom_forming = False

        if not dif_w.empty:
            w_idx = dif_w.index[dif_w.index <= dt]
            if len(w_idx) >= 2:
                w_curr_dif = dif_w.loc[w_idx[-1]]
                w_prev_dif = dif_w.loc[w_idx[-2]]
                weekly_dif_decreasing = (w_curr_dif < w_prev_dif)
                w_curr_hist = hist_w.loc[w_idx[-1]]
                w_prev_hist = hist_w.loc[w_idx[-2]]
                w_curr_ma5 = ma5_w.loc[w_idx[-1]]
                w_curr_ma10 = ma10_w.loc[w_idx[-1]]

                weekly_ma_dead = (w_curr_ma5 < w_curr_ma10)
                weekly_macd_dead = (w_curr_hist <= 0)
                is_weekly_bullish = (w_curr_hist > 0 and w_curr_ma5 > w_curr_ma10)
                is_weekly_bottom_forming = (w_curr_hist < 0 and w_curr_hist > w_prev_hist) or (w_curr_hist < 0 and c_close > w_curr_ma5)

        change_pct = ((c_close - p_close) / p_close) * 100
        if change_pct > 0: price_display = f"🔺 {c_close:.2f} (+{change_pct:.2f}%)"
        elif change_pct < 0: price_display = f"🔻 {c_close:.2f} ({change_pct:.2f}%)"
        else: price_display = f"➖ {c_close:.2f} (0.00%)"

        date_str = dt.strftime('%Y/%m/%d')
        date_short = dt.strftime('%m/%d')

        actions = []
        if h_dual_bull: actions.append(f"🔥雙重底背離({date_short})")
        elif h_dual_bear: actions.append(f"⚠️雙重頂背離({date_short})")

        if p_close <= p_ma20 and c_close > c_ma20: actions.append(f"日線突破20MA ({date_short})")
        if p_hist <= 0 and c_hist > 0: actions.append(f"日MACD剛金叉 ({date_short})")
        elif p_hist >= 0 and c_hist < 0: actions.append(f"日MACD剛死叉 ({date_short})")

        # 模擬持倉判斷
        just_exited = (sim_holding and c_close < c_ma20)

        rec_text, detail_reason = evaluate_strategy_signal(
            c_close, p_close, c_vol, c_vol_ma5,
            c_ma5, c_ma10, c_ma20, p_close, p_ma20,
            c_hist, p_hist, c_rsi, c_lcl,
            is_high_momentum, is_buy_and_hold, stock_profile,
            is_broke_1y_low, l_1y_prev, percentile_1y,
            weekly_dif_decreasing, weekly_ma_dead, weekly_macd_dead,
            is_weekly_bullish, is_weekly_bottom_forming,
            h_dual_bull, h_dual_bear,
            sim_holding, just_exited
        )

        # 動態更新持倉狀態機
        if "走勢向上" in rec_text or "醞釀向上 (週大底+日發動)" in rec_text or "雙重底背離" in rec_text or "破底分批加碼" in rec_text:
            sim_holding = True
        elif "趨勢破位" in rec_text or "出清保本" in rec_text:
            sim_holding = False

        if start_date <= dt.date() <= end_date:
            all_computed_records.append({
                "日期": date_str,
                "代碼": ticker,
                "名稱": name,
                "收盤價(漲跌)": price_display,
                "股性模式": stock_profile,
                "建議": rec_text,
                "最新動態": " / ".join(actions) if actions else "-",
                "詳細判定原因": detail_reason
            })

    # 依日期由新到舊倒序呈現
    all_computed_records.reverse()

    ma5_deduction_info = None
    if len(close) >= 5:
        curr_p = close.iloc[-1]
        deduction_price = close.iloc[-5]
        sum_prev_4 = close.iloc[-4:].sum()
        stand_on_ma5_price = sum_prev_4 / 4.0
        turn_up_price = deduction_price
        diff_pct = ((turn_up_price - curr_p) / curr_p) * 100 if curr_p > 0 else 0
        stand_diff_pct = ((stand_on_ma5_price - curr_p) / curr_p) * 100 if curr_p > 0 else 0

        ma5_deduction_info = {
            "current_price": curr_p,
            "deduction_price": deduction_price,
            "turn_up_price": turn_up_price,
            "turn_up_diff_pct": diff_pct,
            "stand_on_ma5_price": stand_on_ma5_price,
            "stand_diff_pct": stand_diff_pct
        }

    return pd.DataFrame(all_computed_records), ma5_deduction_info

# ==========================================
# 深度分析綜合判斷結論生成函數
# ==========================================
def generate_summary_insight(df_records, ticker, name, ma5_info=None):
    if df_records.empty:
        return ""
    
    latest_row = df_records.iloc[0]
    latest_date = latest_row['日期']
    latest_rec = latest_row['建議']
    latest_reason = latest_row['詳細判定原因']
    latest_profile = latest_row['股性模式']
    
    rec_counts = df_records['建議'].value_counts()
    dominant_rec = rec_counts.index[0]
    total_days = len(df_records)
    
    if "底背離" in latest_rec:
        trend_status = "🔥 雙重底背離強勢反轉結構（最優質起漲點）"
        action_advice = "股價創低但 MACD 與 RSI 同步墊高，空方動能耗盡，大轉折向上概率極高，可積極分批布局加碼！"
        box_color = "#e8f5e9"
        border_color = "#81c784"
    elif "頂背離" in latest_rec:
        trend_status = "⚠️ 雙重頂背離高檔見頂結構（頭部風險）"
        action_advice = "股價創新高但 MACD 與 RSI 雙雙衰退，量價背離明顯，多頭無力推升，建議果斷減碼 50% 鎖利！"
        box_color = "#fff3e0"
        border_color = "#ffb74d"
    elif "長期持有" in latest_rec:
        trend_status = "🔵 核心被動持有結構（不執行波段停損停利）"
        action_advice = "隨全球總體經濟長期成長滾動複利或穩定收取配息，免受短期技術指標干擾，建議定期定額或逢低持續續抱。"
        box_color = "#e3f2fd"
        border_color = "#90caf9"
    elif "破底分批加碼" in latest_rec:
        trend_status = "🟢 破底翻多築底確認（左側進場區）"
        action_advice = "已跌破近 1 年低點但日線雙指標翻多站穩 5MA，空方動能耗盡，可採取金字塔分批攤平加碼策略，切勿恐慌殺低。"
        box_color = "#e8f5e9"
        border_color = "#a5d6a7"
    elif "走勢向上" in latest_rec:
        trend_status = "🟢 順勢多頭波段（右側攻擊架構）"
        action_advice = "長短線指標維持共振多頭，波段趨勢向上確立，持股者續抱主升段，新進部位以 10MA 或 20MA 為移動防守基準。"
        box_color = "#e8f5e9"
        border_color = "#a5d6a7"
    elif "敏捷減碼" in latest_rec:
        trend_status = "🟠 高檔短期轉弱（跌破 10MA 鎖利點）"
        action_advice = "股價跌破日 10MA 或日 MACD 翻綠，短期動能衰退，建議立即減碼 50% 鎖住獲利，其餘部位以 20MA 月線作最後防線。"
        box_color = "#fff3e0"
        border_color = "#ffb74d"
    elif "趨勢破位" in latest_rec or "出清保本" in latest_rec:
        trend_status = "🔴 趨勢破位出清（跌破 20MA 月線防線）"
        action_advice = "實質跌破 20MA 月線，多頭架構結束。空手者切勿貿然進場接刀；持股者應嚴格落實紀律，出清剩餘部位保本。"
        box_color = "#ffebee"
        border_color = "#ef9a9a"
    elif "空手觀望" in latest_rec:
        trend_status = "⚪ 空手觀望結構（無部位耐心等待）"
        action_advice = "股價處於月線下方空頭架構，手上無持股。保留現金銀彈，耐心等待股價實質站回月線或出現大底背離再行進場。"
        box_color = "#f5f5f5"
        border_color = "#e0e0e0"
    elif "負乖離超賣" in latest_rec:
        trend_status = "🟡 極端負乖離超賣區（等待技術反彈）"
        action_advice = "股價跌破布林下軌且 RSI 處於嚴重超賣，隨時醞釀技術性急彈，切勿在此刻恐慌殺低在阿呆谷，等待回測 10MA 再行減碼。"
        box_color = "#fff8e1"
        border_color = "#ffe082"
    else:
        trend_status = "🟡 震盪整理／方向未明觀察區"
        action_advice = "多空指標未完全同步，方向尚不明朗。多看少做，保留充裕現金，靜待關鍵型態或帶量長紅明確表態。"
        box_color = "#f5f5f5"
        border_color = "#e0e0e0"

    event_notes = []
    actions_found = [act for act in df_records['最新動態'] if act != "-"]
    if actions_found:
        event_notes.append(f"區間內觸發關鍵動態：{'、'.join(set(actions_found))}")
    if (df_records['收盤價(漲跌)'].str.contains(r'\+([5-9]|\d{2})\.')).any():
        event_notes.append("區間內曾出現單日漲幅逾 5% 的強彈衝刺，但需提防是否為空頭架構下的假突破。")
    if (df_records['收盤價(漲跌)'].str.contains(r'\-([5-9]|\d{2})\.')).any():
        event_notes.append("區間內曾遭逢單日大跌逾 5% 的長黑賣壓，空方籌碼尚未完全消化。")

    event_text = ("；".join(event_notes) + "。") if event_notes else "區間內無特殊突發量價突破事件，維持常態波動走勢。"

    ma5_html = ""
    if ma5_info:
        ma5_html = f'<div style="margin: 6px 0; font-size: 14px; color: #1565c0;"><b>【明日 5MA 翻揚展望】</b>：明日扣抵價為 <b>{ma5_info["deduction_price"]:.2f} 元</b>。明日收盤需達 <b>{ma5_info["stand_on_ma5_price"]:.2f} 元 ({ma5_info["stand_diff_pct"]:+.2f}%)</b> 方能實質站上 5MA；需收在 <b>{ma5_info["turn_up_price"]:.2f} 元 ({ma5_info["turn_up_diff_pct"]:+.2f}%)</b> 以上，日 5MA 斜率才會正式走平翻揚向上。</div>'

    lines = [
        f'<div style="background-color: {box_color}; border: 1.5px solid {border_color}; border-radius: 8px; padding: 16px 20px; margin-top: 20px;">',
        f'<h4 style="margin: 0 0 10px 0; color: #1a1a1a; font-size: 18px;">💡 綜合判斷結論：{ticker} - {name}</h4>',
        f'<div style="margin: 6px 0; font-size: 15px; color: #222;"><b>【當前定調】</b>：<span style="font-weight: bold;">{trend_status}</span></div>',
        f'<div style="margin: 6px 0; font-size: 14px; color: #444;"><b>【最新狀態 ({latest_date})】</b>：<b>{latest_rec}</b> ｜ 股性：<b>{latest_profile}</b> ｜ 原因：{latest_reason}</div>',
        ma5_html,
        f'<div style="margin: 6px 0; font-size: 14px; color: #444;"><b>【區間走勢特徵】</b>：過去 {total_days} 個交易日中，以「{dominant_rec}」為主要常態。{event_text}</div>',
        f'<div style="margin: 10px 0 0 0; font-size: 15px; font-weight: bold; color: #b71c1c;">🎯 實戰操作建議：{action_advice}</div>',
        '</div>'
    ]
    return "".join(lines)

def style_dataframe(df):
    def color_trend(val):
        if isinstance(val, str):
            if '🔺' in val: return 'color: #ff4b4b; font-weight: bold;'
            elif '🔻' in val: return 'color: #00c853; font-weight: bold;'
            elif '⚠️' in val: return 'color: #f57c00; font-weight: bold;'
        return ''
    def color_profile(val):
        if isinstance(val, str):
            if '🚀' in val: return 'color: #d81b60; font-weight: bold;'
            elif '🏛️' in val: return 'color: #1976d2; font-weight: bold;'
            elif '💰' in val: return 'color: #2e7d32; font-weight: bold;'
        return ''
    def color_rec(val):
        if isinstance(val, str):
            if '雙重底背離' in val: return 'color: #1b5e20; font-weight: bold; background-color: #a5d6a7;'
            elif '雙重頂背離' in val: return 'color: #b71c1c; font-weight: bold; background-color: #ffcdd2;'
            elif '敏捷減碼' in val: return 'color: #e65100; font-weight: bold; background-color: #ffe0b2;'
            elif '趨勢破位' in val or '出清保本' in val: return 'color: #b71c1c; font-weight: bold; background-color: #ffcdd2;'
            elif '空手觀望' in val: return 'color: #616161; font-weight: bold; background-color: #eeeeee;'
            elif '破底分批加碼' in val: return 'color: #1b5e20; font-weight: bold; background-color: #c8e6c9;'
            elif '走勢向上' in val: return 'color: #2e7d32; font-weight: bold; background-color: #e8f5e9;'
            elif '破底打底觀察' in val: return 'color: #b78103; font-weight: bold; background-color: #fff9c4;'
            elif '長期持有' in val: return 'color: #0d47a1; font-weight: bold; background-color: #e3f2fd;'
            elif '週大底+日發動' in val: return 'color: #2e7d32; font-weight: bold; background-color: #e8f5e9;'
            elif '負乖離超賣' in val: return 'color: #f57f17; font-weight: bold; background-color: #fffde7;'
        return ''
        
    res = df.style
    if hasattr(res, "map"):
        if '收盤價(漲跌)' in df.columns: res = res.map(color_trend, subset=['收盤價(漲跌)'])
        if '股性模式' in df.columns: res = res.map(color_profile, subset=['股性模式'])
        if '建議' in df.columns: res = res.map(color_rec, subset=['建議'])
    else:
        if '收盤價(漲跌)' in df.columns: res = res.applymap(color_trend, subset=['收盤價(漲跌)'])
        if '股性模式' in df.columns: res = res.applymap(color_profile, subset=['股性模式'])
        if '建議' in df.columns: res = res.applymap(color_rec, subset=['建議'])
    return res

@st.cache_data(ttl=300)
def get_chart_data(ticker, interval, period):
    df = yf.download(ticker, period=period, interval=interval, progress=False)
    if df.empty: return None
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    df = df.dropna()
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean() 
    df['Vol_MA5'] = df['Volume'].rolling(window=5).mean()
    
    df['STD20'] = df['Close'].rolling(window=20).std()
    df['UCL'] = df['MA20'] + 2 * df['STD20']
    df['LCL'] = df['MA20'] - 2 * df['STD20']

    df['DIF'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
    df['DEA'] = df['DIF'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['DIF'] - df['DEA']
    df['MACD_Color'] = ['#ef5350' if val > 0 else '#26a69a' for val in df['MACD_Hist']]
    
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    ema_gain = gain.ewm(com=13, adjust=False).mean()
    ema_loss = loss.ewm(com=13, adjust=False).mean()
    rs = ema_gain / ema_loss
    df['RSI'] = 100 - (100 / (1 + rs))

    df['Candle_Dir'] = df['Close'] >= df['Open']
    df['Vol_Color'] = ['#ef5350' if d else '#26a69a' for d in df['Candle_Dir']]
    return df

# ==========================================
# 🎯 頁面分頁宣告
# ==========================================
tab_dashboard, tab_rules, tab_settings, tab_war_room, tab_deep_dive = st.tabs([
    "📊 看盤儀表板", "📖 策略判斷原則", "⚙️ 自選股編輯", "⚔️ 買賣戰情室", "🔬 深度分析"
])

if st.session_state.current_group_choice == "自選股 2":
    ACTIVE_WATCHLIST = parse_watchlist(st.session_state.watchlist_2_text)
elif st.session_state.current_group_choice == "自選股 3":
    ACTIVE_WATCHLIST = parse_watchlist(st.session_state.watchlist_3_text)
else:
    ACTIVE_WATCHLIST = parse_watchlist(st.session_state.watchlist_1_text)

# 快取獲取當前自選股資料
display_df = analyze_signals_comprehensive(ACTIVE_WATCHLIST)
market_trend_global = get_market_trend(st.session_state.market_ticker_input)

# 背景自動檢查訊號與定時早晚報
check_and_notify_signals(display_df, market_trend_global, st.session_state.current_group_choice)

# ==========================================
# 分頁 1：主看盤儀表板 
# ==========================================
with tab_dashboard:
    col_group, col_empty = st.columns([1, 1])
    with col_group:
        current_group = st.radio(
            "📌 選擇自選股組合 (標準預設為自選股 1)：", 
            ["自選股 1", "自選股 2", "自選股 3"], 
            index=["自選股 1", "自選股 2", "自選股 3"].index(st.session_state.current_group_choice),
            horizontal=True
        )
        if current_group != st.session_state.current_group_choice:
            st.session_state.current_group_choice = current_group
            save_settings()
            st.rerun()

    market_ticker = st.text_input("📊 設定總體資金水位參考標的 (預設 0050.TW)：", key="market_ticker_input", on_change=update_other_inputs).strip().upper()
    if market_trend_global:
        st.markdown(
            f'''
            <div style="background-color: {market_trend_global['color']}; padding: 15px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #ccc;">
                <h4 style="margin: 0; color: #333;">🧭 總體資金水位儀表板 ({market_ticker})</h4>
                <p style="margin: 5px 0 0 0; font-size: 18px; font-weight: bold; color: #333;">狀態：{market_trend_global['status']}</p>
                <p style="margin: 5px 0 0 0; color: #555;">💡 建議：{market_trend_global['advice']}</p>
            </div>
            ''', unsafe_allow_html=True
        )
    else:
        st.warning(f"⚠️ 無法取得 {market_ticker} 的資料，請確認代碼是否正確。")

    st.divider()
    st.subheader("🔍 臨時標的快速分析")
    col_temp1, col_temp2, col_temp3 = st.columns([2, 2, 2])
    with col_temp1:
        st.text_input("輸入代碼 (例：2317.TW)", key="search_ticker", on_change=update_selected_from_search)
    with col_temp2:
        st.text_input("輸入名稱 (選填，例：鴻海)", key="search_name", on_change=update_other_inputs)

    temp_ticker = st.session_state.search_ticker.strip().upper()
    temp_name = st.session_state.search_name.strip()

    if temp_ticker:
        disp_name = temp_name if temp_name else temp_ticker
        temp_dict = {temp_ticker: disp_name}
        with st.spinner(f"正在綜合分析 {temp_ticker}..."):
            temp_df = analyze_signals_comprehensive(temp_dict)
            
        if not temp_df.empty and "⚠️ 無資料" not in temp_df.iloc[0]['收盤價(漲跌)']:
            st.dataframe(
                style_dataframe(temp_df.drop(columns=['股性類別'])), 
                use_container_width=True,
                column_config={"Yahoo股市": st.column_config.LinkColumn("🔗 Yahoo股市", display_text="點擊前往")}
            )
            with col_temp3:
                st.write("") 
                st.write("")
                if st.button(f"➕ 加入到當前【{st.session_state.current_group_choice}】"):
                    target_key = "watchlist_1_text" if st.session_state.current_group_choice == "自選股 1" else ("watchlist_2_text" if st.session_state.current_group_choice == "自選股 2" else "watchlist_3_text")
                    if temp_ticker not in st.session_state[target_key]:
                        st.session_state[target_key] += f"\n{temp_ticker},{disp_name}"
                        save_settings()
                        st.rerun()
                    else:
                        st.warning(f"此標的已在【{st.session_state.current_group_choice}】中。")
        else:
            st.error("無法取得該代碼資料，請確認代碼是否正確。")
    st.divider()

    if not display_df.empty:
        st.subheader(f"📊 【{st.session_state.current_group_choice}】狀態總覽 (長短線綜合唯一解 - 共 {len(display_df)} 檔)")
        
        filter_opt = st.radio(
            "🔍 狀態篩選：", 
            ["👀 顯示全部", "🔥 雙重底背離", "🟢 破底加碼", "🟢 只看走勢向上", "💡 醞釀向上", "🔵 長期持有", "🟡 歷史打底", "🟠 敏捷減碼(破10MA)", "🔴 趨勢破位(出清)", "⚪ 空手觀望", "🟡 負乖離超賣", "⚡ 剛發生交叉"], 
            index=0,
            horizontal=True
        )
        
        filtered_df = display_df.copy()
        if filter_opt == "🔥 雙重底背離":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("底背離", na=False)]
        elif filter_opt == "🟢 破底加碼":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("破底分批加碼", na=False)]
        elif filter_opt == "🟢 只看走勢向上":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("走勢向上", na=False)]
        elif filter_opt == "💡 醞釀向上":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("醞釀向上", na=False)]
        elif filter_opt == "🔵 長期持有":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("長期持有", na=False)]
        elif filter_opt == "🟡 歷史打底":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("歷史低檔打底", na=False)]
        elif filter_opt == "🟠 敏捷減碼(破10MA)":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("減碼", na=False)]
        elif filter_opt == "🔴 趨勢破位(出清)":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("破位|出清", na=False)]
        elif filter_opt == "⚪ 空手觀望":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("空手觀望", na=False)]
        elif filter_opt == "🟡 負乖離超賣":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("負乖離超賣", na=False)]
        elif filter_opt == "⚡ 剛發生交叉":
            filtered_df = filtered_df[filtered_df['最新動態'] != "-"]

        df_steady = filtered_df[filtered_df['股性類別'] == "穩健型"].drop(columns=['股性類別']).reset_index(drop=True)
        df_momentum = filtered_df[filtered_df['股性類別'] == "高動能型"].drop(columns=['股性類別']).reset_index(drop=True)

        st.markdown(f"#### 🏛️ 穩健權值 / 核心長期持有型 ({len(df_steady)} 檔)")
        if df_steady.empty:
            st.info("目前無符合篩選條件的穩健型標的。")
        else:
            ev_steady = st.dataframe(
                style_dataframe(df_steady), 
                use_container_width=True,
                on_select="rerun",          
                selection_mode="single-row",
                key="table_steady",
                column_config={"Yahoo股市": st.column_config.LinkColumn("🔗 Yahoo股市", display_text="點擊前往")}
            )
            if ev_steady.selection.rows:
                selected_row_idx = ev_steady.selection.rows[0]
                st.session_state.selected_ticker = df_steady.iloc[selected_row_idx]['代碼']

        st.write("")
        st.markdown(f"#### 🚀 高動能波段型（日線階梯敏捷停利 ＋ 破20MA出清保本） ({len(df_momentum)} 檔)")
        if df_momentum.empty:
            st.info("目前無符合篩選條件的高動能型標的。")
        else:
            ev_momentum = st.dataframe(
                style_dataframe(df_momentum), 
                use_container_width=True,
                on_select="rerun",          
                selection_mode="single-row",
                key="table_momentum",
                column_config={"Yahoo股市": st.column_config.LinkColumn("🔗 Yahoo股市", display_text="點擊前往")}
            )
            if ev_momentum.selection.rows:
                selected_row_idx = ev_momentum.selection.rows[0]
                st.session_state.selected_ticker = df_momentum.iloc[selected_row_idx]['代碼']

    # --- 互動 K 線圖區塊 ---
    st.divider()
    
    col_title, col_toggle = st.columns([3, 2])
    with col_toggle:
        chart_timeframe = st.radio(
            "📊 線圖顯示週期 (僅切換下方K線圖)：", 
            ["日線圖 (Daily)", "週線圖 (Weekly)"], 
            index=0,
            horizontal=True
        )
    with col_title:
        timeframe_display = "週線圖 (Weekly)" if chart_timeframe == "週線圖 (Weekly)" else "日線圖 (Daily)"
        st.subheader(f"📉 價量與指標複合分析圖 ({timeframe_display})")

    tf_interval = "1wk" if chart_timeframe == "週線圖 (Weekly)" else "1d"
    tf_period = "2y" if chart_timeframe == "週線圖 (Weekly)" else "1y"
    ma_s_lbl = "5W" if chart_timeframe == "週線圖 (Weekly)" else "5D"
    ma_l_lbl = "10W" if chart_timeframe == "週線圖 (Weekly)" else "10D"

    chart_options_dict = ACTIVE_WATCHLIST.copy()
    if temp_ticker and temp_ticker not in chart_options_dict:
        disp_name = temp_name if temp_name else temp_ticker
        chart_options_dict[temp_ticker] = disp_name

    options = [f"{k} - {v}" for k, v in chart_options_dict.items()]
    
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
                fig = make_subplots(rows=4, cols=1, shared_xaxes=True, 
                                    vertical_spacing=0.03, row_heights=[0.4, 0.2, 0.2, 0.2])

                fig.add_trace(go.Candlestick(x=chart_df.index, open=chart_df['Open'], high=chart_df['High'],
                                             low=chart_df['Low'], close=chart_df['Close'], 
                                             name='K線', increasing_line_color='#ef5350', decreasing_line_color='#26a69a'), row=1, col=1)
                
                fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['MA5'], line=dict(color='orange', width=1.5), name=f'{ma_s_lbl} MA'), row=1, col=1)
                fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['MA10'], line=dict(color='blue', width=1.5), name=f'{ma_l_lbl} MA'), row=1, col=1)
                fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['MA20'], line=dict(color='gray', dash='dot', width=1.5), name='20MA (月線)'), row=1, col=1)
                
                fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['UCL'], line=dict(color='rgba(150, 150, 150, 0.3)', width=1, dash='dash'), name='UCL (上軌)'), row=1, col=1)
                fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['LCL'], line=dict(color='rgba(150, 150, 150, 0.3)', width=1, dash='dash'), fill='tonexty', fillcolor='rgba(150, 150, 150, 0.1)', name='LCL (下軌)'), row=1, col=1)

                lookback = 60 if tf_interval == "1d" else 26
                if len(chart_df) >= lookback:
                    recent_high = chart_df['High'].tail(lookback).max()
                    recent_low = chart_df['Low'].tail(lookback).min()
                    
                    fig.add_hline(y=recent_high, line_dash="dash", line_color="rgba(239, 83, 80, 0.6)", line_width=1.5,
                                  annotation_text=f"近期壓力 {recent_high:.2f}", annotation_position="top right", 
                                  annotation_font=dict(color="#ef5350", size=12), row=1, col=1)
                    
                    fig.add_hline(y=recent_low, line_dash="dash", line_color="rgba(38, 166, 154, 0.6)", line_width=1.5,
                                  annotation_text=f"近期支撐 {recent_low:.2f}", annotation_position="bottom right", 
                                  annotation_font=dict(color="#26a69a", size=12), row=1, col=1)

                fig.add_trace(go.Bar(x=chart_df.index, y=chart_df['Volume'], marker_color=chart_df['Vol_Color'], name='成交量'), row=2, col=1)
                fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['Vol_MA5'], line=dict(color='orange', width=1), name='5均量'), row=2, col=1)

                fig.add_trace(go.Bar(x=chart_df.index, y=chart_df['MACD_Hist'], marker_color=chart_df['MACD_Color'], name='MACD柱'), row=3, col=1)
                fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['DIF'], line=dict(color='orange', width=1.5), name='DIF'), row=3, col=1)
                fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['DEA'], line=dict(color='blue', width=1.5), name='DEA(MACD)'), row=3, col=1)

                fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['RSI'], line=dict(color='#8e24aa', width=1.5), name='RSI(14)'), row=4, col=1)
                fig.add_hline(y=70, line_dash="dash", line_color="rgba(239, 83, 80, 0.5)", line_width=1, row=4, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="rgba(38, 166, 154, 0.5)", line_width=1, row=4, col=1)

                chart_dates = chart_df.index.strftime('%Y-%m-%d').tolist()
                dt_all = pd.date_range(start=chart_df.index[0], end=chart_df.index[-1])
                dt_breaks = [d.strftime('%Y-%m-%d') for d in dt_all if d.strftime('%Y-%m-%d') not in chart_dates]
                
                end_date_c = chart_df.index[-1]
                start_date_c = end_date_c - pd.DateOffset(years=1) if tf_interval == "1wk" else end_date_c - pd.DateOffset(months=3)

                fig.update_xaxes(
                    range=[start_date_c, end_date_c],
                    rangebreaks=[dict(values=dt_breaks)],
                    rangeselector=dict(
                        buttons=list([
                            dict(count=1, label="1M", step="month", stepmode="backward"),
                            dict(count=3, label="3M", step="month", stepmode="backward"),
                            dict(count=6, label="6M", step="month", stepmode="backward"),
                            dict(count=1, label="1Y", step="year", stepmode="backward"),
                            dict(count=3, label="3Y", step="year", stepmode="backward"),
                            dict(label="全部", step="all")
                        ]),
                        bgcolor="#f0f0f0",
                        activecolor="#cccccc",
                        font=dict(color="#007AFF"),
                        yanchor="top",  
                        y=1.0,          
                        xanchor="left",
                        x=0.01
                    )
                )

                fig.update_layout(
                    height=850, 
                    margin=dict(l=10, r=10, t=40, b=120), 
                    xaxis_rangeslider_visible=False,
                    legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5), 
                    hovermode="x unified"
                )
                fig.update_yaxes(range=[0, 100], row=4, col=1)
                
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            else:
                st.warning("⚠️ 無法取得該標的的 K 線圖資料，請確認代碼是否正確。")

# ==========================================
# 分頁 2：策略判斷原則
# ==========================================
with tab_rules:
    st.header("📖 雙指標波段系統 - 策略判斷原則與決策流程邏輯")
    st.markdown("""
    本系統採用**「長線保護短線」**的全方位跨週期綜合評估。**每檔股票只產出一個綜合最佳決策解**，線圖週期切換僅影響圖表顯示，不干擾決策信號。
    
    ---
    
    ### 🧭 戰情室決策流程邏輯層次（由上而下執行原則）
    
    #### 1️⃣ 第一梯隊：極限轉折與左側防護區（最高優先攔截）
    * **🔥 雙重底背離：`🟢 雙重底背離 (爆發起漲點)`**
        * **觸發條件**：價格創波段新低，但 **MACD(DIF) 與 RSI 同步低點抬高**。
        * **實戰動作**：空方推殺力竭，主力洗盤誘空，爆發強彈機率極高，啟動加碼佈局。
    * **🎯 破底加碼雷達：`🟢 破底分批加碼` (方案 A 嚴格確認型)**
        * **觸發條件**：跌破近 1 年低點或極限低檔（≤ 10%），且收盤價站上日 5MA，同時日 MACD 或 5MA 金叉。
    * **👀 破底打底觀察：`🟡 破底打底觀察`**
        * **觸發條件**：已實質破底或位階極低，但日線 MA/MACD 尚未金叉轉強，嚴禁盲目提早接刀。

    #### 2️⃣ 第二梯隊：資產配置核心（免出場長期持有）
    * **🏛️ 核心資產：`🔵 長期持有`**（SGOV、0050、VOO、QQQM 等）。

    #### 3️⃣ 第三梯隊：右側常規多頭波段（標準進場兩步曲）
    * **第一步（找獵物）：`💡 醞釀向上`**（週線大底即將完成；需連續 2 天站穩 20MA）。
    * **第二步（扣板機）：`🟢 走勢向上`**（長短線共振翻多連續站穩均線且放量）。

    #### 4️⃣ 第四梯隊：高動能階梯式敏捷停利與防守管控 (持倉狀態機)
    * **第一道敏捷防線：`🟠 敏捷減碼 50% (跌破10MA)`**：收盤跌破日 10MA 或日 MACD 翻綠，立即收割 50% 獲利落袋為安。
    * **第二道終極防線：`🔴 趨勢破位 (出清保本)`**：實質跌破日 20MA 月線，多頭結構瓦解，**剩餘部位一次出清，絕不拖延！**
    * **空手保護：`⚪ 空手觀望 (破線無持股)`**：出清後股價仍在月線下，**手上無部位，冷靜觀望，不再天天重複恐嚇出清！**
    * **防假突破過濾：`🟡 突破月線觀察 (待站穩第2日)`**：單日長紅突破月線不追高，待第 2 日確認站穩才准買進。
    * **低檔超賣保護網：`🟡 負乖離超賣 (暫緩追殺等待反彈)`**：股價跌破布林下軌（LCL）或 RSI ≤ 32，全面壓制賣出信號，嚴禁殺在阿呆谷。
    """)

# ==========================================
# 分頁 3：自選股與 LINE 即時通知設定 (含定時早晚報)
# ==========================================
with tab_settings:
    st.subheader("⚙️ 編輯自選股清單（支援 3 組股票組合）")
    st.markdown("請依照 `代碼,名稱` 的格式輸入，每行一檔標的。修改後會自動儲存並同步套用。")
    
    edit_tab1, edit_tab2, edit_tab3 = st.tabs(["📁 自選股 1 (標準預設)", "📁 自選股 2", "📁 自選股 3"])
    
    with edit_tab1:
        u_input1 = st.text_area("📝 編輯自選股 1 清單：", st.session_state.watchlist_1_text, height=300, key="text_edit_1")
        if u_input1 != st.session_state.watchlist_1_text:
            st.session_state.watchlist_1_text = u_input1
            save_settings()
            
    with edit_tab2:
        u_input2 = st.text_area("📝 編輯自選股 2 清單：", st.session_state.watchlist_2_text, height=300, key="text_edit_2")
        if u_input2 != st.session_state.watchlist_2_text:
            st.session_state.watchlist_2_text = u_input2
            save_settings()
            
    with edit_tab3:
        u_input3 = st.text_area("📝 編輯自選股 3 清單：", st.session_state.watchlist_3_text, height=300, key="text_edit_3")
        if u_input3 != st.session_state.watchlist_3_text:
            st.session_state.watchlist_3_text = u_input3
            save_settings()

    st.divider()
    st.subheader("🔔 LINE 即時通知與定時早晚報設定")
    st.markdown("支援 **盤中即時訊號攔截**（🔥雙重底背離、破底加碼、MACD金叉、破位出清）與 **定時早晚報**（08:45 盤前焦點、13:45 盤後覆盤）。")

    col_l1, col_l2 = st.columns([1, 1])
    with col_l1:
        st.checkbox("啟用【盤中關鍵訊號即時推播】(雙背離 / 破底加碼 / MACD金叉 / 破位出清)", value=st.session_state.enable_line_notify_input, key="enable_line_notify_input", on_change=update_other_inputs)
        st.checkbox("啟用【每日定時早晚報推播】(08:45早報 / 13:45晚報)", value=st.session_state.enable_daily_reports_input, key="enable_daily_reports_input", on_change=update_other_inputs)
        line_token = st.text_input("Channel Access Token (Long-lived)：", type="password", value=st.session_state.line_token_input, key="line_token_input", on_change=update_other_inputs)
        line_user_id = st.text_input("Your User ID (以 U 開頭的英數字)：", value=st.session_state.line_user_id_input, key="line_user_id_input", on_change=update_other_inputs)
    
    with col_l2:
        st.markdown("#### 🧪 手動測試推播功能")
        c_btn1, c_btn2, c_btn3 = st.columns(3)
        with c_btn1:
            if st.button("連線測試"):
                if not line_token or not line_user_id:
                    st.error("請先填入 Token 與 User ID！")
                else:
                    test_msg = f"🔔【雙指標系統】連線測試成功！當前時間：{get_tw_now().strftime('%Y-%m-%d %H:%M:%S')}。"
                    ok, res_text = send_line_message(line_token, line_user_id, test_msg)
                    if ok: st.success("✅ 連線測試成功！")
                    else: st.error(f"❌ 失敗：{res_text}")
        with c_btn2:
            if st.button("發送盤前早報"):
                if not line_token or not line_user_id:
                    st.error("請先填入 Token 與 User ID！")
                else:
                    m_msg = build_morning_report(display_df, market_trend_global, st.session_state.current_group_choice)
                    ok, res_text = send_line_message(line_token, line_user_id, m_msg)
                    if ok: st.success("✅ 早報推播成功！")
                    else: st.error(f"❌ 失敗：{res_text}")
        with c_btn3:
            if st.button("發送盤後晚報"):
                if not line_token or not line_user_id:
                    st.error("請先填入 Token 與 User ID！")
                else:
                    e_msg = build_evening_report(display_df, st.session_state.current_group_choice)
                    ok, res_text = send_line_message(line_token, line_user_id, e_msg)
                    if ok: st.success("✅ 晚報推播成功！")
                    else: st.error(f"❌ 失敗：{res_text}")

# ==========================================
# 分頁 4：買賣戰情室 (含各區塊右上角匯出報表)
# ==========================================
with tab_war_room:
    st.subheader(f"⚔️ 買賣戰情室【{st.session_state.current_group_choice}】 (長短線雙週期綜合唯一解)")
    
    if display_df.empty:
        st.warning(f"⚠️【{st.session_state.current_group_choice}】目前為空，請從『⚙️ 自選股編輯』分頁加入股票。")
    else:
        df_dual_bull = display_df[display_df['建議'].str.contains("雙重底背離", na=False)].reset_index(drop=True)
        df_dip_buy = display_df[display_df['建議'].str.contains("破底分批加碼", na=False)].reset_index(drop=True)
        df_trend_up = display_df[display_df['建議'].str.contains("走勢向上", na=False)].reset_index(drop=True)
        df_up = display_df[display_df['建議'].str.contains("醞釀向上", na=False)].reset_index(drop=True)
        
        df_trim_10ma = display_df[display_df['建議'].str.contains("敏捷減碼", na=False)].reset_index(drop=True)
        df_exit_20ma = display_df[display_df['建議'].str.contains("趨勢破位", na=False)].reset_index(drop=True)
        df_watch_empty = display_df[display_df['建議'].str.contains("空手觀望|突破月線觀察", na=False)].reset_index(drop=True)
        df_defense = display_df[display_df['建議'].str.contains("負乖離超賣", na=False)].reset_index(drop=True)
        
        df_hold_core = display_df[display_df['建議'].str.contains("長期持有", na=False)].reset_index(drop=True)
        df_bottom = display_df[display_df['建議'].str.contains("歷史低檔打底", na=False)].reset_index(drop=True)
        
        today_str = get_tw_now().strftime('%Y%m%d')
        grp_name_clean = st.session_state.current_group_choice.replace(" ", "")

        def render_section_with_export(title_text, df_sec, key_prefix):
            col_t, col_b = st.columns([4, 1])
            with col_t:
                st.markdown(f"#### {title_text}")
            with col_b:
                if not df_sec.empty:
                    csv_bytes = df_sec.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="📥 匯出當日報表",
                        data=csv_bytes,
                        file_name=f"戰情室_{key_prefix}_{grp_name_clean}_{today_str}.csv",
                        mime="text/csv",
                        key=f"btn_exp_{key_prefix}"
                    )

        # 🔥 雙重底背離
        if not df_dual_bull.empty:
            render_section_with_export(f"🔥 雙重底背離共振（大轉折起漲）：🟢 雙重底背離 ({len(df_dual_bull)})", df_dual_bull, "雙重底背離")
            ev_db = st.dataframe(
                style_dataframe(df_dual_bull.drop(columns=['股性類別'])), use_container_width=True,
                on_select="rerun", selection_mode="single-row", key="war_db",
                column_config={"Yahoo股市": st.column_config.LinkColumn("🔗 Yahoo股市", display_text="點擊前往")}
            )
            if ev_db.selection.rows:
                st.session_state.selected_ticker = df_dual_bull.iloc[ev_db.selection.rows[0]]['代碼']
            st.divider()

        # 破底分批加碼
        if not df_dip_buy.empty:
            render_section_with_export(f"🎯 破底加碼雷達（已確認翻多）：🟢 破底分批加碼 ({len(df_dip_buy)})", df_dip_buy, "破底加碼")
            ev_dip = st.dataframe(
                style_dataframe(df_dip_buy.drop(columns=['股性類別'])), use_container_width=True,
                on_select="rerun", selection_mode="single-row", key="war_dip",
                column_config={"Yahoo股市": st.column_config.LinkColumn("🔗 Yahoo股市", display_text="點擊前往")}
            )
            if ev_dip.selection.rows:
                st.session_state.selected_ticker = df_dip_buy.iloc[ev_dip.selection.rows[0]]['代碼']
            st.divider()

        # 走勢向上
        render_section_with_export(f"第一步（右側攻擊）：🟢 只看走勢向上 ({len(df_trend_up)})", df_trend_up, "走勢向上")
        if df_trend_up.empty:
            st.info("目前無『走勢向上』標的。")
        else:
            ev_buy = st.dataframe(
                style_dataframe(df_trend_up.drop(columns=['股性類別'])), use_container_width=True, 
                on_select="rerun", selection_mode="single-row", key="war_buy",
                column_config={"Yahoo股市": st.column_config.LinkColumn("🔗 Yahoo股市", display_text="點擊前往")}
            )
            if ev_buy.selection.rows:
                st.session_state.selected_ticker = df_trend_up.iloc[ev_buy.selection.rows[0]]['代碼']

        # 醞釀向上
        render_section_with_export(f"第二步（找獵物）：💡 醞釀向上 ({len(df_up)})", df_up, "醞釀向上")
        if df_up.empty:
            st.info("目前無『醞釀向上』標的。")
        else:
            ev_up = st.dataframe(
                style_dataframe(df_up.drop(columns=['股性類別'])), use_container_width=True, 
                on_select="rerun", selection_mode="single-row", key="war_up",
                column_config={"Yahoo股市": st.column_config.LinkColumn("🔗 Yahoo股市", display_text="點擊前往")}
            )
            if ev_up.selection.rows:
                st.session_state.selected_ticker = df_up.iloc[ev_up.selection.rows[0]]['代碼']
                
        st.divider()

        # 🟠 敏捷減碼 (跌破 10MA)
        if not df_trim_10ma.empty:
            render_section_with_export(f"🟠 第一道敏捷防線（破10MA減碼50%）：🟠 敏捷減碼 ({len(df_trim_10ma)})", df_trim_10ma, "敏捷減碼")
            ev_trim = st.dataframe(
                style_dataframe(df_trim_10ma.drop(columns=['股性類別'])), use_container_width=True,
                on_select="rerun", selection_mode="single-row", key="war_trim",
                column_config={"Yahoo股市": st.column_config.LinkColumn("🔗 Yahoo股市", display_text="點擊前往")}
            )
            if ev_trim.selection.rows:
                st.session_state.selected_ticker = df_trim_10ma.iloc[ev_trim.selection.rows[0]]['代碼']

        # 🔴 趨勢破位 (跌破 20MA 出清)
        if not df_exit_20ma.empty:
            render_section_with_export(f"🔴 第二道終極防線（破月線出清保本）：🔴 趨勢破位 ({len(df_exit_20ma)})", df_exit_20ma, "趨勢破位")
            ev_exit = st.dataframe(
                style_dataframe(df_exit_20ma.drop(columns=['股性類別'])), use_container_width=True,
                on_select="rerun", selection_mode="single-row", key="war_exit",
                column_config={"Yahoo股市": st.column_config.LinkColumn("🔗 Yahoo股市", display_text="點擊前往")}
            )
            if ev_exit.selection.rows:
                st.session_state.selected_ticker = df_exit_20ma.iloc[ev_exit.selection.rows[0]]['代碼']

        # ⚪ 空手觀望
        if not df_watch_empty.empty:
            render_section_with_export(f"⚪ 空手冷靜區（無部位不接刀 / 待站穩）：⚪ 空手觀望 ({len(df_watch_empty)})", df_watch_empty, "空手觀望")
            ev_we = st.dataframe(
                style_dataframe(df_watch_empty.drop(columns=['股性類別'])), use_container_width=True,
                on_select="rerun", selection_mode="single-row", key="war_we",
                column_config={"Yahoo股市": st.column_config.LinkColumn("🔗 Yahoo股市", display_text="點擊前往")}
            )
            if ev_we.selection.rows:
                st.session_state.selected_ticker = df_watch_empty.iloc[ev_we.selection.rows[0]]['代碼']

        # 🟡 低檔超賣禁止追殺
        if not df_defense.empty:
            render_section_with_export(f"🛡️ 低檔超賣保護網（禁止殺跌等待反彈）：🟡 負乖離超賣 ({len(df_defense)})", df_defense, "負乖離超賣")
            ev_hold = st.dataframe(
                style_dataframe(df_defense.drop(columns=['股性類別'])), use_container_width=True, 
                on_select="rerun", selection_mode="single-row", key="war_hold",
                column_config={"Yahoo股市": st.column_config.LinkColumn("🔗 Yahoo股市", display_text="點擊前往")}
            )
            if ev_hold.selection.rows:
                st.session_state.selected_ticker = df_defense.iloc[ev_hold.selection.rows[0]]['代碼']

# ==========================================
# 分頁 5：🔬 深度分析 (含明日 5MA 翻揚扣抵試算與右上角匯出)
# ==========================================
with tab_deep_dive:
    st.subheader("🔬 個股走勢深度分析")
    st.markdown("從當前自選股中挑選標的，並設定時間區間（預設往前回溯 2 個星期）。系統將逐日回溯該標的狀態，並依日期由新到舊排列呈現。")

    col_stock, col_start, col_end = st.columns([2, 2, 2])
    
    deep_options_dict = ACTIVE_WATCHLIST.copy()
    if temp_ticker and temp_ticker not in deep_options_dict:
        disp_name = temp_name if temp_name else temp_ticker
        deep_options_dict[temp_ticker] = disp_name
    
    deep_options = [f"{k} - {v}" for k, v in deep_options_dict.items()]

    with col_stock:
        default_deep_idx = 0
        if st.session_state.selected_ticker:
            for i, opt in enumerate(deep_options):
                if opt.startswith(st.session_state.selected_ticker):
                    default_deep_idx = i
                    break
        selected_deep_opt = st.selectbox("📌 選擇要分析的標的：", deep_options, index=default_deep_idx, key="deep_stock_select")
        target_ticker = selected_deep_opt.split(" - ")[0] if selected_deep_opt else None
        target_name = deep_options_dict.get(target_ticker, target_ticker)

    now_tw_date = get_tw_now().date()
    two_weeks_ago = now_tw_date - timedelta(days=14)

    with col_start:
        start_date = st.date_input("📅 起始時間 (預設往前 2 週)：", value=two_weeks_ago, key="deep_start_date")
    with col_end:
        end_date = st.date_input("📅 結束時間：", value=now_tw_date, key="deep_end_date")

    if start_date > end_date:
        st.error("⚠️ 起始時間必須早於或等於結束時間，請重新選擇日期區間。")
    elif target_ticker:
        with st.spinner(f"正在逐日回溯 {target_ticker} ({target_name}) 狀態明細與扣抵試算..."):
            hist_signals_df, ma5_info = generate_historical_signals_table(target_ticker, target_name, start_date, end_date)

        if hist_signals_df.empty:
            st.warning("⚠️ 所選時間區間內未包含任何開盤交易日或資料不足，請調整日期範圍。")
        else:
            if ma5_info:
                st.markdown("---")
                st.markdown(f"#### 🧭 明日 5MA 均線翻揚與站穩扣抵試算 ({target_ticker})")
                mc1, mc2, mc3 = st.columns(3)
                
                mc1.metric(
                    label="📌 明日 5MA 扣抵值 (5日前價格)",
                    value=f"{ma5_info['deduction_price']:.2f} 元",
                    help="明日將剔除的價格。明日收盤價大於此價位，5MA 即會向上翻揚。"
                )
                mc2.metric(
                    label="📈 5MA 翻揚需收 (目標價)",
                    value=f"{ma5_info['turn_up_price']:.2f} 元",
                    delta=f"{ma5_info['turn_up_diff_pct']:+.2f}% 距現價",
                    delta_color="inverse" if ma5_info['turn_up_diff_pct'] > 0 else "normal",
                    help="明日收盤需高於此價位，5MA 均線斜率才會由負轉正。"
                )
                mc3.metric(
                    label="🛡️ 實質站上 5MA 需收 (目標價)",
                    value=f"{ma5_info['stand_on_ma5_price']:.2f} 元",
                    delta=f"{ma5_info['stand_diff_pct']:+.2f}% 距現價",
                    delta_color="inverse" if ma5_info['stand_diff_pct'] > 0 else "normal",
                    help="明日收盤需高於此價位，收盤價才會正式高於明日 5MA。"
                )
                st.markdown("---")

            col_dh_title, col_dh_btn = st.columns([4, 1])
            with col_dh_title:
                st.markdown(f"#### 📋 {target_ticker} - {target_name} 逐日狀態明細表（{start_date.strftime('%Y/%m/%d')} ~ {end_date.strftime('%Y/%m/%d')}，共 {len(hist_signals_df)} 個交易日）")
            with col_dh_btn:
                deep_csv_bytes = hist_signals_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 匯出當日報表",
                    data=deep_csv_bytes,
                    file_name=f"深度分析_{target_ticker}_{target_name}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    key="btn_exp_deep_table"
                )

            st.dataframe(
                style_dataframe(hist_signals_df),
                use_container_width=True,
                hide_index=True
            )

            summary_card = generate_summary_insight(hist_signals_df, target_ticker, target_name, ma5_info)
            st.markdown(summary_card, unsafe_allow_html=True)

# --- 版權宣告與免責聲明 ---
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: #888888; font-size: 14px; padding: 10px;'>
        本系統由 Robert 開發，僅供技術分析研究，非投資買賣建議
    </div>
    """, 
    unsafe_allow_html=True
)
