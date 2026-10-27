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
    st.header("📖 雙指標波段系統 - 判斷原則")
    st.markdown("""
    本系統專注於「順勢波段做多」與「極端超跌抄底」，排除做空邏輯，穩健累積資產。
    
    ### 🟢 買入標準 (滿足其一即為買點)
    1. **順勢共振買點 (長短線雙多)**：週線 MACD>0 且 5W>10W；日線 MACD>0 且 5MA>10MA，當日成交量 > 5日均量。
    2. **逆勢超跌買點 (爆量 + RSI 雙濾網)**：跌破 LCL (20MA-2σ)，成交量大於 5日均量 2 倍，且 RSI(14) < 30。

    ### 💡 雙向預警雷達 (提早抓轉折)
    - **💡 醞釀向上 (主力打底區)**：MACD 綠柱縮減且股價站上 5MA；或 RSI(14) ≤ 35。強烈建議列入買進觀察清單。
    - **⚠️ 醞釀向下 (提防見頂)**：(需滿足 **週線 DIF 下降** 前提) MACD 紅柱縮減且股價跌破 5MA；或 RSI(14) ≥ 70。

    ---

    ### 🔴 賣出防守與「避免殺低」原則
    - **賣出前提**：當週 MACD 的 DIF 值 < 前一週 DIF 值 (代表長線動能確實衰退)。
    - 若滿足賣出前提，且發生日線死叉，系統會建議「🔴 賣出」。
    - **🟡 避免殺低防護網 (極重要)**：若已滿足賣出條件，但股價**已跌破 LCL 下軌** 或 **RSI(14) ≤ 30**，代表短線乖離過大。此時系統會強制攔截賣出訊號，改為提示**「🟡 避免殺低」**，並自動為您計算第一階段反彈壓力位 (10MA)，提醒您等待技術性反彈再現再行處理。
    """)

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
        for ticker, name in watchlist.items():
            try:
                df = yf.download(ticker, period=period, interval=interval, progress=False)
                if df.empty or len(df) < 35:
                    results.append({
                        "代碼": ticker, "名稱": name, "收盤價(漲跌)": "⚠️ 無資料",
                        "建議": "⚪ 未知", "最新動態": "-",
                        "詳細判定原因": "無足夠 K 線資料，請檢查代碼格式",
                        "Yahoo股市": f"https://finance.yahoo.com/quote/{ticker}"
                    })
                    continue
                
                close = df['Close'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['Close']
                volume = df['Volume'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['Volume']
                close = close.dropna()
                volume = volume.dropna()
                
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
                
                curr_close, prev_close = close.iloc[-1], close.iloc[-2]
                curr_ma5, curr_ma10 = ma5.iloc[-1], ma10.iloc[-1]
                curr_ma20, prev_ma20 = ma20.iloc[-1], ma20.iloc[-2]
                curr_hist = hist.iloc[-1]
                prev_hist = hist.iloc[-2]
                curr_vol, curr_vol_ma5 = volume.iloc[-1], vol_ma5.iloc[-1]
                curr_dif = dif.iloc[-1]
                prev_dif = dif.iloc[-2]
                
                weekly_dif_decreasing = False
                curr_dif_w_val = 0.0
                prev_dif_w_val = 0.0
                
                if interval == "1wk":
                    weekly_dif_decreasing = curr_dif < prev_dif
                    curr_dif_w_val = curr_dif
                    prev_dif_w_val = prev_dif

                std20 = close.rolling(20).std()
                ucl = ma20 + 2 * std20
                lcl = ma20 - 2 * std20
                curr_ucl = ucl.iloc[-1]
                curr_lcl = lcl.iloc[-1]

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
                
                is_weekly_bullish = True
                weekly_status = ""
                daily_status = ""
                
                if interval == "1d":
                    df_w = yf.download(ticker, period="2y", interval="1wk", progress=False)
                    if not df_w.empty and len(df_w) >= 35:
                        close_w = df_w['Close'][ticker] if isinstance(df_w.columns, pd.MultiIndex) else df_w['Close']
                        close_w = close_w.dropna()
                        ma5_w, ma10_w = close_w.rolling(5).mean(), close_w.rolling(10).mean()
                        ema12_w = close_w.ewm(span=12, adjust=False).mean()
                        ema26_w = close_w.ewm(span=26, adjust=False).mean()
                        dif_w = ema12_w - ema26_w
                        hist_w = dif_w - dif_w.ewm(span=9, adjust=False).mean()
                        
                        if len(dif_w) >= 2:
                            curr_dif_w_val = dif_w.iloc[-1]
                            prev_dif_w_val = dif_w.iloc[-2]
                            weekly_dif_decreasing = curr_dif_w_val < prev_dif_w_val
                        
                        if hist_w.iloc[-1] > 0 and ma5_w.iloc[-1] > ma10_w.iloc[-1]:
                            is_weekly_bullish = True
                            weekly_status = "週線長多"
                        else:
                            is_weekly_bullish = False
                            weekly_status = "週線偏空"
                            
                elif interval == "1wk":
                    df_d = yf.download(ticker, period="1y", interval="1d", progress=False)
                    if not df_d.empty and len(df_d) >= 35:
                        close_d = df_d['Close'][ticker] if isinstance(df_d.columns, pd.MultiIndex) else df_d['Close']
                        vol_d = df_d['Volume'][ticker] if isinstance(df_d.columns, pd.MultiIndex) else df_d['Volume']
                        close_d, vol_d = close_d.dropna(), vol_d.dropna()
                        
                        ma5_d, ma10_d = close_d.rolling(5).mean(), close_d.rolling(10).mean()
                        vol_ma5_d = vol_d.rolling(5).mean()
                        ema12_d = close_d.ewm(span=12, adjust=False).mean()
                        ema26_d = close_d.ewm(span=26, adjust=False).mean()
                        hist_d = (ema12_d - ema26_d) - (ema12_d - ema26_d).ewm(span=9, adjust=False).mean()
                        
                        curr_hist_d = hist_d.iloc[-1]
                        curr_ma5_d, curr_ma10_d = ma5_d.iloc[-1], ma10_d.iloc[-1]
                        
                        if curr_hist_d > 0 and curr_ma5_d > curr_ma10_d:
                            if vol_d.iloc[-1] > vol_ma5_d.iloc[-1]:
                                daily_status = "🟢日線帶量買入"
                            else:
                                daily_status = "🟡日線量縮觀察"
                        elif curr_hist_d <= 0 and curr_ma5_d <= curr_ma10_d:
                            daily_status = "🔴日線雙空賣出"
                        else:
                            daily_status = "🟡日線方向分歧"

                # 基礎判定 
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
                    if weekly_dif_decreasing:
                        if curr_rsi <= 30 or curr_close <= curr_lcl:
                            rec_text = "🟡 避免殺低"
                            detail_reason = f"【乖離過大】雖週線DIF下降且已破線，但股價跌破LCL或RSI極度超賣({curr_rsi:.1f})，切勿恐慌殺低。 👉 預估初步反彈壓力：{ma_l_label} (約 {curr_ma10:.2f})"
                        else:
                            rec_text = "🔴 賣出"
                            detail_reason = f"【雙空頭】週線DIF下降(由 {prev_dif_w_val:.2f} 降至 {curr_dif_w_val:.2f})且 {macd_text} 且 {ma_text}，建議出場。"
                    else:
                        rec_text = "🟡 觀察"
                        detail_reason = f"【防守延遲】{macd_text} 且 {ma_text}，但週線DIF仍上升，暫緩賣出。"
                else:
                    rec_text = "🟡 觀察"
                    if not weekly_dif_decreasing and curr_hist < 0:
                        detail_reason = f"【方向分歧】指標偏空，但週線DIF仍上升，暫緩防守。"
                    else:
                        detail_reason = f"【方向分歧】{macd_text} 但 {ma_text}，指標未同步。"

                # 雙向預警雷達
                if "買入" not in rec_text and "賣出" not in rec_text and "殺低" not in rec_text:
                    if weekly_dif_decreasing and curr_rsi >= 70:
                        rec_text = "⚠️ 醞釀向下"
                        detail_reason = f"【逼近超買】週線DIF下降(由 {prev_dif_w_val:.2f} 降至 {curr_dif_w_val:.2f})且RSI達高檔 ({curr_rsi:.1f})，極度貪婪隨時面臨下修。"
                    elif weekly_dif_decreasing and curr_hist > 0 and curr_hist < prev_hist and curr_close < curr_ma5:
                        rec_text = "⚠️ 醞釀向下"
                        detail_reason = f"【動能衰退】MACD紅柱縮減且週線DIF下降(由 {prev_dif_w_val:.2f} 降至 {curr_dif_w_val:.2f})，多方推升無力提防見頂。"
                    elif curr_rsi <= 35:
                        rec_text = "💡 醞釀向上"
                        detail_reason = f"【逼近超賣】RSI降至低檔 ({curr_rsi:.1f})，隨時可能觸發技術性反彈。"
                    elif curr_hist < 0 and curr_hist > prev_hist and curr_close > curr_ma5:
                        rec_text = "💡 醞釀向上"
                        detail_reason = f"【動能收斂】MACD綠柱縮減且站上5MA，空方力竭準備打底。"

                # 追蹤附帶說明
                if interval == "1wk" and daily_status and "觀察" not in rec_text and "醞釀" not in rec_text and "殺低" not in rec_text:
                    if "買入" in daily_status:
                        detail_reason += f" 👉 找買點：{daily_status}"
                    elif "賣出" in daily_status:
                        detail_reason += f" 👉 找賣點：{daily_status}"
                    else:
                        detail_reason += f" 👉 短線動態：{daily_status}"

                # SPC 爆量止跌 + RSI 雙重防護邏輯
                if curr_close <= curr_lcl:
                    if curr_vol > curr_vol_ma5 * 2 and curr_rsi < 30:
                        rec_text = "🟢 逢低買入"
                        detail_reason = f"【SPC極端超跌】跌破LCL、爆出2倍均量且RSI超賣({curr_rsi:.1f})，籌碼換手醞釀強彈！"
                    elif curr_vol > curr_vol_ma5 * 2:
                        detail_reason += f" ⚠️ SPC警示：跌破LCL且爆量，但RSI未達超賣({curr_rsi:.1f})，動能尚未完全竭盡"
                    else:
                        detail_reason += f" ⚠️ SPC警示：跌破LCL下軌，無爆量承接 (RSI:{curr_rsi:.1f})，提防陰跌探底"
                elif curr_close >= curr_ucl:
                    if weekly_dif_decreasing:
                        detail_reason += f" ⚠️ SPC警示：突破UCL上軌且週線DIF下降(由 {prev_dif_w_val:.2f} 降至 {curr_dif_w_val:.2f})，極端超漲提防拉回 (RSI:{curr_rsi:.1f})"
                    else:
                        detail_reason += f" ⚠️ SPC警示：突破UCL上軌，但週線DIF仍上升，動能延續中 (RSI:{curr_rsi:.1f})"

                results.append({
                    "代碼": ticker, 
                    "名稱": name, 
                    "收盤價(漲跌)": price_display,
                    "建議": rec_text,
                    "最新動態": " / ".join(actions) if actions else "-",
                    "詳細判定原因": detail_reason,
                    "Yahoo股市": f"https://finance.yahoo.com/quote/{ticker}"
                })
            except Exception: 
                results.append({
                    "代碼": ticker, "名稱": name, "收盤價(漲跌)": "⚠️ 錯誤",
                    "建議": "⚪ 未知", "最新動態": "-",
                    "詳細判定原因": "抓取過程發生異常，請稍後刷新",
                    "Yahoo股市": f"https://finance.yahoo.com/quote/{ticker}"
                })
                continue
            
        display_df = pd.DataFrame(results)
        if not display_df.empty:
            def get_sort_rank(row):
                if "買入" in row['建議']: return 1  
                elif "醞釀向上" in row['建議']: return 2
                elif "醞釀向下" in row['建議']: return 3
                elif "避免殺低" in row['建議']: return 4 
                elif "觀察" in row['建議']: return 5
                elif "🔴 賣出" in row['建議']: return 6
                else: return 7
            display_df['SortRank'] = display_df.apply(get_sort_rank, axis=1)
            display_df = display_df.sort_values(by=['SortRank', '代碼']).drop(columns=['SortRank']).reset_index(drop=True)
            
        return display_df

    @st.cache_data(ttl=86400)
    def calculate_win_rate(ticker, name, interval):
        try:
            df = yf.download(ticker, period="1y", interval=interval, progress=False)
            if df.empty or len(df) < 35: return None
            
            df_w = yf.download(ticker, period="2y", interval="1wk", progress=False)
            
            close = df['Close'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['Close']
            volume = df['Volume'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['Volume']
            close = close.dropna()
            volume = volume.dropna()
            
            close_w = df_w['Close'][ticker] if isinstance(df_w.columns, pd.MultiIndex) else df_w['Close']
            close_w = close_w.dropna()
            ema12_w = close_w.ewm(span=12, adjust=False).mean()
            ema26_w = close_w.ewm(span=26, adjust=False).mean()
            dif_w = ema12_w - ema26_w
            wdif_dec = (dif_w < dif_w.shift(1)).astype(int)
            
            if interval == '1d':
                wdif_dec_daily = wdif_dec.reindex(close.index, method='ffill').fillna(0)
            
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
                
                if interval == '1d':
                    weekly_dif_decreasing = bool(wdif_dec_daily.iloc[i])
                else:
                    weekly_dif_decreasing = dif.iloc[i] < dif.iloc[i-1]
                    
                vol_condition = curr_vol > curr_vol_ma5
                target_position = (50 if curr_hist > 0 else 0) + (50 if curr_ma5 > curr_ma10 else 0)
                
                if not holding and target_position == 100 and vol_condition:
                    holding = True
                    buy_price = curr_close
                elif holding and target_position == 0 and weekly_dif_decreasing:
                    holding = False
                    trades += 1
                    if curr_close > buy_price:
                        wins += 1
                        
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
        if hasattr(df.style, "map"): return df.style.map(color_trend, subset=['收盤價(漲跌)'])
        else: return df.style.applymap(color_trend, subset=['收盤價(漲跌)'])

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

    # --- 儀表板 UI 渲染區塊 ---
    if st.button("🔄 手動強制刷新 (重置快取)"):
        st.cache_data.clear()

    # ⭐️ 補回漏掉的總體資金水位儀表板
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

    # ⭐️ 補回漏掉的臨時標的快速分析
    st.divider()
    st.subheader("🔍 臨時標的快速分析")
    col_t1, col_t2, col_t3 = st.columns([2, 2, 2])
    with col_t1:
        st.text_input("輸入代碼 (例：2317.TW)", key="search_ticker", on_change=update_selected_from_search)
    with col_t2:
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
                style_dataframe(temp_df), 
                use_container_width=True,
                column_config={"Yahoo股市": st.column_config.LinkColumn("🔗 Yahoo股市", display_text="點擊前往")}
            )
            with col_t3:
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

    display_df = analyze_signals(tf_interval, tf_period, ma_s_lbl, ma_l_lbl, WATCHLIST)
    
    if not display_df.empty:
        # ⭐️ 提取買賣區的股票並實裝紅框總結清單
        df_buy_zone = display_df[display_df['建議'].str.contains("買入|醞釀向上", na=False)]
        df_sell_zone = display_df[display_df['建議'].str.contains("賣出|醞釀向下|避免殺低", na=False)]
        
        buy_list_str = ", ".join(df_buy_zone['代碼'].tolist()) if not df_buy_zone.empty else "無"
        sell_list_str = ", ".join(df_sell_zone['代碼'].tolist()) if not df_sell_zone.empty else "無"
        
        st.markdown(
            f'''
            <div style="padding: 10px; border-radius: 5px; background-color: #f9f9f9; border: 1px solid #ddd; margin-bottom: 20px;">
                <span style="color: #2e7d32; font-weight: bold; font-size: 16px;">🟢 買入戰情室：</span> <span style="font-size: 15px;">{buy_list_str}</span> <br><br>
                <span style="color: #c62828; font-weight: bold; font-size: 16px;">🔴 賣出防守線：</span> <span style="font-size: 15px;">{sell_list_str}</span>
            </div>
            ''', 
            unsafe_allow_html=True
        )

        st.subheader(f"📊 自選股狀態總覽 ({timeframe_option})")
        
        # ⭐️ 還原原本的過濾按鈕與表格
        filter_opt = st.radio(
            "🔍 快速篩選：", 
            ["👀 顯示全部", "🟢 只看買入", "💡 醞釀向上", "⚠️ 醞釀向下", "🟡 避免殺低", "🔴 只看賣出", "⚡ 剛發生交叉"], 
            index=0,
            horizontal=True
        )
        
        filtered_df = display_df.copy()
        if filter_opt == "🟢 只看買入":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("買入", na=False)]
        elif filter_opt == "💡 醞釀向上":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("醞釀向上", na=False)]
        elif filter_opt == "⚠️ 醞釀向下":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("醞釀向下", na=False)]
        elif filter_opt == "🟡 避免殺低":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("避免殺低", na=False)]
        elif filter_opt == "🔴 只看賣出":
            filtered_df = filtered_df[filtered_df['建議'].str.contains("賣出", na=False)]
        elif filter_opt == "⚡ 剛發生交叉":
            filtered_df = filtered_df[filtered_df['最新動態'] != "-"]

        if filtered_df.empty: 
            st.info("目前無符合篩選條件的標的。")
        else: 
            display_event = st.dataframe(
                style_dataframe(filtered_df), 
                use_container_width=True,
                on_select="rerun",          
                selection_mode="single-row",
                column_config={"Yahoo股市": st.column_config.LinkColumn("🔗 Yahoo股市", display_text="點擊前往")}
            )
            if display_event.selection.rows:
                selected_row_idx = display_event.selection.rows[0]
                st.session_state.selected_ticker = filtered_df.iloc[selected_row_idx]['代碼']
        
        buy_df = display_df[display_df['建議'].str.contains("買入", na=False)]
        with st.expander("📊 計算『買入』標的歷史勝率 (近一年回測)"):
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
                            st.caption("※ 回測邏輯：過去一年內，當均線與MACD雙多頭且帶量時買進；雙空頭且週線DIF下彎時賣出。")
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
# 分頁 4：買賣戰情室 (獨立頁面)
# ==========================================
with tab_war_room:
    st.subheader(f"⚔️ 買賣戰情室 ({timeframe_option})")
    
    if display_df.empty:
        st.warning("⚠️ 自選股清單目前為空，請從『⚙️ 自選股編輯』分頁加入股票。")
    else:
        df_up = display_df[display_df['建議'].str.contains("醞釀向上", na=False)].reset_index(drop=True)
        df_buy = display_df[display_df['建議'].str.contains("買入", na=False)].reset_index(drop=True)
        
        df_down = display_df[display_df['建議'].str.contains("醞釀向下", na=False)].reset_index(drop=True)
        df_sell = display_df[display_df['建議'].str.contains("賣出", na=False)].reset_index(drop=True)
        df_hold = display_df[display_df['建議'].str.contains("避免殺低", na=False)].reset_index(drop=True)
        
        count_buy_zone = len(df_up) + len(df_buy)
        count_sell_zone = len(df_down) + len(df_sell) + len(df_hold)
        
        sub_tab_buy, sub_tab_sell = st.tabs([f"🟢 買入戰情室 ({count_buy_zone})", f"🔴 賣出防守線 ({count_sell_zone})"])
        
        with sub_tab_buy:
            st.markdown(f"#### 第一步（找獵物）：💡 醞釀向上 ({len(df_up)})")
            if df_up.empty:
                st.info("目前無『醞釀向上』標的。")
            else:
                ev_up = st.dataframe(
                    style_dataframe(df_up), use_container_width=True, 
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
                    style_dataframe(df_buy), use_container_width=True, 
                    on_select="rerun", selection_mode="single-row", key="war_buy",
                    column_config={"Yahoo股市": st.column_config.LinkColumn("🔗 Yahoo股市", display_text="點擊前往")}
                )
                if ev_buy.selection.rows:
                    st.session_state.selected_ticker = df_buy.iloc[ev_buy.selection.rows[0]]['代碼']

        with sub_tab_sell:
            st.markdown(f"#### 第一步（提防見頂）：⚠️ 醞釀向下 ({len(df_down)})")
            if df_down.empty:
                st.info("目前無『醞釀向下』標的。")
            else:
                ev_down = st.dataframe(
                    style_dataframe(df_down), use_container_width=True, 
                    on_select="rerun", selection_mode="single-row", key="war_down",
                    column_config={"Yahoo股市": st.column_config.LinkColumn("🔗 Yahoo股市", display_text="點擊前往")}
                )
                if ev_down.selection.rows:
                    st.session_state.selected_ticker = df_down.iloc[ev_down.selection.rows[0]]['代碼']

            st.markdown(f"#### 第二步（紀律出場）：🔴 只看賣出 ({len(df_sell)})")
            if df_sell.empty:
                st.info("目前無『賣出』標的。")
            else:
                ev_sell = st.dataframe(
                    style_dataframe(df_sell), use_container_width=True, 
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
                    style_dataframe(df_hold), use_container_width=True, 
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
