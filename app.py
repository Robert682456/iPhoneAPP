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
# 本機設定檔存取邏輯 (狀態記憶功能)
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "user_settings.json")

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"search_ticker": "", "search_name": "", "market_ticker": "0050.TW"}

def save_settings():
    settings = {
        "search_ticker": st.session_state.search_ticker,
        "search_name": st.session_state.search_name,
        "market_ticker": st.session_state.get("market_ticker_input", "0050.TW")
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

def update_selected_from_search():
    val = st.session_state.search_ticker.strip().upper()
    if val:
        st.session_state.selected_ticker = val
    save_settings()

def update_other_inputs():
    save_settings()

DEFAULT_LIST = """0050.TW,元大台灣50
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

if 'watchlist_text' not in st.session_state:
    st.session_state.watchlist_text = DEFAULT_LIST

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
# 分頁 3：自選股編輯頁面
# ==========================================
with tab_settings:
    st.subheader("⚙️ 編輯自選股清單")
    st.markdown("請依照 `代碼,名稱` 的格式輸入，每行一檔標的。修改後會自動儲存並套用至儀表板。")
    user_input = st.text_area("📝 編輯清單：", st.session_state.watchlist_text, height=500)
    st.session_state.watchlist_text = user_input
    
    WATCHLIST = {}
    for line in user_input.strip().split('\n'):
        if ',' in line:
            ticker, name = line.split(',', 1)
            WATCHLIST[ticker.strip()] = name.strip()

# ==========================================
# 分頁 2：策略判斷原則
# ==========================================
with tab_rules:
    st.header("📖 雙指標波段系統 - 判斷原則（含股性自適應分流）")
    st.markdown("""
    本系統專注於「順勢波段做多」與「極端超跌抄底」，並依據 **14日 ATR%**、**ETF/指數濾網** 與 **存債白名單** 自動切換模式：
    
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
        * **出場機制**：啟動【週線雙死叉分批出場 ＋ 歷史低點/強彈雙保護網】：
            1. **第一階段防線**：週 5W 跌破 10W 時，建議減碼 50% 鎖住部分利潤。
            2. **終極出清防線**：週 MACD 正式死叉時，原則出清剩餘 50% 持股。
            3. **🛡️ 近 1 年歷史低點保護網**：若股價處於近 1 年歷史相對低點區間（位階 ≤ 25%），系統自動攔截賣出訊號，改為提示【歷史低檔打底 (抱牢)】，切勿在相對低檔盲目出清。
            4. **💡 強彈保護傘**：若單日大漲逾 4% 或出現綠柱收斂站上 5MA，系統改為提示【分批停利】，兼顧獲利落袋與防守。

    ---

    ### 🟢 買入標準 (滿足其一即為買點)
    1. **順勢共振買點 (長短線雙多)**：週線 MACD>0 且 5W>10W；日線 MACD>0 且 5MA>10MA，當日成交量 > 5日均量。
    2. **逆勢超跌買點 (爆量 + RSI 雙濾網)**：跌破 LCL (20MA-2σ)，成交量大於 5日均量 2 倍，且 RSI(14) < 30。

    ### 💡 雙向預警雷達 (以「週線大底即將完成」為優先核心)
    - **🌟 醞釀向上 (週大底＋日轉強)**：週 MACD 綠柱收斂站上 5W 均線，且**日線已同步翻多轉強**。大波段起跑最高勝率標的！
    - **💡 醞釀向上 (週線大底打底)**：週 MACD 綠柱持續縮減、週 RSI 低檔脫離，大格局底部成型中。
    - **⚠️ 醞釀向下 (提防見頂)**：(需滿足 **週線 DIF 下降** 前提) MACD 紅柱縮減且股價跌破 5MA；或 RSI(14) ≥ 70。

    ### 🟡 避免殺低防護網 (極重要)
    - 若已滿足賣出條件，但股價**已跌破 LCL 下軌** 或 **RSI(14) ≤ 30**，代表短線極度超跌。系統會強制攔截賣出訊號，改為提示**「🟡 避免殺低」**，提醒等待技術性反彈回 10MA 再行減碼。
    """)

# ==========================================
# 核心函數定義區
# ==========================================
@st.cache_data(ttl=300)
def get_market_trend(ticker, interval, period):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
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
def analyze_signals(interval, period, ma_s_label, ma_l_label, watchlist):
    results = []
    CASH_BOND_LIST = {"SGOV", "BIL", "SHV", "00719B.TW"}
    ETF_WHITE_LIST = {"0050.TW", "VOO", "QQQM", "SPY", "IVV", "0056.TW", "00878.TW", "00919.TW"}

    for ticker, name in watchlist.items():
        try:
            df = yf.download(ticker, period=period, interval=interval, progress=False)
            if df.empty or len(df) < 35:
                results.append({
                    "代碼": ticker, "名稱": name, "收盤價(漲跌)": "⚠️ 無資料",
                    "股性模式": "⚪ 未知", "股性類別": "未知",
                    "建議": "⚪ 未知", "最新動態": "-",
                    "詳細判定原因": "無足夠 K 線資料，請檢查代碼格式",
                    "Yahoo股市": f"https://finance.yahoo.com/quote/{ticker}"
                })
                continue
            
            close = df['Close'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['Close']
            high = df['High'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['High']
            low = df['Low'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['Low']
            volume = df['Volume'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['Volume']
            close, high, low, volume = close.dropna(), high.dropna(), low.dropna(), volume.dropna()
            
            # --- 股性指標計算 ---
            tr1 = high - low
            tr2 = (high - close.shift(1)).abs()
            tr3 = (low - close.shift(1)).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr14 = tr.rolling(14).mean().iloc[-1]
            curr_close, prev_close = close.iloc[-1], close.iloc[-2]
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
            
            # --- 計算近 1 年歷史相對位階百分位 ---
            lookback_1y = 52 if interval == "1wk" else min(250, len(close))
            high_1y = high.tail(lookback_1y).max()
            low_1y = low.tail(lookback_1y).min()
            if high_1y > low_1y:
                percentile_1y = ((curr_close - low_1y) / (high_1y - low_1y)) * 100
            else:
                percentile_1y = 50.0
            
            is_relative_low = (percentile_1y <= 25.0)

            ma5, ma10, ma20 = close.rolling(5).mean(), close.rolling(10).mean(), close.rolling(20).mean()
            vol_ma5 = volume.rolling(5).mean()
            
            ema12, ema26 = close.ewm(span=12, adjust=False).mean(), close.ewm(span=26, adjust=False).mean()
            dif = ema12 - ema26
            dea = dif.ewm(span=9, adjust=False).mean()
            hist = dif - dea 
            
            delta = close.diff()
            gain = delta.clip(lower=0)
            loss = -1 * delta.clip(upper=0)
            ema_gain = gain.ewm(com=13, adjust=False).mean()
            ema_loss = loss.ewm(com=13, adjust=False).mean()
            rs = ema_gain / ema_loss
            rsi = 100 - (100 / (1 + rs))
            curr_rsi = rsi.iloc[-1]

            std20 = close.rolling(20).std()
            ucl = ma20 + 2 * std20
            lcl = ma20 - 2 * std20
            curr_ucl, curr_lcl = ucl.iloc[-1], lcl.iloc[-1]

            curr_ma5, curr_ma10 = ma5.iloc[-1], ma10.iloc[-1]
            curr_ma20, prev_ma20 = ma20.iloc[-1], ma20.iloc[-2]
            curr_hist, prev_hist = hist.iloc[-1], hist.iloc[-2]
            curr_vol, curr_vol_ma5 = volume.iloc[-1], vol_ma5.iloc[-1]
            curr_dif, prev_dif = dif.iloc[-1], dif.iloc[-2]
            
            weekly_dif_decreasing = False
            curr_dif_w_val, prev_dif_w_val = 0.0, 0.0
            weekly_ma_dead = False
            weekly_macd_dead = False
            
            # ==========================================
            # 取得「真實週線」與「真實日線」雙週期數據
            # ==========================================
            if interval == "1d":
                d_close, d_ma5, d_hist, d_prev_hist = curr_close, curr_ma5, curr_hist, prev_hist
                df_w = yf.download(ticker, period="2y", interval="1wk", progress=False)
                if not df_w.empty and len(df_w) >= 35:
                    close_w = df_w['Close'][ticker] if isinstance(df_w.columns, pd.MultiIndex) else df_w['Close']
                    close_w = close_w.dropna()
                    ma5_w, ma10_w = close_w.rolling(5).mean(), close_w.rolling(10).mean()
                    ema12_w = close_w.ewm(span=12, adjust=False).mean()
                    ema26_w = close_w.ewm(span=26, adjust=False).mean()
                    dif_w = ema12_w - ema26_w
                    hist_w = dif_w - dif_w.ewm(span=9, adjust=False).mean()
                    
                    delta_w = close_w.diff()
                    gw = delta_w.clip(lower=0).ewm(com=13, adjust=False).mean()
                    lw = (-1 * delta_w.clip(upper=0)).ewm(com=13, adjust=False).mean()
                    rsi_w = 100 - (100 / (1 + (gw / lw)))
                    
                    w_close = close_w.iloc[-1]
                    w_ma5 = ma5_w.iloc[-1]
                    w_hist = hist_w.iloc[-1]
                    w_prev_hist = hist_w.iloc[-2]
                    w_rsi = rsi_w.iloc[-1]
                    
                    if len(dif_w) >= 2:
                        curr_dif_w_val = dif_w.iloc[-1]
                        prev_dif_w_val = dif_w.iloc[-2]
                        weekly_dif_decreasing = curr_dif_w_val < prev_dif_w_val
                    
                    weekly_ma_dead = (ma5_w.iloc[-1] < ma10_w.iloc[-1])
                    weekly_macd_dead = (hist_w.iloc[-1] <= 0)
                    is_weekly_bullish = (hist_w.iloc[-1] > 0 and ma5_w.iloc[-1] > ma10_w.iloc[-1])
                    weekly_status = "週線長多" if is_weekly_bullish else "週線偏空"
                else:
                    w_close, w_ma5, w_hist, w_prev_hist, w_rsi = curr_close, curr_ma5, curr_hist, prev_hist, curr_rsi
                    is_weekly_bullish = True
                    weekly_status = "週線長多"
            else:
                # 當前已在週線模式
                w_close, w_ma5, w_hist, w_prev_hist, w_rsi = curr_close, curr_ma5, curr_hist, prev_hist, curr_rsi
                weekly_dif_decreasing = curr_dif < prev_dif
                curr_dif_w_val, prev_dif_w_val = curr_dif, prev_dif
                weekly_ma_dead = (curr_ma5 < curr_ma10) and (ma5.iloc[-2] >= ma10.iloc[-2])
                weekly_macd_dead = (curr_hist <= 0) and (prev_hist > 0)
                is_weekly_bullish = (curr_hist > 0 and curr_ma5 > curr_ma10)
                weekly_status = "週線長多" if is_weekly_bullish else "週線偏空"
                
                df_d = yf.download(ticker, period="6mo", interval="1d", progress=False)
                if not df_d.empty and len(df_d) >= 35:
                    close_d = df_d['Close'][ticker] if isinstance(df_d.columns, pd.MultiIndex) else df_d['Close']
                    close_d = close_d.dropna()
                    ma5_d = close_d.rolling(5).mean()
                    ema12_d = close_d.ewm(span=12, adjust=False).mean()
                    ema26_d = close_d.ewm(span=26, adjust=False).mean()
                    dif_d = ema12_d - ema26_d
                    hist_d = dif_d - dif_d.ewm(span=9, adjust=False).mean()
                    
                    d_close = close_d.iloc[-1]
                    d_ma5 = ma5_d.iloc[-1]
                    d_hist = hist_d.iloc[-1]
                    d_prev_hist = hist_d.iloc[-2]
                else:
                    d_close, d_ma5, d_hist, d_prev_hist = curr_close, curr_ma5, curr_hist, prev_hist

            # ==========================================
            # 🎯 優先核心：週線大底即將完成 (Bottom Forming)
            # ==========================================
            # 條件：週 MACD 綠柱收斂 (w_hist < 0 且 w_hist > w_prev_hist)
            #       或週價已站上週 5W 均線 (w_close > w_ma5)
            #       或週 RSI 位於相對低檔 (w_rsi <= 40)
            is_weekly_bottom_forming = (w_hist < 0 and w_hist > w_prev_hist) or (w_close > w_ma5 and w_hist < 0) or (w_rsi <= 40)
            
            # 日線是否同步轉強發動
            is_daily_confirmed = (d_close > d_ma5) and (d_hist > d_prev_hist)

            vol_condition = curr_vol > curr_vol_ma5  
            
            change_pct = ((curr_close - prev_close) / prev_close) * 100
            if change_pct > 0: price_display = f"🔺 {curr_close:.2f} (+{change_pct:.2f}%)"
            elif change_pct < 0: price_display = f"🔻 {curr_close:.2f} ({change_pct:.2f}%)"
            else: price_display = f"➖ {curr_close:.2f} (0.00%)"
            
            last_date_str = close.index[-1].strftime('%m/%d')
            
            actions = []
            if interval == "1d" and prev_close <= prev_ma20 and curr_close > curr_ma20:
                actions.append(f"日線突破20MA ({last_date_str})")
            if prev_hist <= 0 and curr_hist > 0:
                actions.append(f"MACD剛金叉 ({last_date_str})")
            elif prev_hist >= 0 and curr_hist < 0:
                actions.append(f"MACD剛死叉 ({last_date_str})")
            if ma5.iloc[-2] <= ma10.iloc[-2] and curr_ma5 > curr_ma10:
                actions.append(f"MA剛金叉 ({last_date_str})")
            elif ma5.iloc[-2] >= ma10.iloc[-2] and curr_ma5 < curr_ma10:
                actions.append(f"MA剛死叉 ({last_date_str})")
                
            target_position = (50 if curr_hist > 0 else 0) + (50 if curr_ma5 > curr_ma10 else 0)
            
            macd_sign = (hist > 0).astype(int)
            macd_crosses = macd_sign.diff()[macd_sign.diff() != 0].dropna()
            macd_date = macd_crosses.index[-1].strftime('%m/%d') if not macd_crosses.empty else "-"
            
            ma_sign = (ma5 > ma10).astype(int)
            ma_crosses = ma_sign.diff()[ma_sign.diff() != 0].dropna()
            ma_date = ma_crosses.index[-1].strftime('%m/%d') if not ma_crosses.empty else "-"

            macd_text = f"MACD>0(自{macd_date})" if curr_hist > 0 else f"MACD<0(自{macd_date})"
            ma_text = f"{ma_s_label}>{ma_l_label}(自{ma_date})" if curr_ma5 > curr_ma10 else f"{ma_s_label}<{ma_l_label}(自{ma_date})"

            # ==========================================
            # 建議判定 (存債資產強制免出場攔截)
            # ==========================================
            if is_cash_bond:
                rec_text = "🔵 長期持有 (領息)"
                detail_reason = "【免出場存債模式】純收息超短債資產，波動極低且穩定配息，免受波段指標干擾，建議長期續抱。"
            else:
                if target_position == 100:
                    if vol_condition:
                        if interval == "1d" and not is_weekly_bullish:
                            rec_text = "🟡 觀察"
                            detail_reason = f"【短多長空】日線翻多帶量，但{weekly_status}，反彈暫不進場"
                        else:
                            rec_text = "🟢 買入"
                            resonance_text = " (長短線共振)" if interval == "1d" else ""
                            detail_reason = f"【雙多頭+帶量】{macd_text} 且 {ma_text}，量>{ma_s_label}均量{resonance_text}"
                    else:
                        rec_text = "🟡 觀察"
                        detail_reason = f"【量能不足】{macd_text} 且 {ma_text}，量縮觀望"
                
                elif target_position == 0:
                    if curr_rsi <= 30 or curr_close <= curr_lcl:
                        rec_text = "🟡 避免殺低"
                        detail_reason = f"【乖離過大】雖已破線，但股價跌破LCL或RSI極度超賣({curr_rsi:.1f})，切勿恐慌殺低。 👉 預估初步反彈壓力：{ma_l_label} (約 {curr_ma10:.2f})"
                    else:
                        if is_high_momentum:
                            if weekly_macd_dead:
                                # 🛡️ 歷史相對低點攔截保護 (近1年位階 ≤ 25%)
                                if is_relative_low:
                                    rec_text = "🟡 歷史低檔打底 (抱牢)"
                                    detail_reason = f"【歷史相對低點保護】近1年位階僅 {percentile_1y:.1f}%(≤25%)，基期極低且逼近年度大底({low_1y:.2f})，週線死叉具滯後性，低接者切勿在底部殺低，建議耐心抱牢！"
                                elif change_pct >= 4.0:
                                    rec_text = "🟠 分批停利 (強彈中)"
                                    detail_reason = f"【低接強彈保護】週線雖死叉，但當日強漲 {change_pct:.2f}%，低檔有大單承接，建議先分批獲利減碼 30%~50%，剩餘持股改看日線 5MA 防守，切勿盲目清倉！"
                                else:
                                    rec_text = "🔴 賣出 (動能出清)"
                                    detail_reason = f"【動能型終極出場】週MACD死叉確認大波段結束，建議出清剩餘 50% 部位。"
                            elif weekly_ma_dead:
                                if is_relative_low:
                                    rec_text = "🟡 歷史低檔打底 (抱牢)"
                                    detail_reason = f"【歷史相對低點保護】近1年位階僅 {percentile_1y:.1f}%(≤25%)，股價處於年度底部區間，暫緩停損減碼，建議耐心等待打底反彈。"
                                else:
                                    rec_text = "🟠 減碼 (週MA死叉)"
                                    detail_reason = f"【動能型第一防線】週5W跌破10W，先行減碼 50% 鎖住利潤，其餘等週MACD確認。"
                            else:
                                rec_text = "🟡 觀察 (抱牢主升)"
                                detail_reason = f"【動能型抱牢】日線震盪洗盤，但週線 5W>10W 且 MACD>0，無懼短線波動續抱。"
                        else:
                            if weekly_dif_decreasing:
                                rec_text = "🔴 賣出 (日線敏捷)"
                                detail_reason = f"【穩健型防守】週線DIF下降且日線翻空，保護獲利全數出場。"
                            else:
                                rec_text = "🟡 觀察"
                                detail_reason = f"【防守延遲】日線翻空，但週線DIF仍上升，暫緩賣出。"
                else:
                    rec_text = "🟡 觀察"
                    if not weekly_dif_decreasing and curr_hist < 0:
                        detail_reason = f"【方向分歧】指標偏空，但週線DIF仍上升，暫緩防守。"
                    else:
                        detail_reason = f"【方向分歧】{macd_text} 但 {ma_text}，指標未同步。"

                # ==========================================
                # 雙向預警雷達 (週線大底即將完成優先)
                # ==========================================
                if "買入" not in rec_text and "賣出" not in rec_text and "減碼" not in rec_text and "停利" not in rec_text and "打底" not in rec_text and "殺低" not in rec_text:
                    if weekly_dif_decreasing and curr_rsi >= 70:
                        rec_text = "⚠️ 醞釀向下"
                        detail_reason = f"【逼近超買】週線DIF下降且RSI達高檔 ({curr_rsi:.1f})，極度貪婪隨時面臨下修。"
                    elif weekly_dif_decreasing and curr_hist > 0 and curr_hist < prev_hist and curr_close < curr_ma5:
                        rec_text = "⚠️ 醞釀向下"
                        detail_reason = f"【動能衰退】MACD紅柱縮減且週線DIF下降，多方推升無力提防見頂。"
                    elif is_weekly_bottom_forming:
                        if is_daily_confirmed:
                            rec_text = "🌟 醞釀向上 (週大底+日發動)"
                            detail_reason = "【週線大底＋日線發動】週MACD綠柱收斂或站上5W均線，且日線已率先翻多轉強，大格局起跑第一獵物！"
                        else:
                            rec_text = "💡 醞釀向上 (週大底打底)"
                            detail_reason = "【週線大底即將完成】週MACD綠柱持續縮減或RSI低檔超賣，長線籌碼沉澱，適合左側分批布局！"

                if curr_close <= curr_lcl:
                    if curr_vol > curr_vol_ma5 * 2 and curr_rsi < 30:
                        rec_text = "🟢 逢低買入"
                        detail_reason = f"【SPC極端超跌】跌破LCL、爆出2倍均量且RSI超賣({curr_rsi:.1f})，籌碼換手醞釀強彈！"

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

@st.cache_data(ttl=86400)
def calculate_win_rate(ticker, name, interval):
    try:
        df = yf.download(ticker, period="1y", interval=interval, progress=False)
        if df.empty or len(df) < 35: return None
        
        df_w = yf.download(ticker, period="2y", interval="1wk", progress=False)
        
        close = df['Close'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['Close']
        high = df['High'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['High']
        low = df['Low'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['Low']
        volume = df['Volume'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['Volume']
        close, high, low, volume = close.dropna(), high.dropna(), low.dropna(), volume.dropna()
        
        close_w = df_w['Close'][ticker] if isinstance(df_w.columns, pd.MultiIndex) else df_w['Close']
        close_w = close_w.dropna()
        ma5_w, ma10_w = close_w.rolling(5).mean(), close_w.rolling(10).mean()
        ema12_w = close_w.ewm(span=12, adjust=False).mean()
        ema26_w = close_w.ewm(span=26, adjust=False).mean()
        dif_w = ema12_w - ema26_w
        hist_w = dif_w - dif_w.ewm(span=9, adjust=False).mean()
        wdif_dec = (dif_w < dif_w.shift(1)).astype(int)
        
        tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
        atr14 = tr.rolling(14).mean()
        atr_pct = (atr14 / close) * 100
        
        CASH_BOND_LIST = {"SGOV", "BIL", "SHV", "00719B.TW"}
        ETF_WHITE_LIST = {"0050.TW", "VOO", "QQQM", "SPY", "IVV", "0056.TW", "00878.TW", "00919.TW"}
        is_cash_bond = (ticker in CASH_BOND_LIST) or ("美債" in name and "0-3" in name) or ("超短債" in name)
        is_etf_or_index = (
            ticker in ETF_WHITE_LIST 
            or "ETF" in name.upper() 
            or "50" in name 
            or "指數" in name
        )
        
        if interval == '1d':
            wdif_dec_aligned = wdif_dec.reindex(close.index, method='ffill').fillna(0)
            w_ma5_aligned = ma5_w.reindex(close.index, method='ffill')
            w_ma10_aligned = ma10_w.reindex(close.index, method='ffill')
            w_hist_aligned = hist_w.reindex(close.index, method='ffill')
        
        ma5, ma10 = close.rolling(5).mean(), close.rolling(10).mean()
        vol_ma5 = volume.rolling(5).mean()
        ema12, ema26 = close.ewm(span=12, adjust=False).mean(), close.ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        hist = dif - dea 
        
        trades, wins = 0, 0
        holding = False
        buy_price = 0
        
        for i in range(20, len(close)):
            curr_close = close.iloc[i]
            curr_ma5, curr_ma10 = ma5.iloc[i], ma10.iloc[i]
            curr_hist = hist.iloc[i]
            curr_vol, curr_vol_ma5 = volume.iloc[i], vol_ma5.iloc[i]
            curr_atr_pct = atr_pct.iloc[i]
            
            target_position = (50 if curr_hist > 0 else 0) + (50 if curr_ma5 > curr_ma10 else 0)
            vol_condition = curr_vol > curr_vol_ma5
            
            if not holding and target_position == 100 and vol_condition:
                holding = True
                buy_price = curr_close
            elif holding:
                should_exit = False
                if is_cash_bond:
                    should_exit = False
                elif not is_etf_or_index and curr_atr_pct >= 3.5:
                    if interval == '1d':
                        should_exit = (w_hist_aligned.iloc[i] <= 0) and (w_ma5_aligned.iloc[i] < w_ma10_aligned.iloc[i])
                    else:
                        should_exit = (hist.iloc[i] <= 0) and (ma5.iloc[i] < ma10.iloc[i])
                else:
                    if interval == '1d':
                        should_exit = (target_position == 0) and bool(wdif_dec_aligned.iloc[i])
                    else:
                        should_exit = (target_position == 0) and (dif.iloc[i] < dif.iloc[i-1])
                        
                if should_exit:
                    holding = False
                    trades += 1
                    if curr_close > buy_price: wins += 1
                        
        win_rate = (wins / trades * 100) if trades > 0 else 0
        return {
            "代碼": ticker, 
            "名稱": name,
            "總交易次數": trades, 
            "獲利次數": wins, 
            "歷史勝率": f"{win_rate:.1f}%" if trades > 0 else "無交易紀錄"
        }
    except Exception:
        return None

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
# 分頁 1：主看盤儀表板 
# ==========================================
with tab_dashboard:
    col1, col2 = st.columns([1, 1])
    with col1:
        st.title("📈 雙指標波段系統")
    with col2:
        timeframe_option = st.radio(
            "請選擇分析週期：", 
            ["週線 (Weekly)", "日線 (Daily)"], 
            index=1,
            horizontal=True
        )

    if timeframe_option == "週線 (Weekly)":
        tf_interval = "1wk"
        tf_period = "2y"
        ma_s_lbl = "5W"
        ma_l_lbl = "10W"
    else:
        tf_interval = "1d"
        tf_period = "1y"
        ma_s_lbl = "5D"
        ma_l_lbl = "10D"

    # 總體資金水位儀表板 
    market_ticker = st.text_input("📊 設定總體資金水位參考標的 (預設 0050.TW)：", key="market_ticker_input", on_change=update_other_inputs).strip().upper()
    with st.spinner(f"運算 {market_ticker} 總體指標中..."):
        market_trend = get_market_trend(market_ticker, tf_interval, tf_period)
        if market_trend:
            st.markdown(
                f'''
                <div style="background-color: {market_trend['color']}; padding: 15px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #ccc;">
                    <h4 style="margin: 0; color: #333;">🧭 總體資金水位儀表板 ({market_ticker} {timeframe_option})</h4>
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
        with st.spinner(f"正在分析 {temp_ticker}..."):
            temp_df = analyze_signals(tf_interval, tf_period, ma_s_lbl, ma_l_lbl, temp_dict)
            
        if not temp_df.empty and "⚠️ 無資料" not in temp_df.iloc[0]['收盤價(漲跌)']:
            st.dataframe(
                style_dataframe(temp_df.drop(columns=['股性類別'])), 
                use_container_width=True,
                column_config={"Yahoo股市": st.column_config.LinkColumn("🔗 Yahoo股市", display_text="點擊前往")}
            )
            with col_temp3:
                st.write("") 
                st.write("")
                if st.button("➕ 加入自選股"):
                    if temp_ticker not in st.session_state.watchlist_text:
                        st.session_state.watchlist_text += f"\n{temp_ticker},{disp_name}"
                        st.rerun()
                    else:
                        st.warning("此標的已在您的自選股清單中。")
        else:
            st.error("無法取得該代碼資料，請確認代碼是否正確。")
    st.divider()
    
    # 主要分析運算
    display_df = analyze_signals(tf_interval, tf_period, ma_s_lbl, ma_l_lbl, WATCHLIST)

    if not display_df.empty:
        st.subheader(f"📊 自選股狀態總覽 ({timeframe_option})")
        
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

        # ==========================================
        # 依股性分區塊獨立呈現 (穩健型 vs 高動能型)
        # ==========================================
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
        
        buy_df = display_df[display_df['建議'].str.contains("買入", na=False)]
        with st.expander("📊 計算『買入』標的歷史勝率 (近一年回測 - 含股性自適應出場)"):
            if st.button("🚀 執行歷史回測"):
                if buy_df.empty:
                    st.warning("目前沒有處於買入狀態的標的，無法進行回測。")
                else:
                    with st.spinner("正在進行歷史交易模擬回測..."):
                        backtest_results = []
                        for _, row in buy_df.iterrows():
                            res = calculate_win_rate(row['代碼'], row['名稱'], tf_interval)
                            if res: backtest_results.append(res)
                        
                        if backtest_results:
                            st.dataframe(pd.DataFrame(backtest_results), use_container_width=True)
                            st.caption("※ 回測邏輯：動能型標的依週線雙死叉出場；穩健型依日線敏捷出場。")
                        else:
                            st.error("無法取得回測資料。")

    # --- 互動 K 線圖區塊 ---
    st.divider()
    st.subheader("📉 價量與指標複合分析圖")

    chart_options_dict = WATCHLIST.copy()
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
            chart_df = get_chart_data(selected_ticker, tf_interval, "5y")
            
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
                if tf_interval == "1wk":
                    start_date = end_date - pd.DateOffset(years=1)
                else:
                    start_date = end_date - pd.DateOffset(months=3)

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
                            dict(count=5, label="5Y", step="year", stepmode="backward"),
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
                    legend=dict(
                        orientation="h", 
                        yanchor="top", 
                        y=-0.1,  
                        xanchor="center", 
                        x=0.5
                    ), 
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
    st.subheader(f"⚔️ 買賣戰情室 ({timeframe_option})")
    
    if display_df.empty:
        st.warning("⚠️ 自選股清單目前為空，請從『⚙️ 自選股編輯』分頁加入股票。")
    else:
        df_up = display_df[display_df['建議'].str.contains("醞釀向上", na=False)].reset_index(drop=True)
        df_buy = display_df[display_df['建議'].str.contains("買入", na=False)].reset_index(drop=True)
        
        df_bottom = display_df[display_df['建議'].str.contains("打底", na=False)].reset_index(drop=True)
        df_take_profit = display_df[display_df['建議'].str.contains("分批停利", na=False)].reset_index(drop=True)
        df_down = display_df[display_df['建議'].str.contains("醞釀向下", na=False)].reset_index(drop=True)
        df_trim = display_df[display_df['建議'].str.contains("減碼", na=False)].reset_index(drop=True)
        df_sell = display_df[display_df['建議'].str.contains("賣出", na=False)].reset_index(drop=True)
        df_hold = display_df[display_df['建議'].str.contains("避免殺低", na=False)].reset_index(drop=True)
        
        st.markdown(f"#### 第一步（找獵物）：💡 醞釀向上 ({len(df_up)})  [週線大底即將完成優先]")
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
