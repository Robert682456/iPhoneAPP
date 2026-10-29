import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh
import json
import os
import math
from datetime import datetime, timedelta

st.set_page_config(page_title="雙指標波段系統", page_icon="📈", layout="wide")

# 自動重整機制：每 5 分鐘 (300,000 毫秒) 自動重新載入網頁
st_autorefresh(interval=5 * 60 * 1000, key="auto_refresh")

# ==========================================
# 本機設定檔存取邏輯 (支援 3 組自選股)
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "user_settings.json")

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
        "watchlist_3": DEFAULT_LIST_3
    }

def save_settings():
    settings = {
        "search_ticker": st.session_state.search_ticker,
        "search_name": st.session_state.search_name,
        "market_ticker": st.session_state.get("market_ticker_input", "0050.TW"),
        "current_group": st.session_state.get("current_group_choice", "自選股 1"),
        "watchlist_1": st.session_state.get("watchlist_1_text", DEFAULT_LIST_1),
        "watchlist_2": st.session_state.get("watchlist_2_text", DEFAULT_LIST_2),
        "watchlist_3": st.session_state.get("watchlist_3_text", DEFAULT_LIST_3)
    }
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False)
    except Exception:
        pass

# 初始化 Session State
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

# 計算台股最小升降單位 (Tick)
def get_tick_size(price):
    if price < 10: return 0.01
    elif price < 50: return 0.05
    elif price < 100: return 0.1
    elif price < 500: return 0.5
    elif price < 1000: return 1.0
    else: return 5.0

# 向上取整至最小跳動檔位
def round_up_tick(val):
    tick = get_tick_size(val)
    return math.ceil(val / tick) * tick

# --- 隱藏 Streamlit 預設選單與浮水印 ---
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

tab_dashboard, tab_rules, tab_settings, tab_war_room, tab_deep_dive = st.tabs([
    "📊 看盤儀表板", "📖 策略判斷原則", "⚙️ 自選股編輯", "⚔️ 買賣戰情室", "🔬 深度分析"
])
display_df = pd.DataFrame()

# ==========================================
# 分頁 3：自選股編輯頁面
# ==========================================
with tab_settings:
    st.subheader("⚙️ 編輯自選股清單（支援 3 組股票組合）")
    st.markdown("請依照 `代碼,名稱` 的格式輸入，每行一檔標的。修改後會自動儲存並同步套用。")
    
    edit_tab1, edit_tab2, edit_tab3 = st.tabs(["📁 自選股 1 (標準預設)", "📁 自選股 2", "📁 自選股 3"])
    
    with edit_tab1:
        u_input1 = st.text_area("📝 編輯自選股 1 清單：", st.session_state.watchlist_1_text, height=450, key="text_edit_1")
        if u_input1 != st.session_state.watchlist_1_text:
            st.session_state.watchlist_1_text = u_input1
            save_settings()
            
    with edit_tab2:
        u_input2 = st.text_area("📝 編輯自選股 2 清單：", st.session_state.watchlist_2_text, height=450, key="text_edit_2")
        if u_input2 != st.session_state.watchlist_2_text:
            st.session_state.watchlist_2_text = u_input2
            save_settings()
            
    with edit_tab3:
        u_input3 = st.text_area("📝 編輯自選股 3 清單：", st.session_state.watchlist_3_text, height=450, key="text_edit_3")
        if u_input3 != st.session_state.watchlist_3_text:
            st.session_state.watchlist_3_text = u_input3
            save_settings()

if st.session_state.current_group_choice == "自選股 2":
    ACTIVE_WATCHLIST = parse_watchlist(st.session_state.watchlist_2_text)
elif st.session_state.current_group_choice == "自選股 3":
    ACTIVE_WATCHLIST = parse_watchlist(st.session_state.watchlist_3_text)
else:
    ACTIVE_WATCHLIST = parse_watchlist(st.session_state.watchlist_1_text)

# ==========================================
# 分頁 2：策略判斷原則
# ==========================================
with tab_rules:
    st.header("📖 雙指標波段系統 - 策略判斷原則與決策流程邏輯")
    
    st.markdown("""
    本系統採用**「長線保護短線」**的全方位跨週期綜合評估。**每檔股票只產出一個綜合最佳決策解**，線圖週期切換僅影響圖表顯示，不干擾決策信號。
    
    ---
    
    ### 🧭 戰情室決策流程邏輯層次（由上而下執行原則）
    
    #### 1️⃣ 第一梯隊：左側極限防護區（最高優先攔截）
    * **🎯 破底加碼雷達：`🟢 破底分批加碼` (方案 A 嚴格確認型)**
        * **觸發條件**：股價跌破近 1 年低點或處於年度極限低檔（≤ 10%），且**收盤價實質站上日 5MA**，同時**日 MACD 金叉 (柱狀 > 0) 或 5MA 金叉 10MA**。
        * **實戰動作**：確認空方動能耗盡且短線翻多，啟動左側金字塔分批攤平布局，**全面壓制任何賣出訊號**。
    * **👀 破底打底觀察：`🟡 破底打底觀察`**
        * **觸發條件**：已實質破底或位階極低，但日線 MA/MACD 尚未金叉轉強。
        * **實戰動作**：**嚴禁盲目提早進場接刀**，耐心等待日線指標正式翻多，保留現金銀彈。

    #### 2️⃣ 第二梯隊：資產配置核心（免出場長期持有）
    * **🏛️ 核心資產：`🔵 長期持有`**
        * **納入名單**：超短天期美債（SGOV、BIL 等）與大盤核心原型 ETF（0050、VOO、QQQM 等）。
        * **實戰動作**：隨經濟長期成長滾動複利或穩定領息，**完全免疫短期技術出場信號**。

    #### 3️⃣ 第三梯隊：右側常規多頭波段（標準進場兩步曲）
    * **第一步（找獵物）：`💡 醞釀向上`**
        * **優先準則**：以**「週線大底即將完成」**為核心。若週線 MACD 死叉，日線需連續 2 天站穩 20MA。
    * **第二步（扣板機）：`🟢 走勢向上`**
        * **觸發條件**：週線維持長多，日線雙指標翻多帶量突破。

    #### 4️⃣ 第四梯隊：轉折防守與紀律出場管控
    * **`🛡️ 歷史低檔打底`** $\rightarrow$ **`🟠 分批停利`** $\rightarrow$ **`⚠️ 醞釀向下`** $\rightarrow$ **`🟠 建議減碼50%`** $\rightarrow$ **`🔴 只看賣出`** $\rightarrow$ **`🟡 避免殺低`**。
    """)

