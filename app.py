import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh
import json
import os

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

# 解析字串為字典的公用函數
def parse_watchlist(text):
    watchlist = {}
    for line in text.strip().split('\n'):
        if ',' in line:
            ticker, name = line.split(',', 1)
            watchlist[ticker.strip()] = name.strip()
    return watchlist

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

# 建立 4 個分頁
tab_dashboard, tab_rules, tab_settings, tab_war_room = st.tabs(["📊 看盤儀表板", "📖 策略判斷原則", "⚙️ 自選股編輯", "⚔️ 買賣戰情室"])
display_df = pd.DataFrame()

# ==========================================
# 分頁 3：自選股編輯頁面 (支援 3 組切換編輯)
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

# 取得當前選取的自選股清單
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
    st.header("📖 雙指標波段系統 - 判斷原則（長短線雙週期綜合唯一解）")
    st.markdown("""
    本系統採用「長線保護短線」的全方位跨週期綜合評估。**每檔股票只會有一個綜合最佳建議**，不隨檢視圖表切換而改變：
    
    ### 🧬 股性自適應分流機制
    
    * **💰 貨幣市場 / 超短債存債模式**：
        * **鎖定條件**：SGOV、BIL、SHV 等超短天期美國國債或貨幣市場 ETF。
        * **操作機制**：**【免出場長期持有】**。此類標的波動極微且每月穩定配息，不適用波段技術指標，系統自動鎖定為長期領息，永不發出賣出訊號。

    * **🏛️ 穩健權值 / 指數ETF型**：
        * **鎖定條件**：大型權值、傳產循環股（ATR% < 3.5%），或大盤指數 ETF（如 0050、VOO、QQQM 等）。
        * **進場條件**：長短線共振帶量買進（或 SPC 極端超跌爆量）。
        * **出場機制**：啟動【日線敏捷出場】。當週線 DIF 下降且日線雙指標翻空時出場，防止回吐高檔波段利潤。
    
    * **🚀 高動能波段型**：
        * **鎖定條件**：中小型科技股、高波動成長飆股（ATR% ≥ 3.5%）。
        * **進場條件**：長短線共振帶量買進（或打底起漲）。
        * **出場機制**：啟動【週線雙死叉分批出場 ＋ 歷史低點保護】：
            1. **第一階段防線**：週 5W 跌破 10W 時，建議減碼 50% 鎖住部分利潤。
            2. **終極出清防線**：週 MACD 正式死叉時，原則出清剩餘 50% 持股。
            3. **🛡️ 近 1 年歷史低點保護網**：若股價處於近 1 年歷史相對低點區間（位階 ≤ 25%），系統自動攔截賣出訊號，改為提示【歷史低檔打底 (抱牢)】，切勿在相對低檔盲目出清。
            4. **💡 強彈保護傘**：若單日大漲逾 4%，改為提示【分批停利】，兼顧獲利落袋與防守。

    ---

    ### 🟢 買入標準 (滿足其一即為買點)
    1. **順勢共振買點 (長短線雙多)**：週線 MACD>0 且 5W>10W；日線 MACD>0 且 5MA>10MA，當日成交量 > 5日均量。
    2. **逆勢超跌買點 (爆量 + RSI 雙濾網)**：跌破 LCL (20MA-2σ)，成交量大於 5日均量 2 倍，且 RSI(14) < 30。

    ### 💡 雙向預警雷達 (以「週線大底即將完成」為最高優先)
    - **🌟 醞釀向上 (週大底+日發動)**：週 MACD 綠柱收斂站上 5W 均線，且**日線已同步翻多轉強**。大波段起跑最高勝率標的！
    - **💡 醞釀向上 (週大底打底)**：週 MACD 綠柱持續縮減或 RSI 低檔脫離，長線大格局底部沉澱中。
    - **⚠️ 醞釀向下 (提防見頂)**：(需滿足 **週線 DIF 下降** 前提) MACD 紅柱縮減且股價跌破 5MA；或 RSI(14) ≥ 70。

    ### 🟡 避免殺低防護網 (極重要)
    - 若已滿足賣出條件，但股價**已跌破 LCL 下軌** 或 **RSI(14) ≤ 30**，代表短線極度超跌。系統會強制攔截賣出訊號，改為提示**「🟡 避免殺低」**，提醒等待技術性反彈回 10MA 再行減碼。
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
    CASH_BOND_LIST = {"SGOV", "BIL", "SHV", "00719B.TW"}
    ETF_WHITE_LIST = {"0050.TW", "VOO", "QQQM", "SPY", "IVV", "0056.TW", "00878.TW", "00919.TW"}

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
            
            is_cash_bond = (ticker in CASH_BOND_LIST) or ("美債" in name and "0-3" in name) or ("超短債" in name)
            is_etf_or_index = (
                ticker in ETF_WHITE_LIST 
                or "ETF" in name.upper() 
                or "50" in name 
                or "指數" in name
            )
            
            if is_cash_bond:
                is_high_momentum = False
                stock_profile = "💰 收息·存債"
                stock_category = "穩健型"
            elif is_etf_or_index:
                is_high_momentum = False
                stock_profile = "🏛️ 穩健·指數ETF"
                stock_category = "穩健型"
            else:
                is_high_momentum = (atr_pct >= 3.5)
                stock_profile = f"🚀 動能({atr_pct:.1f}%)" if is_high_momentum else f"🏛️ 穩健({atr_pct:.1f}%)"
                stock_category = "高動能型" if is_high_momentum else "穩健型"

            high_1y = high_d.tail(250).max()
            low_1y = low_d.tail(250).min()
            percentile_1y = ((curr_close - low_1y) / (high_1y - low_1y)) * 100 if high_1y > low_1y else 50.0
            is_relative_low = (percentile_1y <= 25.0)

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
                w_rsi = rsi_w.iloc[-1]
            else:
                weekly_dif_decreasing = False
                weekly_ma_dead = False
                weekly_macd_dead = False
                is_weekly_bullish = True
                w_close, w_ma5, w_hist, w_prev_hist, w_rsi = curr_close, curr_ma5_d, curr_hist_d, prev_hist_d, curr_rsi_d

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
            
            is_weekly_bottom_forming = (w_hist < 0 and w_hist > w_prev_hist) or (w_close > w_ma5 and w_hist < 0) or (w_rsi <= 40)
            is_daily_launching = (curr_close > curr_ma5_d) and (curr_hist_d > prev_hist_d)

            # 綜合唯一建議判定
            if is_cash_bond:
                rec_text = "🔵 長期持有 (領息)"
                detail_reason = "【免出場存債模式】純收息超短債資產，波動極低且穩定配息，免受波段指標干擾，建議長期續抱。"
            else:
                if target_pos_d == 100 and vol_condition_d:
                    if not is_weekly_bullish:
                        rec_text = "🟡 觀察"
                        detail_reason = "【短多長空】日線翻多帶量，但週線長線格局尚未同步，暫作觀察。"
                    else:
                        rec_text = "🟢 買入"
                        detail_reason = "【長短線共振帶量】週線維持長多，日線雙指標翻多且成交量超越5日均量！"
                
                elif target_pos_d == 0:
                    if curr_rsi_d <= 30 or curr_close <= curr_lcl_d:
                        rec_text = "🟡 避免殺低"
                        detail_reason = f"【嚴重負乖離】日線跌破LCL或RSI極度超賣({curr_rsi_d:.1f})，切勿恐慌殺低，靜待技術反彈。"
                    else:
                        if is_high_momentum:
                            if is_weekly_bottom_forming:
                                if is_daily_launching:
                                    rec_text = "🌟 醞釀向上 (週大底+日發動)"
                                    detail_reason = "【週線大底＋日線發動】週MACD綠柱持續收斂打底，日線已率先帶動站上5MA轉強，大波段起跑首選！"
                                else:
                                    rec_text = "💡 醞釀向上 (週大底打底)"
                                    detail_reason = "【週線大底沉澱】週MACD綠柱收斂或低檔超賣，大格局正築底中，適合左側分批布局。"
                            elif is_relative_low:
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
                            detail_reason = "【週線大底＋日線發動】週MACD綠柱持續收斂打底，日線已率先帶動站上5MA轉強，大波段起跑首選！"
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
            if "買入" in row['建議']: return 1  
            elif "週大底+日發動" in row['建議']: return 2
            elif "週大底打底" in row['建議']: return 3
            elif "長期持有" in row['建議']: return 4
            elif "打底" in row['建議']: return 5
            elif "停利" in row['建議']: return 6
            elif "醞釀向下" in row['建議']: return 7
            elif "減碼" in row['建議']: return 8
            elif "避免殺低" in row['建議']: return 9 
            elif "觀察" in row['建議']: return 10
            elif "賣出" in row['建議']: return 11
            else: return 12
        df_results['SortRank'] = df_results.apply(get_sort_rank, axis=1)
        df_results = df_results.sort_values(by=['SortRank', '代碼']).drop(columns=['SortRank']).reset_index(drop=True)
        
    return df_results

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
            if '分批停利' in val: return 'color: #e65100; font-weight: bold; background-color: #fff3e0;'
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
# 分頁 1：主看盤儀表板 (支援切換 3 組自選股)
# ==========================================
with tab_dashboard:
    # 頂部控制面板：選擇自選股組合 ＋ 切換線圖週期
    col_group, col_chart = st.columns([1, 1])
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

    with col_chart:
        chart_timeframe = st.radio(
            "📊 線圖顯示週期 (僅切換下方K線圖)：", 
            ["日線圖 (Daily)", "週線圖 (Weekly)"], 
            index=0,
            horizontal=True
        )

    tf_interval = "1wk" if chart_timeframe == "週線圖 (Weekly)" else "1d"
    tf_period = "2y" if chart_timeframe == "週線圖 (Weekly)" else "1y"
    ma_s_lbl = "5W" if chart_timeframe == "週線圖 (Weekly)" else "5D"
    ma_l_lbl = "10W" if chart_timeframe == "週線圖 (Weekly)" else "10D"

    # 總體資金水位儀表板 
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

    # 臨時標的快速分析
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
    
    # 主要分析運算 (使用當前選取的自選股組合)
    with st.spinner(f"正在綜合運算【{st.session_state.current_group_choice}】所有標的..."):
        display_df = analyze_signals_comprehensive(ACTIVE_WATCHLIST)

    if not display_df.empty:
        st.subheader(f"📊 【{st.session_state.current_group_choice}】狀態總覽 (長短線綜合唯一解 - 共 {len(display_df)} 檔)")
        
        # 快速篩選器
        filter_opt = st.radio(
            "🔍 狀態篩選：", 
            ["👀 顯示全部", "🟢 只看買入", "💡 醞釀向上", "🔵 長期持有", "🟡 歷史打底", "🟠 分批停利", "⚠️ 醞釀向下", "🟠 建議減碼", "🟡 避免殺低", "🔴 只看賣出", "⚡ 剛發生交叉"], 
            index=0,
            horizontal=True
        )
        
        filtered_df = display_df.copy()
        if filter_opt == "🟢 只看買入":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("買入", na=False)]
        elif filter_opt == "💡 醞釀向上":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("醞釀向上", na=False)]
        elif filter_opt == "🔵 長期持有":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("長期持有", na=False)]
        elif filter_opt == "🟡 歷史打底":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("打底", na=False)]
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

        # 依股性分區塊獨立呈現
        df_steady = filtered_df[filtered_df['股性類別'] == "穩健型"].drop(columns=['股性類別']).reset_index(drop=True)
        df_momentum = filtered_df[filtered_df['股性類別'] == "高動能型"].drop(columns=['股性類別']).reset_index(drop=True)

        st.markdown(f"#### 🏛️ 穩健權值 / 指數ETF型（日線敏捷出場 / 存債） ({len(df_steady)} 檔)")
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
        st.markdown(f"#### 🚀 高動能波段型（週線雙死叉 ＋ 近1年歷史低點/強彈雙保護） ({len(df_momentum)} 檔)")
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
    st.subheader(f"📉 價量與指標複合分析圖 ({chart_timeframe})")

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
                
                end_date = chart_df.index[-1]
                start_date = end_date - pd.DateOffset(years=1) if tf_interval == "1wk" else end_date - pd.DateOffset(months=3)

                fig.update_xaxes(
                    range=[start_date, end_date],
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
# 分頁 4：買賣戰情室 (同步套用所選自選股組合)
# ==========================================
with tab_war_room:
    st.subheader(f"⚔️ 買賣戰情室【{st.session_state.current_group_choice}】 (長短線雙週期綜合唯一解)")
    
    if display_df.empty:
        st.warning(f"⚠️【{st.session_state.current_group_choice}】目前為空，請從『⚙️ 自選股編輯』分頁加入股票。")
    else:
        df_up = display_df[display_df['建議'].str.contains("醞釀向上", na=False)].reset_index(drop=True)
        df_buy = display_df[display_df['建議'].str.contains("買入", na=False)].reset_index(drop=True)
        
        df_bottom = display_df[display_df['建議'].str.contains("打底", na=False)].reset_index(drop=True)
        df_take_profit = display_df[display_df['建議'].str.contains("分批停利", na=False)].reset_index(drop=True)
        df_down = display_df[display_df['建議'].str.contains("醞釀向下", na=False)].reset_index(drop=True)
        df_trim = display_df[display_df['建議'].str.contains("減碼", na=False)].reset_index(drop=True)
        df_sell = display_df[display_df['建議'].str.contains("賣出", na=False)].reset_index(drop=True)
        df_hold = display_df[display_df['建議'].str.contains("避免殺低", na=False)].reset_index(drop=True)
        
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

        st.markdown(f"#### 第二步（扣板機）：🟢 只看買入 ({len(df_buy)})")
        if df_buy.empty:
            st.info("目前無『買入』標的。")
        else:
            ev_buy = st.dataframe(
                style_dataframe(df_buy.drop(columns=['股性類別'])), use_container_width=True, 
                on_select="rerun", selection_mode="single-row", key="war_buy",
                column_config={"Yahoo股市": st.column_config.LinkColumn("🔗 Yahoo股市", display_text="點擊前往")}
            )
            if ev_buy.selection.rows:
                st.session_state.selected_ticker = df_buy.iloc[ev_buy.selection.rows[0]]['代碼']
                
        st.divider()

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

        st.markdown(f"#### 第三步（最後確認）：🟡 避免殺低 ({len(df_hold)})")
        if df_hold.empty:
            st.info("目前無『避免殺低』標的。")
        else:
            ev_hold = st.dataframe(
                style_dataframe(df_hold.drop(columns=['股性類別'])), use_container_width=True, 
                on_select="rerun", selection_mode="single-row", key="war_hold",
                column_config={"Yahoo股市": st.column_config.LinkColumn("🔗 Yahoo股市", display_text="點擊前往")}
            )
            if ev_hold.selection.rows:
                st.session_state.selected_ticker = df_hold.iloc[ev_hold.selection.rows[0]]['代碼']

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
