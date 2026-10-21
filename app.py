import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 設定手機版網頁顯示為寬螢幕比例
st.set_page_config(page_title="週線雙指標波段系統", page_icon="📈", layout="wide")

# 自選股清單
WATCHLIST = {
    "0050.TW": "元大台灣50",
    "2330.TW": "台積電",
    "2308.TW": "台達電",
    "1504.TW": "東元",
    "3008.TW": "大立光",
    "3362.TW": "先進光",
    "3622.TW": "淳安電子",
    "1101.TW": "台泥",
    "1415.HK": "高偉電子",
    "2342.HK": "京信通信",
    "1729.HK": "匯聚科技",
    "2304.HK": "京西國際",
    "VOO": "VOO標普500",
    "QQQM": "QQQM納指100",
    "SGOV": "SGOV美債",
    "GLDM": "GLDM黃金"
}

# 1. 運算所有自選股最新訊號 (快取機制)
@st.cache_data(ttl=3600)
def analyze_weekly_signals():
    results = []
    for ticker, name in WATCHLIST.items():
        try:
            df = yf.download(ticker, period="2y", interval="1wk", progress=False)
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
            if prev_hist <= 0 and curr_hist > 0: actions.append("🟢 MACD金叉(+50%)")
            elif prev_hist >= 0 and curr_hist < 0: actions.append("🔴 MACD死叉(-50%)")
            if prev_ma5 <= prev_ma10 and curr_ma5 > curr_ma10: actions.append("🟢 MA金叉(+50%)")
            elif prev_ma5 >= prev_ma10 and curr_ma5 < curr_ma10: actions.append("🔴 MA死叉(-50%)")
                
            target_position = (50 if curr_hist > 0 else 0) + (50 if curr_ma5 > curr_ma10 else 0)
            
            results.append({
                "代碼": ticker, "名稱": name, "收盤價": round(float(close.iloc[-1]), 2),
                "MACD": "多頭" if curr_hist > 0 else "空頭", "MA": "5W>10W" if curr_ma5 > curr_ma10 else "5W<10W",
                "持股水位": f"{target_position}%", "本週動態": " / ".join(actions) if actions else "-"
            })
        except Exception: continue
    return pd.DataFrame(results)

# 2. 抓取單一股票完整數據畫圖用
@st.cache_data(ttl=3600)
def get_chart_data(ticker):
    df = yf.download(ticker, period="2y", interval="1wk", progress=False)
    if df.empty: return None
    
    # 處理 yfinance 格式
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    df = df.dropna()
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['DIF'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
    df['DEA'] = df['DIF'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['DIF'] - df['DEA']
    
    # 定義 MACD 柱狀體顏色 (紅漲綠跌)
    df['Color'] = ['#ef5350' if val > 0 else '#26a69a' for val in df['MACD_Hist']]
    return df

# --- UI 介面設計 ---
st.title("📈 週線波段系統")

if st.button("🔄 刷新最新數據"):
    st.cache_data.clear()

with st.spinner("運算技術指標中..."):
    df_signals = analyze_weekly_signals()
    if not df_signals.empty:
        st.subheader("📌 本週需調整倉位的標的")
        action_df = df_signals[df_signals['本週動態'] != "-"]
        if action_df.empty: st.info("本週無交叉訊號，維持原持股。")
        else: st.dataframe(action_df, use_container_width=True)
            
        st.subheader("📊 全部自選股狀態")
        st.dataframe(df_signals, use_container_width=True)

# --- 互動 K 線圖區塊 ---
st.divider()
st.subheader("📉 個股技術線圖分析 (週線)")

# 建立選單 (格式：0050.TW - 元大台灣50)
options = [f"{k} - {v}" for k, v in WATCHLIST.items()]
selected_option = st.selectbox("請選擇要查看的標的：", options)
selected_ticker = selected_option.split(" - ")[0]

with st.spinner("繪製圖表中..."):
    chart_df = get_chart_data(selected_ticker)
    
    if chart_df is not None:
        # 使用 Plotly 建立子圖 (上面 K線+均線，下面 MACD)
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                            vertical_spacing=0.05, row_heights=[0.7, 0.3])

        # 1. K 線圖
        fig.add_trace(go.Candlestick(x=chart_df.index, open=chart_df['Open'], high=chart_df['High'],
                                     low=chart_df['Low'], close=chart_df['Close'], 
                                     name='K線', increasing_line_color='#ef5350', decreasing_line_color='#26a69a'), 
                      row=1, col=1)
        
        # 2. 5W & 10W 均線
        fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['MA5'], line=dict(color='orange', width=1.5), name='5W MA'), row=1, col=1)
        fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['MA10'], line=dict(color='blue', width=1.5), name='10W MA'), row=1, col=1)

        # 3. MACD 柱狀體與快慢線
        fig.add_trace(go.Bar(x=chart_df.index, y=chart_df['MACD_Hist'], marker_color=chart_df['Color'], name='MACD柱'), row=2, col=1)
        fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['DIF'], line=dict(color='black', width=1), name='DIF'), row=2, col=1)
        fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['DEA'], line=dict(color='purple', width=1), name='DEA(MACD)'), row=2, col=1)

        # 優化手機版顯示 Layout
        fig.update_layout(
            height=500,
            margin=dict(l=10, r=10, t=10, b=10), # 縮小邊界適合手機
            xaxis_rangeslider_visible=False,     # 隱藏下方拖拉桿節省空間
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), # 圖例放上方水平排列
            hovermode="x unified"
        )
        
        st.plotly_chart(fig, use_container_width=True)