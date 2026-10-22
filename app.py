import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="雙指標波段系統", page_icon="📈", layout="wide")

# 自動重整機制：每 5 分鐘 (300,000 毫秒) 自動重新載入網頁
st_autorefresh(interval=5 * 60 * 1000, key="auto_refresh")

# ⭐️ 初始化 Session State 與自動連動函式
if 'selected_ticker' not in st.session_state:
    st.session_state.selected_ticker = None

def update_selected_from_search():
    """當搜尋框內容改變時，自動將 K 線圖切換至搜尋標的"""
    val = st.session_state.search_ticker.strip().upper()
    if val:
        st.session_state.selected_ticker = val

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

# 建立手機友善的頂部分頁
tab_dashboard, tab_rules, tab_settings = st.tabs(["📊 看盤儀表板", "📖 策略判斷原則", "⚙️ 自選股編輯"])

# ==========================================
# 分頁 3：自選股編輯頁面
# ==========================================
with tab_settings:
    st.subheader("⚙️ 編輯自選股清單")
    st.markdown("請依照 `代碼,名稱` 的格式輸入，每行一檔標的。修改後會自動儲存並套用至儀表板。")
    st.markdown("💡 **提示：** 港股代碼若無法抓取，請嘗試去掉前面的 0（例如：將 `02342.HK` 改為 `2342.HK`）。")
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
    本系統以 **「週線級別的買入訊號」** 作為核心標準與操作前提，徹底貫徹 **「長線保護短線」** 的交易紀律。
    
    ### 🎯 核心精神：週線決定方向，日線尋找買點
    必須在「週線大趨勢偏多」的保護傘下，才能在「日線」尋找切入發動點。嚴格禁止在週線空頭趨勢中搶買日線的反彈。

    ---

    ### 🟢 買入標準 (必須同時滿足)
    1. **大趨勢保護 (週線條件 - 先決標準)**：
       - **週線 MACD > 0**：柱狀圖位於零軸之上，屬於長線多頭格局。
       - **週線 5MA > 10MA**：短期均線大於長期均線。
    2. **精準發動點 (日線條件)**：
       - **日線 MACD > 0**：短線動能翻多。
       - **日線 5MA > 10MA**：短線均線黃金交叉。
       - **帶量上攻**：當日成交量必須 **大於 5日均量**，確認有主力資金點火。
    
    👉 *當以上條件完全符合時，系統會判定為「🟢 買入 (長短線共振)」。*

    ---

    ### 🔴 賣出與防守標準 (滿足其一即應警戒)
    1. **動能轉弱 (MACD 死叉)**：日線 MACD 柱狀圖由紅翻綠 (MACD < 0)。
    2. **趨勢跌破 (均線死叉)**：日線 5MA 跌破 10MA。
    3. **生命線跌破 (破月線)**：日線收盤價跌穿 20MA (月線)，視為波段防守線失守。

    👉 *當日線出現雙空頭 (MACD < 0 且 5MA < 10MA) 時，系統會直接判定為「🔴 賣出」，建議迅速收回資金。*

    ---

    ### 🟡 觀察狀態 (不動作)
    - **量能不足**：日線雖然均線與MACD雙多頭，但當日成交量小於5日均量，視為無量虛漲。
    - **短多長空**：日線呈現多頭，但「週線」處於偏空狀態。這屬於下跌趨勢中的「反彈」，系統會強制降級為觀察，不建議進場。
    - **方向分歧**：均線與 MACD 其中一個多頭、另一個空頭，指標未完全同步。
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

    # --- 大盤(0050) 多空環境燈號分析 ---
    @st.cache_data(ttl=300)
    def get_market_trend(interval, period):
        try:
            df = yf.download("0050.TW", period=period, interval=interval, progress=False)
            if df.empty: return None
            
            close = df['Close']["0050.TW"] if isinstance(df.columns, pd.MultiIndex) else df['Close']
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

    # 1. 運算所有自選股最新訊號
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
                        "詳細判定原因": "無足夠 K 線資料，請檢查代碼格式 (如港股請去 0)"
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
                
                curr_close, prev_close = close.iloc[-1], close.iloc[-2]
                curr_ma5, curr_ma10 = ma5.iloc[-1], ma10.iloc[-1]
                curr_ma20, prev_ma20 = ma20.iloc[-1], ma20.iloc[-2]
                curr_hist = hist.iloc[-1]
                curr_vol, curr_vol_ma5 = volume.iloc[-1], vol_ma5.iloc[-1]
                
                vol_condition = curr_vol > curr_vol_ma5  
                
                change_pct = ((curr_close - prev_close) / prev_close) * 100
                if change_pct > 0: price_display = f"🔺 {curr_close:.2f} (+{change_pct:.2f}%)"
                elif change_pct < 0: price_display = f"🔻 {curr_close:.2f} ({change_pct:.2f}%)"
                else: price_display = f"➖ {curr_close:.2f} (0.00%)"
                
                actions = []
                if interval == "1d" and prev_close <= prev_ma20 and curr_close > curr_ma20:
                    actions.append("日線突破20MA")
                if hist.iloc[-2] <= 0 and curr_hist > 0:
                    actions.append("MACD剛金叉")
                elif hist.iloc[-2] >= 0 and curr_hist < 0:
                    actions.append("MACD剛死叉")
                if ma5.iloc[-2] <= ma10.iloc[-2] and curr_ma5 > curr_ma10:
                    actions.append("MA剛金叉")
                elif ma5.iloc[-2] >= ma10.iloc[-2] and curr_ma5 < curr_ma10:
                    actions.append("MA剛死叉")
                    
                target_position = (50 if curr_hist > 0 else 0) + (50 if curr_ma5 > curr_ma10 else 0)
                macd_text = "MACD>0" if curr_hist > 0 else "MACD<0"
                ma_text = f"{ma_s_label}>{ma_l_label}" if curr_ma5 > curr_ma10 else f"{ma_s_label}<{ma_l_label}"
                
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
                        hist_w = (ema12_w - ema26_w) - (ema12_w - ema26_w).ewm(span=9, adjust=False).mean()
                        
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

                # 依據雙週期邏輯給出最終建議
                if target_position == 100:
                    if vol_condition:
                        if interval == "1d" and not is_weekly_bullish:
                            rec_text = "🟡 觀察"
                            detail_reason = f"【短多長空】日線翻多帶量，但{weekly_status}，視為反彈暫不進場"
                        else:
                            rec_text = "🟢 買入"
                            resonance_text = " (長短線共振)" if interval == "1d" else ""
                            detail_reason = f"【雙多頭+帶量】{macd_text} 且 {ma_text}，量>{ma_s_label}均量{resonance_text}"
                    else:
                        rec_text = "🟡 觀察"
                        detail_reason = f"【量能不足】{macd_text} 且 {ma_text}，但量縮觀望"
                elif target_position == 0:
                    rec_text = "🔴 賣出"
                    detail_reason = f"【雙空頭】{macd_text} 且 {ma_text}，建議出場"
                else:
                    rec_text = "🟡 觀察"
                    detail_reason = f"【方向分歧】{macd_text} 但 {ma_text}，指標未同步"

                if interval == "1wk" and daily_status and "觀察" not in rec_text:
                    if "買入" in daily_status:
                        detail_reason += f" 👉 找買點：{daily_status}"
                    elif "賣出" in daily_status:
                        detail_reason += f" 👉 找賣點：{daily_status}"
                    else:
                        detail_reason += f" 👉 短線動態：{daily_status}"

                results.append({
                    "代碼": ticker, 
                    "名稱": name, 
                    "收盤價(漲跌)": price_display,
                    "建議": rec_text,
                    "最新動態": " / ".join(actions) if actions else "-",
                    "詳細判定原因": detail_reason
                })
            except Exception: 
                results.append({
                    "代碼": ticker, "名稱": name, "收盤價(漲跌)": "⚠️ 錯誤",
                    "建議": "⚪ 未知", "最新動態": "-",
                    "詳細判定原因": "抓取過程發生異常，請稍後刷新"
                })
                continue
            
        df_results = pd.DataFrame(results)
        if not df_results.empty:
            def get_sort_rank(row):
                if "🟢 買入" in row['建議']: return 1
                elif "🔴 賣出" in row['建議']: return 2
                elif "🟡 觀察" in row['建議']: return 3
                else: return 4
            df_results['SortRank'] = df_results.apply(get_sort_rank, axis=1)
            df_results = df_results.sort_values(by=['SortRank', '代碼']).drop(columns=['SortRank']).reset_index(drop=True)
            
        return df_results

    # 策略歷史回測引擎
    @st.cache_data(ttl=86400)
    def calculate_win_rate(ticker, name, interval):
        try:
            df = yf.download(ticker, period="1y", interval=interval, progress=False)
            if df.empty or len(df) < 35: return None
            
            close = df['Close'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['Close']
            volume = df['Volume'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['Volume']
            close = close.dropna()
            volume = volume.dropna()
            
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
                
                vol_condition = curr_vol > curr_vol_ma5
                target_position = (50 if curr_hist > 0 else 0) + (50 if curr_ma5 > curr_ma10 else 0)
                
                if not holding and target_position == 100 and vol_condition:
                    holding = True
                    buy_price = curr_close
                elif holding and target_position == 0:
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

    # 抓取單一股票完整數據畫圖用
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
        
        df['DIF'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
        df['DEA'] = df['DIF'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['DIF'] - df['DEA']
        df['MACD_Color'] = ['#ef5350' if val > 0 else '#26a69a' for val in df['MACD_Hist']]
        
        df['Candle_Dir'] = df['Close'] >= df['Open']
        df['Vol_Color'] = ['#ef5350' if d else '#26a69a' for d in df['Candle_Dir']]
        return df

    # --- 儀表板 UI 渲染區塊 ---
    if st.button("🔄 手動強制刷新 (重置快取)"):
        st.cache_data.clear()

    with st.spinner("運算技術指標與量能中..."):
        market_trend = get_market_trend(tf_interval, tf_period)
        if market_trend:
            st.markdown(
                f'''
                <div style="background-color: {market_trend['color']}; padding: 15px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #ccc;">
                    <h4 style="margin: 0; color: #333;">🧭 總體資金水位儀表板 (0050 {timeframe_option})</h4>
                    <p style="margin: 5px 0 0 0; font-size: 18px; font-weight: bold; color: #333;">狀態：{market_trend['status']}</p>
                    <p style="margin: 5px 0 0 0; color: #555;">💡 建議：{market_trend['advice']}</p>
                </div>
                ''', unsafe_allow_html=True
            )

        st.divider()
        st.subheader("🔍 臨時標的快速分析")
        col_t1, col_t2, col_t3 = st.columns([2, 2, 2])
        with col_t1:
            st.text_input("輸入代碼 (例：2317.TW)", key="search_ticker", on_change=update_selected_from_search)
        with col_t2:
            st.text_input("輸入名稱 (選填，例：鴻海)", key="search_name")

        temp_ticker = st.session_state.search_ticker.strip().upper()
        temp_name = st.session_state.search_name.strip()

        if temp_ticker:
            disp_name = temp_name if temp_name else temp_ticker
            temp_dict = {temp_ticker: disp_name}
            with st.spinner(f"正在分析 {temp_ticker}..."):
                temp_df = analyze_signals(tf_interval, tf_period, ma_s_lbl, ma_l_lbl, temp_dict)
                
            if not temp_df.empty and "⚠️ 無資料" not in temp_df.iloc[0]['收盤價(漲跌)']:
                st.dataframe(style_dataframe(temp_df), use_container_width=True)
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
                st.error("無法取得該代碼資料，請確認代碼是否正確（美股 AAPL，台股 2317.TW，港股去零 700.HK）。")
        st.divider()

        display_df = analyze_signals(tf_interval, tf_period, ma_s_lbl, ma_l_lbl, WATCHLIST)
        
        if not display_df.empty:
            st.subheader(f"📊 自選股狀態總覽 ({timeframe_option})")
            
            # ⭐️ 這裡將預設 index 改為 1 (預設選取 "🟢 只看買入")
            filter_opt = st.radio(
                "🔍 快速篩選：", 
                ["👀 顯示全部", "🟢 只看買入", "🔴 只看賣出", "⚡ 剛發生交叉"], 
                index=1,
                horizontal=True
            )
            
            filtered_df = display_df.copy()
            if filter_opt == "🟢 只看買入":
                filtered_df = filtered_df[filtered_df['建議'].str.contains("買入", na=False)]
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
                    selection_mode="single-row" 
                )
                if display_event.selection.rows:
                    selected_row_idx = display_event.selection.rows[0]
                    st.session_state.selected_ticker = filtered_df.iloc[selected_row_idx]['代碼']
            
            buy_df = display_df[display_df['建議'].str.contains("買入", na=False)]
            with st.expander("📊 計算『買入』標的歷史勝率 (近一年回測)"):
                if st.button("🚀 執行歷史回測"):
                    if buy_df.empty:
                        st.warning("目前沒有處於『🟢 買入』狀態的標的，無法進行回測。")
                    else:
                        with st.spinner("正在進行歷史交易模擬回測..."):
                            backtest_results = []
                            for _, row in buy_df.iterrows():
                                res = calculate_win_rate(row['代碼'], row['名稱'], tf_interval)
                                if res: backtest_results.append(res)
                            
                            if backtest_results:
                                st.dataframe(pd.DataFrame(backtest_results), use_container_width=True)
                                st.caption("※ 回測邏輯：過去一年內，當均線與MACD雙多頭且帶量時買進；雙空頭時賣出。")
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
                fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                                    vertical_spacing=0.03, row_heights=[0.5, 0.2, 0.3])

                fig.add_trace(go.Candlestick(x=chart_df.index, open=chart_df['Open'], high=chart_df['High'],
                                             low=chart_df['Low'], close=chart_df['Close'], 
                                             name='K線', increasing_line_color='#ef5350', decreasing_line_color='#26a69a'), row=1, col=1)
                
                fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['MA5'], line=dict(color='orange', width=1.5), name=f'{ma_s_lbl} MA'), row=1, col=1)
                fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['MA10'], line=dict(color='blue', width=1.5), name=f'{ma_l_lbl} MA'), row=1, col=1)
                fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['MA20'], line=dict(color='gray', dash='dot', width=1.5), name='20MA (月線)'), row=1, col=1)

                fig.add_trace(go.Bar(x=chart_df.index, y=chart_df['Volume'], marker_color=chart_df['Vol_Color'], name='成交量'), row=2, col=1)
                fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['Vol_MA5'], line=dict(color='orange', width=1), name='5均量'), row=2, col=1)

                fig.add_trace(go.Bar(x=chart_df.index, y=chart_df['MACD_Hist'], marker_color=chart_df['MACD_Color'], name='MACD柱'), row=3, col=1)
                fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['DIF'], line=dict(color='orange', width=1.5), name='DIF'), row=3, col=1)
                fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['DEA'], line=dict(color='blue', width=1.5), name='DEA(MACD)'), row=3, col=1)

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
                    height=750, 
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
                
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            else:
                st.warning("⚠️ 無法取得該標的的 K 線圖資料，請確認代碼是否正確。")
    else:
        st.warning("⚠️ 自選股清單目前為空，請從上方的『⚙️ 自選股編輯』分頁加入股票。")

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
