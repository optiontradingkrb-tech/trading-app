import os
import requests
import pandas as pd
from flask import Flask, jsonify

# ENV
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# TELEGRAM
def send_telegram(msg):
    if not TOKEN or not CHAT_ID:
        return
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    
    try:
        requests.post(url, data=payload)
    except:
        pass

# DATA
def get_data():
    url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI"
    data = requests.get(url).json()

    close = data['chart']['result'][0]['indicators']['quote'][0]['close']
    df = pd.DataFrame(close, columns=['Close'])
    df.dropna(inplace=True)

    return df

# STRATEGY
def strategy():
    df = get_data()
    price = df['Close'].iloc[-1]

    ma = df['Close'].rolling(10).mean().iloc[-1]

    if price > ma:
        signal = "BUY CALL"
    else:
        signal = "BUY PUT"

    return {
        "signal": signal,
        "price": round(price, 2),
        "sl": round(price - 20, 2),
        "target": round(price + 40, 2)
    }

# APP
app = Flask(__name__)

@app.route("/")
def home():
    data = strategy()

    msg = f"""
🔥 SIGNAL

{data['signal']}
Price: {data['price']}
SL: {data['sl']}
Target: {data['target']}
"""

    send_telegram(msg)

    return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
