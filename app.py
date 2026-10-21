import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 設定手機版網頁顯示為寬螢幕比例
st.set_page_config(page_title="雙指標波段系統", page_icon="📈", layout="wide")

# --- 側邊欄：自選股動態管理 ---
st.sidebar.header("⚙️ 自選股管理")
st.sidebar.markdown("請依照 `代碼,名稱` 的格式輸入，每行一檔標的。若要刪除，直接將該行清空即可。")

# 預設清單
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

# 讓使用者在側邊欄編輯文字框
user_input = st.sidebar.text_area("📝 編輯清單：", DEFAULT_LIST, height=400)

# 動態解析使用者輸入的清單
WATCHLIST = {}
for line in user_input.strip().split('\n'):
    if ',' in line:
        ticker, name = line.split(',', 1)
        WATCHLIST[ticker.strip()] = name.strip()

# --- 週期選擇器 ---
st.title("📈 雙指標訊號追蹤")
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

# 1. 運算所有自選股最新訊號 (加入 watchlist 作為快取參數，確保名單更新時自動重算)
@st.cache_data(ttl=3600)
def analyze_signals(interval, period, ma_s_label, ma_l_label, watchlist):
    results = []
    for ticker, name in watchlist.items():
        try:
            df = yf.download(ticker, period=period, interval=interval, progress=False)
            if df.empty or len(df) < 35: continue
            
            close = df['Close'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['Close']
            close = close.dropna()
            
            ma5, ma10 = close.rolling(5).mean(), close.rolling(10).mean()
            ema12, ema26 = close.ewm(span=12, adjust=False).mean(), close.ewm(span=26, adjust=False).mean()
            dif = ema12 - ema26
            dea = dif.ewm(span=9, adjust=False).mean()
            hist = dif - dea 
            
            curr_ma5, prev_ma5 = ma5.iloc[-1], ma5.iloc[-2]
            curr_ma10, prev_ma10 = ma10.iloc[-1], ma10.iloc[-2]
            curr_hist, prev_hist = hist.iloc[-1], hist.iloc[-2]
            
            actions = []
            if prev_hist <= 0 and curr_hist > 0: actions.append("🟢 MACD金叉")
            elif prev_hist >= 0 and curr_hist < 0: actions.append("🔴 MACD死叉")
            if prev_ma5 <= prev_ma10 and curr_ma5 > curr_ma10: actions.append("🟢 MA金叉")
            elif prev_ma5 >= prev_ma10 and curr_ma5 < curr_ma10: actions.append("🔴 MA死叉")
                
            target_position = (50 if curr_hist > 0 else 0) + (50 if curr_ma5 > curr_ma10 else 0)
            if target_position == 100:
                rec_text = "🟢 買入"
            elif target_position == 50:
                rec_text = "🟡 觀察"
            else:
                rec_text = "🔴 賣出"
            
            results.append({
                "代碼": ticker, "名稱": name, "收盤價": round(float(close.iloc[-1]), 2),
                "MACD": "多頭" if curr_hist > 0 else "空頭", 
                "MA": f"{ma_s_label}>{ma_l_label}" if curr_ma5 > curr_ma10 else f"{ma_s_label}<{ma_l_label}",
                "建議": rec_text,
                "最新動態": " / ".join(actions) if actions else "-"
            })
        except Exception: continue
    return pd.DataFrame(results)

# 2. 抓取單一股票完整數據畫圖用
@st.cache_data(ttl=3600)
def get_chart_data(ticker, interval, period):
    df = yf.download(ticker, period=period, interval=interval, progress=False)
    if df.empty: return None
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    df = df.dropna()
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['DIF'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
    df['DEA'] = df['DIF'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['DIF'] - df['DEA']
    df['Color'] = ['#ef5350' if val > 0 else '#26a69a' for val in df['MACD_Hist']]
    return df

# --- UI 介面設計 ---
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("🔄 刷新最新數據"):
        st.cache_data.clear()

with st.spinner("運算技術指標中..."):
    # 傳入動態生成的 WATCHLIST
    df_signals = analyze_signals(tf_interval, tf_period, ma_short_label, ma_long_label, WATCHLIST)
    if not df_signals.empty:
        st.subheader("📌 需調整倉位的標的")
        action_df = df_signals[df_signals['最新動態'] != "-"]
        if action_df.empty: st.info("目前無交叉訊號，維持原持股。")
        else: st.dataframe(action_df, use_container_width=True)
            
        st.subheader(f"📊 全部自選股狀態 ({timeframe_option})")
        st.dataframe(df_signals, use_container_width=True)

# --- 互動 K 線圖區塊 ---
st.divider()
st.subheader("📉 個股技術線圖分析")

# 下拉選單改為讀取動態生成的 WATCHLIST
options = [f"{k} - {v}" for k, v in WATCHLIST.items()]
if options:
    selected_option = st.selectbox("請選擇要查看的標的：", options)
    selected_ticker = selected_option.split(" - ")[0]

    with st.spinner("繪製圖表中..."):
        chart_df = get_chart_data(selected_ticker, tf_interval, tf_period)
        
        if chart_df is not None:
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.05, row_heights=[0.7, 0.3])

            fig.add_trace(go.Candlestick(x=chart_df.index, open=chart_df['Open'], high=chart_df['High'],
                                         low=chart_df['Low'], close=chart_df['Close'], 
                                         name='K線', increasing_line_color='#ef5350', decreasing_line_color='#26a69a'), 
                          row=1, col=1)
            
            fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['MA5'], line=dict(color='orange', width=1.5), name=f'{ma_short_label} MA'), row=1, col=1)
            fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['MA10'], line=dict(color='blue', width=1.5), name=f'{ma_long_label} MA'), row=1, col=1)

            fig.add_trace(go.Bar(x=chart_df.index, y=chart_df['MACD_Hist'], marker_color=chart_df['Color'], name='MACD柱'), row=2, col=1)
            fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['DIF'], line=dict(color='black', width=1), name='DIF'), row=2, col=1)
            fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['DEA'], line=dict(color='purple', width=1), name='DEA(MACD)'), row=2, col=1)

            fig.update_layout(
                height=500,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_rangeslider_visible=False,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                hovermode="x unified"
            )
            
            st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("⚠️ 自選股清單目前為空，請從左上角側邊欄加入股票。")