# ==========================================
# 核心函數定義區
# ==========================================
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
                if "SGOV" in ticker or "BIL" in ticker or "SHV" in ticker or "債" in name:
                    stock_profile = "💰 核心·收息存債"
                else:
                    stock_profile = "🏛️ 核心·指數複利"
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
            
            curr_ma5_d, curr_ma10_d = ma5_d.iloc[-1], ma10_d.iloc[-1]
            curr_hist_d, prev_hist_d = hist_d.iloc[-1], hist_d.iloc[-2]
            curr_vol_d, curr_vol_ma5_d = volume_d.iloc[-1], vol_ma5_d.iloc[-1]

            is_daily_golden_cross = (curr_hist_d > 0) or (curr_ma5_d > curr_ma10_d)
            is_above_ma5 = (curr_close > curr_ma5_d)
            is_daily_stopping_drop = is_above_ma5 and is_daily_golden_cross

            is_standing_on_ma20_2days = (curr_close > ma20_d.iloc[-1]) and (prev_close > ma20_d.iloc[-2])

            if len(close_w) >= 35:
                ma5_w, ma10_w = close_w.rolling(5).mean(), close_w.rolling(10).mean()
                ema12_w, ema26_w = close_w.ewm(span=12, adjust=False).mean(), close_w.ewm(span=26, adjust=False).mean()
                dif_w = ema12_w - ema26_w
                hist_w = dif_w - dif_w.ewm(span=9, adjust=False).mean()
                delta_w = close_w.diff()
                gw = delta_w.clip(lower=0).ewm(com=13, adjust=False).mean()
                lw = (-1 * delta_w.clip(upper=0)).ewm(com=13, adjust=False).mean()
                rsi_w = 100 - (100 / (1 + (gw / lw)))
                
                curr_dif_w, prev_dif_w = dif_w.iloc[-1], dif_w.iloc[-2]
                weekly_dif_decreasing = curr_dif_w < prev_dif_w
                weekly_ma_dead = (ma5_w.iloc[-1] < ma10_w.iloc[-1])
                weekly_macd_dead = (hist_w.iloc[-1] <= 0)
                is_weekly_bullish = (hist_w.iloc[-1] > 0 and ma5_w.iloc[-1] > ma10_w.iloc[-1])
                
                w_close = close_w.iloc[-1]
                w_ma5 = ma5_w.iloc[-1]
                w_hist, w_prev_hist = hist_w.iloc[-1], hist_w.iloc[-2]
            else:
                weekly_dif_decreasing = False
                weekly_ma_dead = False
                weekly_macd_dead = False
                is_weekly_bullish = True
                w_close, w_ma5, w_hist, w_prev_hist = curr_close, curr_ma5_d, curr_hist_d, prev_hist_d

            change_pct = ((curr_close - prev_close) / prev_close) * 100
            if change_pct > 0: price_display = f"🔺 {curr_close:.2f} (+{change_pct:.2f}%)"
            elif change_pct < 0: price_display = f"🔻 {curr_close:.2f} ({change_pct:.2f}%)"
            else: price_display = f"➖ {curr_close:.2f} (0.00%)"
            
            last_date_str = close_d.index[-1].strftime('%m/%d')
            actions = []
            if prev_close <= ma20_d.iloc[-2] and curr_close > ma20_d.iloc[-1]:
                actions.append(f"日線突破20MA ({last_date_str})")
            if prev_hist_d <= 0 and curr_hist_d > 0:
                actions.append(f"日MACD剛金叉 ({last_date_str})")
            elif prev_hist_d >= 0 and curr_hist_d < 0:
                actions.append(f"日MACD剛死叉 ({last_date_str})")

            target_pos_d = (50 if curr_hist_d > 0 else 0) + (50 if curr_ma5_d > curr_ma10_d else 0)
            vol_condition_d = curr_vol_d > curr_vol_ma5_d
            
            is_weekly_bottom_forming = (w_hist < 0 and w_hist > w_prev_hist) or (w_close > w_ma5 and w_hist < 0)
            
            if weekly_macd_dead:
                is_daily_launching = (curr_close > curr_ma5_d) and (curr_hist_d > prev_hist_d) and is_standing_on_ma20_2days
            else:
                is_daily_launching = (curr_close > curr_ma5_d) and (curr_hist_d > prev_hist_d)

            # ==========================================
            # 綜合唯一建議判定
            # ==========================================
            if is_buy_and_hold:
                rec_text = "🔵 長期持有 (核心被動)"
                if "債" in stock_profile:
                    detail_reason = "【免出場核心資產】純收息超短債，波動極低且穩定配息，免受技術指標干擾，建議長期續抱。"
                else:
                    detail_reason = "【免出場核心資產】大盤原型指數，隨經濟成長滾動長期複利，不執行技術面停損停利，建議定期定額或逢低續抱。"
            
            elif is_broke_1y_low:
                if is_daily_stopping_drop:
                    rec_text = "🟢 破底分批加碼"
                    detail_reason = f"【破底確認翻多】跌破近1年低點({low_1y_prev:.2f})後，日線已正式金叉(MACD或5MA翻多)且站上5MA，確認止跌轉強，啟動左側金字塔分批加碼！"
                else:
                    rec_text = "🟡 破底打底觀察"
                    detail_reason = f"【破底未止跌】跌破近1年低點({low_1y_prev:.2f})，但日線 MA/MACD 尚未金叉轉強，空方慣性未改，暫緩攤平、耐心等待翻多信號！"

            else:
                if target_pos_d == 100 and vol_condition_d:
                    if not is_weekly_bullish:
                        rec_text = "🟡 觀察"
                        detail_reason = "【短多長空】日線翻多帶量，但週線長線格局尚未同步，暫作觀察。"
                    else:
                        rec_text = "🟢 走勢向上"
                        detail_reason = "【長短線共振帶量】週線維持長多，日線雙指標翻多且成交量超越5日均量，確立波段走勢向上！"
                
                elif target_pos_d == 0:
                    if curr_rsi_d <= 30 or curr_close <= curr_lcl_d:
                        rec_text = "🟡 避免殺低"
                        detail_reason = f"【嚴重負乖離】日線跌破LCL或RSI極度超賣({curr_rsi_d:.1f})，切勿恐慌殺低，靜待技術反彈。"
                    else:
                        if is_high_momentum:
                            if is_weekly_bottom_forming:
                                if is_daily_launching:
                                    rec_text = "🌟 醞釀向上 (週大底+日發動)"
                                    detail_reason = "【週線大底＋日線連續2天站穩20MA】週MACD綠柱持續收斂打底，且日線已實質站穩月線2日確認發動，大波段起跑首選！"
                                else:
                                    rec_text = "💡 醞釀向上 (週大底打底)"
                                    detail_reason = "【週線大底沉澱】週MACD綠柱收斂或低檔超賣，大格局正築底中，適合左側分批布局。"
                            elif percentile_1y <= 25.0:
                                rec_text = "🟡 歷史低檔打底 (抱牢)"
                                detail_reason = f"【歷史相對低點保護】近1年位階僅 {percentile_1y:.1f}%(≤25%)，基期極低，技術死叉具滯後性，低接者抱牢勿殺低！"
                            elif weekly_macd_dead:
                                if change_pct >= 4.0:
                                    rec_text = "🟠 分批停利 (強彈中)"
                                    detail_reason = f"【低接強彈保護】週線雖死叉，但當日強漲 {change_pct:.2f}%，先獲利減碼 30%~50%，其餘看日 5MA 防守。"
                                else:
                                    rec_text = "🔴 賣出 (動能出清)"
                                    detail_reason = "【動能型終極出場】週MACD正式死叉確認波段結束，建議出清剩餘 50% 部位。"
                            elif weekly_ma_dead:
                                rec_text = "🟠 減碼 (週MA死叉)"
                                detail_reason = "【動能型第一防線】週 5W 跌破 10W，先行減碼 50% 鎖利，其餘等週MACD確認。"
                            else:
                                rec_text = "🟡 觀察 (抱牢主升)"
                                detail_reason = "【動能型抱牢】日線震盪洗盤，但週線 5W>10W 且 MACD>0，無懼短線震盪續抱。"
                        else:
                            if weekly_dif_decreasing:
                                rec_text = "🔴 賣出 (日線敏捷)"
                                detail_reason = "【穩健型防守】週線DIF下降且日線翻空，保護獲利果斷全出。"
                            else:
                                rec_text = "🟡 觀察"
                                detail_reason = "【防守延遲】日線翻空，但週線DIF仍上升，暫緩賣出。"
                else:
                    if weekly_dif_decreasing and curr_rsi_d >= 70:
                        rec_text = "⚠️ 醞釀向下"
                        detail_reason = f"【逼近超買】週線DIF下降且日RSI高達 ({curr_rsi_d:.1f})，極度貪婪提防見頂拉回。"
                    elif weekly_dif_decreasing and curr_hist_d > 0 and curr_hist_d < prev_hist_d and curr_close < curr_ma5_d:
                        rec_text = "⚠️ 醞釀向下"
                        detail_reason = "【動能衰退】日MACD紅柱縮減且週線DIF下降，多方推升無力防範頭部成型。"
                    elif is_weekly_bottom_forming:
                        if is_daily_launching:
                            rec_text = "🌟 醞釀向上 (週大底+日發動)"
                            detail_reason = "【週線大底＋日線連續2天站穩20MA】週MACD綠柱持續收斂打底，且日線已實質站穩月線2日確認發動，大波段起跑首選！"
                        else:
                            rec_text = "💡 醞釀向上 (週大底打底)"
                            detail_reason = "【週線大底沉澱】週MACD綠柱收斂或低檔超賣，大格局正築底中，適合左側分批布局。"
                    else:
                        rec_text = "🟡 觀察"
                        detail_reason = "【方向分歧】指標未完全同步，維持觀望。"

                if curr_close <= curr_lcl_d and curr_vol_d > curr_vol_ma5_d * 2 and curr_rsi_d < 30:
                    rec_text = "🟢 逢低買入"
                    detail_reason = f"【SPC極端超跌】跌破LCL、爆出2倍均量且RSI超賣({curr_rsi_d:.1f})，籌碼換手醞釀強彈！"

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
            if "破底分批加碼" in row['建議']: return 1
            elif "走勢向上" in row['建議']: return 2  
            elif "週大底+日發動" in row['建議']: return 3
            elif "週大底打底" in row['建議']: return 4
            elif "長期持有" in row['建議']: return 5
            elif "破底打底觀察" in row['建議']: return 6
            elif "歷史低檔打底" in row['建議']: return 7
            elif "停利" in row['建議']: return 8
            elif "醞釀向下" in row['建議']: return 9
            elif "減碼" in row['建議']: return 10
            elif "避免殺低" in row['建議']: return 11 
            elif "觀察" in row['建議']: return 12
            elif "賣出" in row['建議']: return 13
            else: return 14
        df_results['SortRank'] = df_results.apply(get_sort_rank, axis=1)
        df_results = df_results.sort_values(by=['SortRank', '代碼']).drop(columns=['SortRank']).reset_index(drop=True)
        
    return df_results

