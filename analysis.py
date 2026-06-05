"""
analysis.py — technical-analysis engine.
Same logic as your original ta_analysis.py, wrapped in run() so the API can call it.
Returns a list of dicts (the same schema the frontend reads).
"""
import yfinance as yf
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

STOCKS = {
    "Infosys":          "INFY.NS",
    "TCS":              "TCS.NS",
    "Persistent Sys":   "PERSISTENT.NS",
    "HCL Tech":         "HCLTECH.NS",
    "Wipro":            "WIPRO.NS",
    "Bharti Airtel":    "BHARTIARTL.NS",
    "ICICI Bank":       "ICICIBANK.NS",
    "HDFC Bank":        "HDFCBANK.NS",
    "Sun Pharma":       "SUNPHARMA.NS",
    "Bajaj Finance":    "BAJFINANCE.NS",
    "CESC":             "CESC.NS",
    "Newgen Software":  "NEWGEN.NS",
    "Acme Solar":       "ACMESOLAR.NS",
    "Birlasoft":        "BSOFT.NS",
    "Mastek":           "MASTEK.NS",
}


def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(com=period - 1, adjust=True).mean()
    loss = (-delta.clip(upper=0)).ewm(com=period - 1, adjust=True).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def compute_macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def detect_candle_patterns(df):
    patterns = []
    o, h, l, c = df['Open'], df['High'], df['Low'], df['Close']
    body = abs(c - o)
    candle_range = h - l
    avg_body = body.rolling(10).mean()
    for i in [-1, -2, -3]:
        idx = i
        try:
            b = body.iloc[idx]
            r = candle_range.iloc[idx]
            ab = avg_body.iloc[idx]
            op, cl, hi, lo = o.iloc[idx], c.iloc[idx], h.iloc[idx], l.iloc[idx]
            upper_wick = hi - max(op, cl)
            lower_wick = min(op, cl) - lo
            tag = 'today' if i == -1 else f'{abs(i)}d ago'
            if b < 0.1 * r and r > 0:
                patterns.append(f"Doji({tag})")
            elif lower_wick > 2 * b and upper_wick < b and cl > op:
                patterns.append(f"🔨Hammer({tag})")
            elif upper_wick > 2 * b and lower_wick < b and cl < op:
                patterns.append(f"⭐ShootingStar({tag})")
            elif i == -1 and cl > op and c.iloc[-2] < o.iloc[-2] and cl > o.iloc[-2] and op < c.iloc[-2]:
                patterns.append("🟢BullishEngulfing(today)")
            elif i == -1 and cl < op and c.iloc[-2] > o.iloc[-2] and cl < o.iloc[-2] and op > c.iloc[-2]:
                patterns.append("🔴BearishEngulfing(today)")
            elif b > 1.5 * ab and upper_wick < 0.05 * b and lower_wick < 0.05 * b:
                direction = "Bullish" if cl > op else "Bearish"
                patterns.append(f"{'🟢' if cl > op else '🔴'}Marubozu-{direction}({tag})")
        except Exception:
            pass
    return patterns if patterns else ["No clear pattern"]


def run():
    """Fetch + analyze all stocks. Returns list sorted by score desc."""
    results = []
    for name, ticker in STOCKS.items():
        try:
            df = yf.download(ticker, period="6mo", interval="1d",
                             progress=False, auto_adjust=True)
            if df.empty or len(df) < 30:
                continue
            df.columns = (df.columns.get_level_values(0)
                          if isinstance(df.columns, pd.MultiIndex) else df.columns)
            close, volume = df['Close'], df['Volume']

            rsi = compute_rsi(close).iloc[-1]
            macd_line, signal_line, histogram = compute_macd(close)
            macd_val, macd_sig = macd_line.iloc[-1], signal_line.iloc[-1]
            macd_hist = histogram.iloc[-1]

            ma20 = close.rolling(20).mean().iloc[-1]
            ma50 = close.rolling(50).mean().iloc[-1]
            ma200 = close.rolling(200).mean().iloc[-1]
            current = close.iloc[-1]

            vol_ratio = volume.iloc[-1] / volume.rolling(20).mean().iloc[-1]
            ret_1w = (current / close.iloc[-6] - 1) * 100
            ret_1m = (current / close.iloc[-22] - 1) * 100
            high_52w = close.rolling(252).max().iloc[-1]
            pct_from_52w_high = (current / high_52w - 1) * 100

            score, reasons = 0, []
            if current > ma20:  score += 1; reasons.append("Above MA20")
            if current > ma50:  score += 1; reasons.append("Above MA50")
            if current > ma200: score += 1; reasons.append("Above MA200")
            if ma20 > ma50:     score += 1; reasons.append("MA20>MA50")
            if macd_val > macd_sig: score += 2; reasons.append("MACD Bullish")
            if macd_hist > 0 and macd_hist > histogram.iloc[-2]:
                score += 1; reasons.append("MACD Hist Rising")
            if 40 < rsi < 70:   score += 1; reasons.append("RSI Healthy")
            elif rsi > 70:      score -= 1; reasons.append("RSI Overbought")
            elif rsi < 30:      score -= 1; reasons.append("RSI Oversold")
            if vol_ratio > 1.5: score += 1; reasons.append("Volume Spike")
            if ret_1w > 3:      score += 1; reasons.append(f"Strong 1W +{ret_1w:.1f}%")

            results.append({
                "name": name,
                "ticker": ticker.replace(".NS", ""),
                "price": round(float(current), 2),
                "rsi": round(float(rsi), 1),
                "macd_hist": round(float(macd_hist), 2),
                "ma20": round(float(ma20), 2),
                "ma50": round(float(ma50), 2),
                "ma200": round(float(ma200), 2),
                "vol_ratio": round(float(vol_ratio), 2),
                "ret_1w": round(float(ret_1w), 2),
                "ret_1m": round(float(ret_1m), 2),
                "pct_52w_high": round(float(pct_from_52w_high), 2),
                "score": score,
                "reasons": reasons,
                "patterns": detect_candle_patterns(df),
            })
        except Exception as e:
            print(f"Error {name}: {e}")

    results.sort(key=lambda x: x['score'], reverse=True)
    return results


if __name__ == "__main__":
    import json
    data = run()
    with open("ta_results.json", "w") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {len(data)} rows to ta_results.json")
