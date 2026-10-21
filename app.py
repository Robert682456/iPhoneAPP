import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="雙指標波段系統", page_icon="📈", layout="wide")

# --- 側邊欄：自選股動態管理 ---
st.sidebar.header("⚙️ 自選股管理")
st.sidebar.markdown("請依照 `代碼,名稱` 的格式輸入，每行一檔標的。若要刪除，直接將該行清空即可。")

DEFAULT_LIST = """0050.TW,元大台灣50
00752.TW,中信中國50
00880B.TW,野村澳州公債
00725B.TW,國泰投資級公司債
2812.TW,台中銀
5386.TW,青雲
1101.TW,台泥
2330.TW,台積電
3008.TW,大立光
3362.TW,先進光
1415.HK,高偉電子
02342.HK,京信通信
VOO,VOO標普500
QQQM,QQQM納指100
SGOV,SGOV美債"""

user_input = st.sidebar.text_area("📝 編輯清單：", DEFAULT_LIST, height=400)
WATCHLIST = {}
for line in user_input.strip().split('\n'):
    if ',' in line:
        ticker, name = line.split(',', 1)
        WATCHLIST[ticker.strip()] = name.strip()

# --- 週期選擇器 ---
st.title("📈 高階波段訊號追蹤 (含價量濾網)")
timeframe_option = st.radio(
    "請選擇分析週期：", 
    ["週線 (Weekly)", "日線 (Daily)"], 
    horizontal=True
)

if timeframe_option == "週線 (Weekly)":
    tf_interval = "1wk"
    tf_period = "2y"
    ma_short_label = "5W"
    ma_long_label = "10W"
else:
    tf_interval = "1d"
    tf_period = "1y"
    ma_short_label = "5D"
    ma_long_label = "10D"

# --- ⭐️ 新增：大盤(0050) 多空環境燈號分析 ---
@st.cache_data(ttl=3600)
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
        curr_dif = dif.iloc[-1]
        
        # 判定大盤燈號邏輯
        if curr_hist > 0 and curr_hist > prev_hist:
            status = "🟢 多頭擴張"
            advice = "大盤趨勢向上，操作部位可適度放大至 80%~100%。"
            color = "#e8f5e9" # 淺綠底
        elif curr_hist > 0 and curr_hist <= prev_hist:
            status = "🟡 高檔震盪 (柱狀收斂)"
            advice = "大盤動能減弱，維持現有持股，新部位需嚴格挑選帶量突破標的。"
            color = "#fff8e1" # 淺黃底
        elif curr_hist < 0 and curr_hist > prev_hist:
            status = "🟡 跌深反彈 (水下金叉)"
            advice = "大盤有落底跡象，可以 30%~50% 資金小量試單，嚴設前低停損。"
            color = "#fff8e1" # 淺黃底
        else:
            status = "🔴 空頭發散"
            advice = "大盤趨勢向下，建議縮小操作部位至 30% 以下，多看少做保本為主。"
            color = "#ffebee" # 淺紅底
            
        return {"status": status, "advice": advice, "color": color, "price": close.iloc[-1]}
    except Exception:
        return None