# ==========================================
# 歷史逐日狀態回溯引擎 (專供深度分析 - 含 5MA 翻揚價計算)
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

    daily_records = []
    trading_dates = [d for d in df_d.index if start_date <= d.date() <= end_date]
    trading_dates.sort(reverse=True)

    for dt in trading_dates:
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

        # 計算明日 5MA 翻揚價與扣抵值
        # 明日 5MA 計算會踢掉 loc-3 的價格 (即 4 天前收盤價)
        deduction_price = close.iloc[loc - 3] if loc >= 3 else c_close
        sum_prev4 = close.iloc[loc-3:loc+1].sum()  # 過去 4 天收盤價總和
        req_above_5ma = sum_prev4 / 4.0            # 站上 5MA 需大於之基準
        
        # 翻揚目標價取「大於扣抵值」與「大於 4 天均價」之較大者，並往上進位至最小 Tick
        target_reversal_val = max(deduction_price, req_above_5ma)
        tick_sz = get_tick_size(target_reversal_val)
        target_reversal_price = round_up_tick(target_reversal_val + 0.0001)

        if is_buy_and_hold:
            is_high_momentum = False
            if "SGOV" in ticker or "BIL" in ticker or "SHV" in ticker or "債" in name:
                stock_profile = "💰 核心·收息存債"
            else:
                stock_profile = "🏛️ 核心·指數複利"
        else:
            is_high_momentum = (atr_pct >= 3.5)
            stock_profile = f"🚀 動能({atr_pct:.1f}%)" if is_high_momentum else f"🏛️ 穩健({atr_pct:.1f}%)"

        lookback_len = min(250, loc)
        h_1y = high.iloc[loc - lookback_len:loc + 1].max()
        l_1y_prev = low.iloc[loc - lookback_len:loc].min() if lookback_len > 1 else low.iloc[loc]
        l_1y = min(l_1y_prev, c_low)
        percentile_1y = ((c_close - l_1y) / (h_1y - l_1y)) * 100 if h_1y > l_1y else 50.0

        is_broke_1y_low = (c_close <= l_1y_prev * 1.01) or (percentile_1y <= 10.0)

        is_daily_golden_cross = (c_hist > 0) or (c_ma5 > c_ma10)
        is_above_ma5 = (c_close > c_ma5)
        is_daily_stopping_drop = is_above_ma5 and is_daily_golden_cross

        is_standing_on_ma20_2days = (c_close > c_ma20) and (p_close > p_ma20)

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
        if p_close <= p_ma20 and c_close > c_ma20:
            actions.append(f"日線突破20MA ({date_short})")
        if p_hist <= 0 and c_hist > 0:
            actions.append(f"日MACD剛金叉 ({date_short})")
        elif p_hist >= 0 and c_hist < 0:
            actions.append(f"日MACD剛死叉 ({date_short})")

        target_pos_d = (50 if c_hist > 0 else 0) + (50 if c_ma5 > c_ma10 else 0)
        vol_condition_d = c_vol > c_vol_ma5
        
        if weekly_macd_dead:
            is_daily_launching = (c_close > c_ma5) and (c_hist > p_hist) and is_standing_on_ma20_2days
        else:
            is_daily_launching = (c_close > c_ma5) and (c_hist > p_hist)

        # 核心判定
        if is_buy_and_hold:
            rec_text = "🔵 長期持有 (核心被動)"
            if "債" in stock_profile:
                detail_reason = "【免出場核心資產】純收息超短債，波動極低且穩定配息，免受技術指標干擾，建議長期續抱。"
            else:
                detail_reason = "【免出場核心資產】大盤原型指數，隨經濟成長滾動長期複利，不執行技術面停損停利，建議定期定額或逢低續抱。"

        elif is_broke_1y_low:
            if is_daily_stopping_drop:
                rec_text = "🟢 破底分批加碼"
                detail_reason = f"【破底確認翻多】跌破近1年低點({l_1y_prev:.2f})後，日線已正式金叉(MACD或5MA翻多)且站上5MA，確認止跌轉強，啟動左側金字塔分批加碼！"
            else:
                rec_text = "🟡 破底打底觀察"
                detail_reason = f"【破底未止跌】跌破近1年低點({l_1y_prev:.2f})，但日線 MA/MACD 尚未金叉轉強，空方慣性未改，暫緩攤平、耐心等待翻多信號！"

        else:
            if target_pos_d == 100 and vol_condition_d:
                if not is_weekly_bullish:
                    rec_text = "🟡 觀察"
                    detail_reason = "【短多長空】日線翻多帶量，但週線長線格局尚未同步，暫作觀察。"
                else:
                    rec_text = "🟢 走勢向上"
                    detail_reason = "【長短線共振帶量】週線維持長多，日線雙指標翻多且成交量超越5日均量，確立波段走勢向上！"

            elif target_pos_d == 0:
                if c_rsi <= 30 or c_close <= c_lcl:
                    rec_text = "🟡 避免殺低"
                    detail_reason = f"【嚴重負乖離】日線跌破LCL或RSI極度超賣({c_rsi:.1f})，切勿恐慌殺低，靜待技術反彈。"
                else:
                    if is_high_momentum:
                        if is_weekly_bottom_forming:
                            if is_daily_launching:
                                rec_text = "🌟 醞釀向上 (週大底+日發動)"
                                detail_reason = "【週線大底＋日線連續2天站穩20MA】週MACD綠柱持續收斂打底，且日線已實質站穩月線2日確認發動，大波段起跑首選！"
                            else:
                                rec_text = "💡 醞釀向上 (週大底打底)"
                                detail_reason = "【週線大底沉澱】週MACD綠柱收斂或低檔超賣，大格局正築底中，適合左側分批布局。"
                        elif percentile_1y <= 25.0:
                            rec_text = "🟡 歷史低檔打底 (抱牢)"
                            detail_reason = f"【歷史相對低點保護】近1年位階僅 {percentile_1y:.1f}%(≤25%)，基期極低，技術死叉具滯後性，低接者抱牢勿殺低！"
                        elif weekly_macd_dead:
                            if change_pct >= 4.0:
                                rec_text = "🟠 分批停利 (強彈中)"
                                detail_reason = f"【低接強彈保護】週線雖死叉，但當日強漲 {change_pct:.2f}%，先獲利減碼 30%~50%，其餘看日 5MA 防守。"
                            else:
                                rec_text = "🔴 賣出 (動能出清)"
                                detail_reason = "【動能型終極出場】週MACD正式死叉確認波段結束，建議出清剩餘 50% 部位。"
                        elif weekly_ma_dead:
                            rec_text = "🟠 減碼 (週MA死叉)"
                            detail_reason = "【動能型第一防線】週 5W 跌破 10W，先行減碼 50% 鎖利，其餘等週MACD確認。"
                        else:
                            rec_text = "🟡 觀察 (抱牢主升)"
                            detail_reason = "【動能型抱牢】日線震盪洗盤，但週線 5W>10W 且 MACD>0，無懼短線震盪續抱。"
                    else:
                        if weekly_dif_decreasing:
                            rec_text = "🔴 賣出 (日線敏捷)"
                            detail_reason = "【穩健型防守】週線DIF下降且日線翻空，保護獲利果斷全出。"
                        else:
                            rec_text = "🟡 觀察"
                            detail_reason = "【防守延遲】日線翻空，但週線DIF仍上升，暫緩賣出。"
            else:
                if weekly_dif_decreasing and c_rsi >= 70:
                    rec_text = "⚠️ 醞釀向下"
                    detail_reason = f"【逼近超買】週線DIF下降且日RSI高達 ({c_rsi:.1f})，極度貪婪提防見頂拉回。"
                elif weekly_dif_decreasing and c_hist > 0 and c_hist < p_hist and c_close < c_ma5:
                    rec_text = "⚠️ 醞釀向下"
                    detail_reason = "【動能衰退】日MACD紅柱縮減且週線DIF下降，多方推升無力防範頭部成型。"
                elif is_weekly_bottom_forming:
                    if is_daily_launching:
                        rec_text = "🌟 醞釀向上 (週大底+日發動)"
                        detail_reason = "【週線大底＋日線連續2天站穩20MA】週MACD綠柱持續收斂打底，且日線已實質站穩月線2日確認發動，大波段起跑首選！"
                    else:
                        rec_text = "💡 醞釀向上 (週大底打底)"
                        detail_reason = "【週線大底沉澱】週MACD綠柱收斂或低檔超賣，大格局正築底中，適合左側分批布局。"
                else:
                    rec_text = "🟡 觀察"
                    detail_reason = "【方向分歧】指標未完全同步，維持觀望。"

            if c_close <= c_lcl and c_vol > c_vol_ma5 * 2 and c_rsi < 30:
                rec_text = "🟢 逢低買入"
                detail_reason = f"【SPC極端超跌】跌破LCL、爆出2倍均量且RSI超賣({c_rsi:.1f})，籌碼換手醞釀強彈！"

        daily_records.append({
            "日期": date_str,
            "代碼": ticker,
            "名稱": name,
            "收盤價(漲跌)": price_display,
            "明日扣抵價": f"{deduction_price:.2f}",
            "翻揚目標價": f"{target_reversal_price:.2f}",
            "股性模式": stock_profile,
            "建議": rec_text,
            "最新動態": " / ".join(actions) if actions else "-",
            "詳細判定原因": detail_reason
        })

    # 計算全期最新一日的「明日翻揚參數」供摘要卡片使用
    latest_loc = len(close) - 1
    latest_c = close.iloc[-1]
    latest_deduct = close.iloc[latest_loc - 3] if latest_loc >= 3 else latest_c
    latest_sum4 = close.iloc[latest_loc-3:latest_loc+1].sum()
    latest_target_val = max(latest_deduct, latest_sum4 / 4.0)
    latest_target_price = round_up_tick(latest_target_val + 0.0001)
    req_growth_pct = ((latest_target_price - latest_c) / latest_c) * 100

    next_day_forecast = {
        "current_close": latest_c,
        "deduction_price": latest_deduct,
        "target_price": latest_target_price,
        "growth_pct": req_growth_pct
    }

    return pd.DataFrame(daily_records), next_day_forecast

