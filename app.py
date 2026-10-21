# 1. 運算所有自選股最新訊號
@st.cache_data(ttl=3600)
def analyze_signals(interval, period, ma_s_label, ma_l_label):
    results = []
    for ticker, name in WATCHLIST.items():
        try:
            df = yf.download(ticker, period=period, interval=interval, progress=False)
            if df.empty or len(df) < 35: continue
            
            close = df['Close'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['Close']
            close = close.dropna()
            
            # 計算均線與 MACD
            ma5, ma10 = close.rolling(5).mean(), close.rolling(10).mean()
            ema12, ema26 = close.ewm(span=12, adjust=False).mean(), close.ewm(span=26, adjust=False).mean()
            dif = ema12 - ema26
            dea = dif.ewm(span=9, adjust=False).mean()
            hist = dif - dea 
            
            curr_ma5, prev_ma5 = ma5.iloc[-1], ma5.iloc[-2]
            curr_ma10, prev_ma10 = ma10.iloc[-1], ma10.iloc[-2]
            curr_hist, prev_hist = hist.iloc[-1], hist.iloc[-2]
            
            # 判斷訊號
            actions = []
            if prev_hist <= 0 and curr_hist > 0: actions.append("🟢 MACD金叉(+50%)")
            elif prev_hist >= 0 and curr_hist < 0: actions.append("🔴 MACD死叉(-50%)")
            if prev_ma5 <= prev_ma10 and curr_ma5 > curr_ma10: actions.append(f"🟢 MA金叉(+50%)")
            elif prev_ma5 >= prev_ma10 and curr_ma5 < curr_ma10: actions.append(f"🔴 MA死叉(-50%)")
                
            # 計算基礎水位積分 (0, 50, 100)
            target_position = (50 if curr_hist > 0 else 0) + (50 if curr_ma5 > curr_ma10 else 0)
            
            # 將數值轉換為「建議」文字
            if target_position == 100:
                rec_text = "買入"
            elif target_position == 50:
                rec_text = "觀察"
            else:
                rec_text = "賣出"
            
            results.append({
                "代碼": ticker, "名稱": name, "收盤價": round(float(close.iloc[-1]), 2),
                "MACD": "多頭" if curr_hist > 0 else "空頭", 
                "MA": f"{ma_s_label}>{ma_l_label}" if curr_ma5 > curr_ma10 else f"{ma_s_label}<{ma_l_label}",
                "建議": rec_text,  # 這裡已將欄位名稱改為「建議」並帶入文字
                "最新動態": " / ".join(actions) if actions else "-"
            })
        except Exception: continue
    return pd.DataFrame(results)