# 1. 運算所有自選股最新訊號
@st.cache_data(ttl=3600)
def analyze_signals(interval, period, ma_s_label, ma_l_label, watchlist):
    results = []
    for ticker, name in watchlist.items():
        try:
            df = yf.download(ticker, period=period, interval=interval, progress=False)
            if df.empty or len(df) < 35: continue
            
            close = df['Close'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['Close']
            volume = df['Volume'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['Volume']
            close = close.dropna()
            volume = volume.dropna()
            
            ma5, ma10 = close.rolling(5).mean(), close.rolling(10).mean()
            ma20 = close.rolling(20).mean()
            vol_ma5 = volume.rolling(5).mean()
            
            ema12, ema26 = close.ewm(span=12, adjust=False).mean(), close.ewm(span=26, adjust=False).mean()
            dif = ema12 - ema26
            dea = dif.ewm(span=9, adjust=False).mean()
            hist = dif - dea 
            
            curr_close, prev_close = close.iloc[-1], close.iloc[-2]
            curr_ma5, prev_ma5 = ma5.iloc[-1], ma5.iloc[-2]
            curr_ma10, prev_ma10 = ma10.iloc[-1], ma10.iloc[-2]
            curr_ma20, prev_ma20 = ma20.iloc[-1], ma20.iloc[-2]
            
            curr_hist, prev_hist = hist.iloc[-1], hist.iloc[-2]
            curr_dif = dif.iloc[-1]
            
            curr_vol = volume.iloc[-1]
            curr_vol_ma5 = vol_ma5.iloc[-1]
            vol_condition = curr_vol > curr_vol_ma5  
            
            change_pct = ((curr_close - prev_close) / prev_close) * 100
            if change_pct > 0: price_display = f"🔺 {curr_close:.2f} (+{change_pct:.2f}%)"
            elif change_pct < 0: price_display = f"🔻 {curr_close:.2f} ({change_pct:.2f}%)"
            else: price_display = f"➖ {curr_close:.2f} (0.00%)"
            
            actions = []
            
            if interval == "1d":
                if prev_close <= prev_ma20 and curr_close > curr_ma20:
                    if vol_condition: actions.append("🟢 日線帶量突破(提前佈局)")
                    else: actions.append("⚠️ 日線無量突破(提防假突破)")

            if prev_hist <= 0 and curr_hist > 0:
                if vol_condition:
                    if curr_dif > 0: actions.append("🟢 零上帶量金叉(強勢主升)")
                    else: actions.append("🟢 水下帶量金叉(嚴設停損)")
                else: actions.append("⚠️ 無量金叉(觀望)")
            elif prev_hist >= 0 and curr_hist < 0:
                actions.append("🔴 MACD死叉(賣出)")
            elif interval == "1wk" and prev_hist < 0 and curr_hist < 0 and curr_hist > prev_hist:
                actions.append("💡 柱狀收斂(切日線看20MA)")

            if prev_ma5 <= prev_ma10 and curr_ma5 > curr_ma10:
                if vol_condition: actions.append("🟢 MA帶量金叉")
                else: actions.append("⚠️ MA無量金叉")
            elif prev_ma5 >= prev_ma10 and curr_ma5 < curr_ma10:
                actions.append("🔴 MA死叉(賣出)")
                
            target_position = (50 if curr_hist > 0 else 0) + (50 if curr_ma5 > curr_ma10 else 0)
            if target_position == 100: rec_text = "🟢 買入" if vol_condition else "🟡 觀察(無量)"
            elif target_position == 50: rec_text = "🟡 觀察"
            else: rec_text = "🔴 賣出"
            
            results.append({
                "代碼": ticker, "名稱": name, "收盤價(漲跌)": price_display,
                "MACD": "多頭" if curr_hist > 0 else "空頭", 
                "MA": f"{ma_s_label}>{ma_l_label}" if curr_ma5 > curr_ma10 else f"{ma_s_label}<{ma_l_label}",
                "建議": rec_text,
                "最新動態": " / ".join(actions) if actions else "-"
            })
        except Exception: continue
        
    df_results = pd.DataFrame(results)
    if not df_results.empty:
        def get_sort_rank(row):
            if "🟢 買入" in row['建議'] or "提前佈局" in row['最新動態']: return 1
            elif "🟡 觀察" in row['建議']: return 2
            else: return 3
                
        df_results['SortRank'] = df_results.apply(get_sort_rank, axis=1)
        df_results = df_results.sort_values(by='SortRank').drop(columns=['SortRank']).reset_index(drop=True)
        
    return df_results

def style_dataframe(df):
    def color_trend(val):
        if isinstance(val, str):
            if '🔺' in val: return 'color: #ff4b4b; font-weight: bold;'
            elif '🔻' in val: return 'color: #00c853; font-weight: bold;'
        return ''
    if hasattr(df.style, "map"): return df.style.map(color_trend, subset=['收盤價(漲跌)'])
    else: return df.style.applymap(color_trend, subset=['收盤價(漲跌)'])

# 2. 抓取單一股票完整數據畫圖用
@st.cache_data(ttl=3600)
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

# --- UI 介面設計 ---
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("🔄 刷新最新數據"):
        st.cache_data.clear()

with st.spinner("運算技術指標與量能中..."):
    # ⭐️ 渲染大盤燈號儀表板
    market_trend = get_market_trend(tf_interval, tf_period)
    if market_trend:
        st.markdown(
            f"""
            <div style="background-color: {market_trend['color']}; padding: 15px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #ccc;">
                <h4 style="margin: 0; color: #333;">🧭 總體資金水位儀表板 (0050 {timeframe_option})</h4>
                <p style="margin: 5px 0 0 0; font-size: 18px; font-weight: bold; color: #333;">
                    狀態：{market_trend['status']}
                </p>
                <p style="margin: 5px 0 0 0; color: #555;">
                    💡 建議：{market_trend['advice']}
                </p>
            </div>
            """, 
            unsafe_allow_html=True
        )

    # 渲染個股表格
    df_signals = analyze_signals(tf_interval, tf_period, ma_short_label, ma_long_label, WATCHLIST)
    if not df_signals.empty:
        st.subheader("📌 重點動態追蹤 (量能與位階濾網)")
        action_df = df_signals[df_signals['最新動態'] != "-"]
        
        if action_df.empty: st.info("目前無交叉訊號，維持原持股。")
        else: st.dataframe(style_dataframe(action_df), use_container_width=True)
            
        st.subheader(f"📊 全部自選股狀態 ({timeframe_option})")
        st.dataframe(style_dataframe(df_signals), use_container_width=True)

# --- 互動 K 線圖區塊 ---
st.divider()
st.subheader("📉 價量與指標複合分析圖")

options = [f"{k} - {v}" for k, v in WATCHLIST.items()]
if options:
    selected_option = st.selectbox("請選擇要查看的標的：", options)
    selected_ticker = selected_option.split(" - ")[0]

    with st.spinner("繪製圖表中..."):
        chart_df = get_chart_data(selected_ticker, tf_interval, tf_period)
        if chart_df is not None:
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.03, row_heights=[0.5, 0.2, 0.3])

            fig.add_trace(go.Candlestick(x=chart_df.index, open=chart_df['Open'], high=chart_df['High'],
                                         low=chart_df['Low'], close=chart_df['Close'], 
                                         name='K線', increasing_line_color='#ef5350', decreasing_line_color='#26a69a'), row=1, col=1)
            fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['MA5'], line=dict(color='orange', width=1.5), name=f'{ma_short_label} MA'), row=1, col=1)
            fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['MA10'], line=dict(color='blue', width=1.5), name=f'{ma_long_label} MA'), row=1, col=1)
            fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['MA20'], line=dict(color='gray', dash='dot', width=1.5), name='20MA (月線)'), row=1, col=1)

            fig.add_trace(go.Bar(x=chart_df.index, y=chart_df['Volume'], marker_color=chart_df['Vol_Color'], name='成交量'), row=2, col=1)
            fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['Vol_MA5'], line=dict(color='orange', width=1), name='5均量'), row=2, col=1)

            fig.add_trace(go.Bar(x=chart_df.index, y=chart_df['MACD_Hist'], marker_color=chart_df['MACD_Color'], name='MACD柱'), row=3, col=1)
            fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['DIF'], line=dict(color='black', width=1), name='DIF'), row=3, col=1)
            fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['DEA'], line=dict(color='purple', width=1), name='DEA(MACD)'), row=3, col=1)

            fig.update_layout(height=650, margin=dict(l=10, r=10, t=10, b=10), xaxis_rangeslider_visible=False,
                              legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("⚠️ 自選股清單目前為空，請從左上角側邊欄加入股票。")