# ==========================================
# 深度分析綜合判斷結論生成函數
# ==========================================
def generate_summary_insight(df_records, ticker, name, forecast_info=None):
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
    
    if "長期持有" in latest_rec:
        trend_status = "🔵 核心被動持有結構（不執行波段停損停利）"
        action_advice = "隨全球總體經濟長期成長滾動複利或穩定收取配息，免受短期技術指標干擾，建議定期定額或逢低持續續抱。"
        box_color = "#e3f2fd"
        border_color = "#90caf9"
    elif "破底分批加碼" in latest_rec:
        trend_status = "🟢 破底翻多築底確認（左側進場區）"
        action_advice = "已跌破近 1 年低點但日線雙指標翻多站穩 5MA，空方動能耗盡，可採取金字塔分批攤平加碼策略，切勿恐慌殺低。"
        box_color = "#e8f5e9"
        border_color = "#a5d6a7"
    elif "破底打底觀察" in latest_rec:
        trend_status = "🟡 破底未止跌打底區（左側觀望中）"
        action_advice = "跌破 1 年歷史低點且日線指標尚未金叉向上，空方慣性未改。目前嚴禁盲目提早進場接刀，務必耐心等待站穩 5MA 與 MACD 翻紅！"
        box_color = "#fffde7"
        border_color = "#fff59d"
    elif "走勢向上" in latest_rec:
        trend_status = "🟢 順勢多頭波段（右側攻擊架構）"
        action_advice = "長短線指標維持共振多頭，波段趨勢向上確立，持股者續抱主升段，新進部位以 5MA 或 10MA 為移動防守基準。"
        box_color = "#e8f5e9"
        border_color = "#a5d6a7"
    elif "賣出" in latest_rec:
        trend_status = "🔴 空方主導／出清防守結構"
        action_advice = "技術結構處於空頭或高檔正式破位，波段動能出清中。空手者切勿因單日短線強彈貿然追高；持股者應嚴守紀律停損或出清剩餘部位保本。"
        box_color = "#ffebee"
        border_color = "#ef9a9a"
    elif "停利" in latest_rec or "減碼" in latest_rec:
        trend_status = "🟠 高檔轉折／防守減碼結構"
        action_advice = "短線強彈逢高遇壓力，或週線跌破短期均線。建議先收割 30%~50% 獲利落袋為安，其餘以日 5MA 或前低做最後防線。"
        box_color = "#fff3e0"
        border_color = "#ffcc80"
    elif "避免殺低" in latest_rec:
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

    # 均線翻揚預測段落
    forecast_html = ""
    if forecast_info:
        tgt_p = forecast_info['target_price']
        g_pct = forecast_info['growth_pct']
        ded_p = forecast_info['deduction_price']
        sign_str = f"+{g_pct:.2f}%" if g_pct > 0 else f"{g_pct:.2f}%"
        color_g = "#d32f2f" if g_pct > 0 else "#388e3c"
        forecast_html = f"""
        <p style="margin: 6px 0; font-size: 14px; color: #1565c0;">
            <b>【📐 明日 5MA 翻揚預算】</b>：明日扣抵值為 <b>{ded_p:.2f} 元</b>，明日收盤價至少需達 <b>{tgt_p:.2f} 元</b>（需漲幅 <span style="color:{color_g}; font-weight:bold;">{sign_str}</span>），5MA 才會實質站上並向上翻揚！
        </p>
        """

    summary_html = f"""
    <div style="background-color: {box_color}; border: 1.5px solid {border_color}; border-radius: 8px; padding: 16px 20px; margin-top: 20px;">
        <h4 style="margin: 0 0 10px 0; color: #1a1a1a; font-size: 18px;">💡 綜合判斷結論：{ticker} - {name}</h4>
        <p style="margin: 4px 0; font-size: 15px; color: #222;">
            <b>【當前定調】</b>：<span style="font-weight: bold;">{trend_status}</span>
        </p>
        <p style="margin: 4px 0; font-size: 14px; color: #444;">
            <b>【最新狀態 ({latest_date})】</b>：<b>{latest_rec}</b> ｜ 股性：<b>{latest_profile}</b> ｜ 原因：{latest_reason}
        </p>
        {forecast_html}
        <p style="margin: 4px 0; font-size: 14px; color: #444;">
            <b>【區間走勢特徵】</b>：過去 {total_days} 個交易日中，以「{dominant_rec}」為主要常態。{event_text}
        </p>
        <p style="margin: 8px 0 0 0; font-size: 15px; font-weight: bold; color: #b71c1c;">
            🎯 實戰操作建議：{action_advice}
        </p>
    </div>
    """
    return summary_html

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
            if '破底分批加碼' in val: return 'color: #1b5e20; font-weight: bold; background-color: #c8e6c9;'
            elif '走勢向上' in val: return 'color: #2e7d32; font-weight: bold; background-color: #e8f5e9;'
            elif '破底打底觀察' in val: return 'color: #b78103; font-weight: bold; background-color: #fff9c4;'
            elif '長期持有' in val: return 'color: #0d47a1; font-weight: bold; background-color: #e3f2fd;'
            elif '分批停利' in val: return 'color: #e65100; font-weight: bold; background-color: #fff3e0;'
            elif '打底' in val: return 'color: #1565c0; font-weight: bold; background-color: #e3f2fd;'
            elif '週大底+日發動' in val: return 'color: #2e7d32; font-weight: bold; background-color: #e8f5e9;'
            elif '週大底打底' in val: return 'color: #1565c0; font-weight: bold; background-color: #e3f2fd;'
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
    with st.spinner(f"運算 {market_ticker} 總體指標中..."):
        market_trend = get_market_trend(market_ticker)
        if market_trend:
            st.markdown(
                f'''
                <div style="background-color: {market_trend['color']}; padding: 15px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #ccc;">
                    <h4 style="margin: 0; color: #333;">🧭 總體資金水位儀表板 ({market_ticker})</h4>
                    <p style="margin: 5px 0 0 0; font-size: 18px; font-weight: bold; color: #333;">狀態：{market_trend['status']}</p>
                    <p style="margin: 5px 0 0 0; color: #555;">💡 建議：{market_trend['advice']}</p>
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
    
    with st.spinner(f"正在綜合運算【{st.session_state.current_group_choice}】所有標的..."):
        display_df = analyze_signals_comprehensive(ACTIVE_WATCHLIST)

    if not display_df.empty:
        st.subheader(f"📊 【{st.session_state.current_group_choice}】狀態總覽 (長短線綜合唯一解 - 共 {len(display_df)} 檔)")
        
        filter_opt = st.radio(
            "🔍 狀態篩選：", 
            ["👀 顯示全部", "🟢 破底加碼", "🟡 破底觀察", "🟢 只看走勢向上", "💡 醞釀向上", "🔵 長期持有", "🟡 歷史打底", "🟠 分批停利", "⚠️ 醞釀向下", "🟠 建議減碼", "🟡 避免殺低", "🔴 只看賣出", "⚡ 剛發生交叉"], 
            index=0,
            horizontal=True
        )
        
        filtered_df = display_df.copy()
        if filter_opt == "🟢 破底加碼":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("破底分批加碼", na=False)]
        elif filter_opt == "🟡 破底觀察":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("破底打底觀察", na=False)]
        elif filter_opt == "🟢 只看走勢向上":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("走勢向上", na=False)]
        elif filter_opt == "💡 醞釀向上":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("醞釀向上", na=False)]
        elif filter_opt == "🔵 長期持有":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("長期持有", na=False)]
        elif filter_opt == "🟡 歷史打底":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("歷史低檔打底", na=False)]
        elif filter_opt == "🟠 分批停利":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("分批停利", na=False)]
        elif filter_opt == "⚠️ 醞釀向下":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("醞釀向下", na=False)]
        elif filter_opt == "🟠 建議減碼":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("減碼", na=False)]
        elif filter_opt == "🟡 避免殺低":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("避免殺低", na=False)]
        elif filter_opt == "🔴 只看賣出":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("賣出", na=False)]
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
        st.markdown(f"#### 🚀 高動能波段型（週線雙死叉 ＋ 防假突破站穩20MA雙確認） ({len(df_momentum)} 檔)")
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
# 分頁 4：買賣戰情室
# ==========================================
with tab_war_room:
    st.subheader(f"⚔️ 買賣戰情室【{st.session_state.current_group_choice}】 (長短線雙週期綜合唯一解)")
    
    if display_df.empty:
        st.warning(f"⚠️【{st.session_state.current_group_choice}】目前為空，請從『⚙️ 自選股編輯』分頁加入股票。")
    else:
        df_dip_buy = display_df[display_df['建議'].str.contains("破底分批加碼", na=False)].reset_index(drop=True)
        df_dip_watch = display_df[display_df['建議'].str.contains("破底打底觀察", na=False)].reset_index(drop=True)
        df_up = display_df[display_df['建議'].str.contains("醞釀向上", na=False)].reset_index(drop=True)
        df_trend_up = display_df[display_df['建議'].str.contains("走勢向上", na=False)].reset_index(drop=True)
        
        df_hold_core = display_df[display_df['建議'].str.contains("長期持有", na=False)].reset_index(drop=True)
        df_bottom = display_df[display_df['建議'].str.contains("歷史低檔打底", na=False)].reset_index(drop=True)
        df_take_profit = display_df[display_df['建議'].str.contains("分批停利", na=False)].reset_index(drop=True)
        df_down = display_df[display_df['建議'].str.contains("醞釀向下", na=False)].reset_index(drop=True)
        df_trim = display_df[display_df['建議'].str.contains("減碼", na=False)].reset_index(drop=True)
        df_sell = display_df[display_df['建議'].str.contains("賣出", na=False)].reset_index(drop=True)
        df_defense = display_df[display_df['建議'].str.contains("避免殺低", na=False)].reset_index(drop=True)
        
        # 1️⃣ 第一梯隊：左側極限防護區
        if not df_dip_buy.empty:
            st.markdown(f"#### 🎯 破底加碼雷達（已確認翻多）：🟢 破底分批加碼 ({len(df_dip_buy)})")
            ev_dip = st.dataframe(
                style_dataframe(df_dip_buy.drop(columns=['股性類別'])), use_container_width=True,
                on_select="rerun", selection_mode="single-row", key="war_dip",
                column_config={"Yahoo股市": st.column_config.LinkColumn("🔗 Yahoo股市", display_text="點擊前往")}
            )
            if ev_dip.selection.rows:
                st.session_state.selected_ticker = df_dip_buy.iloc[ev_dip.selection.rows[0]]['代碼']
            st.divider()

        if not df_dip_watch.empty:
            st.markdown(f"#### 👀 破底打底觀察（未金叉暫緩加碼）：🟡 破底打底觀察 ({len(df_dip_watch)})")
            ev_watch = st.dataframe(
                style_dataframe(df_dip_watch.drop(columns=['股性類別'])), use_container_width=True,
                on_select="rerun", selection_mode="single-row", key="war_watch",
                column_config={"Yahoo股市": st.column_config.LinkColumn("🔗 Yahoo股市", display_text="點擊前往")}
            )
            if ev_watch.selection.rows:
                st.session_state.selected_ticker = df_dip_watch.iloc[ev_watch.selection.rows[0]]['代碼']
            st.divider()

        # 2️⃣ 第二梯隊：資產配置核心
        if not df_hold_core.empty:
            st.markdown(f"#### 🏛️ 核心資產（免出場長期持有）：🔵 長期持有 ({len(df_hold_core)})")
            ev_core = st.dataframe(
                style_dataframe(df_hold_core.drop(columns=['股性類別'])), use_container_width=True,
                on_select="rerun", selection_mode="single-row", key="war_core",
                column_config={"Yahoo股市": st.column_config.LinkColumn("🔗 Yahoo股市", display_text="點擊前往")}
            )
            if ev_core.selection.rows:
                st.session_state.selected_ticker = df_hold_core.iloc[ev_core.selection.rows[0]]['代碼']

        # 3️⃣ 第三梯隊：右側常規多頭波段
        st.markdown(f"#### 第一步（找獵物）：💡 醞釀向上 ({len(df_up)})  [週線大底即將完成最高優先]")
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

        st.markdown(f"#### 第二步（扣板機）：🟢 只看走勢向上 ({len(df_trend_up)})")
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
                
        st.divider()

        # 4️⃣ 第四梯隊：轉折防守與出場管控
        if not df_bottom.empty:
            st.markdown(f"#### 🛡️ 歷史低檔保護（切勿殺低 / 抱牢）：🟡 歷史低檔打底 ({len(df_bottom)})")
            ev_bt = st.dataframe(
                style_dataframe(df_bottom.drop(columns=['股性類別'])), use_container_width=True,
                on_select="rerun", selection_mode="single-row", key="war_bt",
                column_config={"Yahoo股市": st.column_config.LinkColumn("🔗 Yahoo股市", display_text="點擊前往")}
            )
            if ev_bt.selection.rows:
                st.session_state.selected_ticker = df_bottom.iloc[ev_bt.selection.rows[0]]['代碼']

        if not df_take_profit.empty:
            st.markdown(f"#### 轉折防護（強彈先收獲利）：🟠 分批停利 ({len(df_take_profit)})")
            ev_tp = st.dataframe(
                style_dataframe(df_take_profit.drop(columns=['股性類別'])), use_container_width=True,
                on_select="rerun", selection_mode="single-row", key="war_tp",
                column_config={"Yahoo股市": st.column_config.LinkColumn("🔗 Yahoo股市", display_text="點擊前往")}
            )
            if ev_tp.selection.rows:
                st.session_state.selected_ticker = df_take_profit.iloc[ev_tp.selection.rows[0]]['代碼']

        st.markdown(f"#### 第一步（提防見頂）：⚠️ 醞釀向下 ({len(df_down)})")
        if df_down.empty:
            st.info("目前無『醞釀向下』標的。")
        else:
            ev_down = st.dataframe(
                style_dataframe(df_down.drop(columns=['股性類別'])), use_container_width=True, 
                on_select="rerun", selection_mode="single-row", key="war_down",
                column_config={"Yahoo股市": st.column_config.LinkColumn("🔗 Yahoo股市", display_text="點擊前往")}
            )
            if ev_down.selection.rows:
                st.session_state.selected_ticker = df_down.iloc[ev_down.selection.rows[0]]['代碼']

        if not df_trim.empty:
            st.markdown(f"#### 第二步 A（動能型減碼防線）：🟠 建議減碼50% ({len(df_trim)})")
            ev_trim = st.dataframe(
                style_dataframe(df_trim.drop(columns=['股性類別'])), use_container_width=True,
                on_select="rerun", selection_mode="single-row", key="war_trim",
                column_config={"Yahoo股市": st.column_config.LinkColumn("🔗 Yahoo股市", display_text="點擊前往")}
            )
            if ev_trim.selection.rows:
                st.session_state.selected_ticker = df_trim.iloc[ev_trim.selection.rows[0]]['代碼']

        st.markdown(f"#### 第二步 B（紀律出場/出清）：🔴 只看賣出 ({len(df_sell)})")
        if df_sell.empty:
            st.info("目前無『賣出』標的。")
        else:
            ev_sell = st.dataframe(
                style_dataframe(df_sell.drop(columns=['股性類別'])), use_container_width=True, 
                on_select="rerun", selection_mode="single-row", key="war_sell",
                column_config={"Yahoo股市": st.column_config.LinkColumn("🔗 Yahoo股市", display_text="點擊前往")}
            )
            if ev_sell.selection.rows:
                st.session_state.selected_ticker = df_sell.iloc[ev_sell.selection.rows[0]]['代碼']

        st.markdown(f"#### 第三步（最後確認）：🟡 避免殺低 ({len(df_defense)})")
