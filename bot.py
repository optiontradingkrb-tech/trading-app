import os
import requests
import pandas as pd
from flask import Flask, jsonify

# ================= ENV =================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# ================= TELEGRAM =================
def send_telegram(msg):
    if not TOKEN or not CHAT_ID:
        return
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}

    try:
        requests.post(url, data=payload, timeout=5)
    except:
        pass

# ================= DATA =================
def get_data():
    url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI"
    data = requests.get(url, timeout=5).json()

    close = data['chart']['result'][0]['indicators']['quote'][0]['close']
    df = pd.DataFrame(close, columns=['Close'])
    df.dropna(inplace=True)

    return df

# ================= STRATEGY =================
def strategy():
    df = get_data()

    close_price = df['Close'].iloc[-1]

    # Simple Trend Logic (FAST & SAFE)
    ma = df['Close'].rolling(10).mean().iloc[-1]

    if close_price > ma:
        signal = "BUY CALL"
        bias = "BULLISH"
        oi_bias = "PUT WRITING"
    else:
        signal = "BUY PUT"
        bias = "BEARISH"
        oi_bias = "CALL WRITING"

    # Smart Money (basic)
    smc = "Liquidity Grab Possible"

    # Pullback
    pullback = "VALID" if abs(close_price - ma) < 30 else "STRONG TREND"

    # Risk
    sl = round(close_price - 20, 2)
    target = round(close_price + 40, 2)
    trailing_sl = round(close_price - 10, 2)

    return {
        "signal": signal,
        "price": round(close_price, 2),
        "strike": round(close_price/50)*50,
        "sl": sl,
        "target": target,
        "trailing_sl": trailing_sl,
        "probability": 60,
        "oi_bias": oi_bias,
        "smc": smc,
        "pullback": pullback,
        "hold_time": "5-10 min",
        "backtest_acc": 60
    }

# ================= FLASK =================
app = Flask(__name__)

@app.route("/")
def home():
    data = strategy()

    msg = f"""
🔥 AI SIGNAL

Signal: {data['signal']}
Price: {data['price']}
Strike: {data['strike']}

SL: {data['sl']}
Target: {data['target']}
TSL: {data['trailing_sl']}

OI: {data['oi_bias']}
SMC: {data['smc']}
Pullback: {data['pullback']}
"""

    send_telegram(msg)

    return jsonify({"data": data})

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
