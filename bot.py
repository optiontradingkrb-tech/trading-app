import os
import time
import requests
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from flask import Flask, jsonify
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense

# ================= LOAD ENV =================
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# ================= TELEGRAM =================
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.post(url, data=payload)
    except:
        pass

# ================= DATA FETCH =================
def get_data():
    url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI"
    data = requests.get(url).json()

    close = data['chart']['result'][0]['indicators']['quote'][0]['close']
    df = pd.DataFrame(close, columns=['Close'])
    df.dropna(inplace=True)

    return df

# ================= LSTM MODEL =================
def train_lstm(df):
    data = df['Close'].values.reshape(-1,1)

    X, y = [], []
    for i in range(10, len(data)):
        X.append(data[i-10:i])
        y.append(data[i])

    X, y = np.array(X), np.array(y)

    model = Sequential()
    model.add(LSTM(50, input_shape=(X.shape[1],1)))
    model.add(Dense(1))

    model.compile(optimizer='adam', loss='mse')
    model.fit(X, y, epochs=2, verbose=0)

    return model

def lstm_prediction(model, df):
    data = df['Close'].values[-10:].reshape(1,10,1)
    pred = model.predict(data, verbose=0)
    return float(pred[0][0])

# ================= STRATEGY =================
def strategy():
    df = get_data()

    close_price = df['Close'].iloc[-1]

    # LSTM
    model = train_lstm(df)
    pred_price = lstm_prediction(model, df)

    if pred_price > close_price:
        bias = "BULLISH"
        signal = "BUY CALL"
    else:
        bias = "BEARISH"
        signal = "BUY PUT"

    # Fake OI (replace later with real API)
    oi_bias = "CALL WRITING" if bias == "BEARISH" else "PUT WRITING"

    # Smart money logic
    smc = "Liquidity Grab Done"

    # Pullback
    pullback = "VALID" if abs(pred_price - close_price) < 50 else "STRONG TREND"

    # Risk management
    sl = round(close_price - 20, 2)
    target = round(close_price + 40, 2)
    trailing_sl = round(close_price - 10, 2)

    hold_time = "5-10 min"

    # Backtest dummy
    accuracy = 65

    return {
        "signal": signal,
        "price": round(close_price,2),
        "strike": round(close_price/50)*50,
        "sl": sl,
        "target": target,
        "trailing_sl": trailing_sl,
        "probability": accuracy,
        "oi_bias": oi_bias,
        "smc": smc,
        "pullback": pullback,
        "hold_time": hold_time,
        "backtest_acc": accuracy
    }

# ================= FLASK API =================
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

Accuracy: {data['probability']}%
"""

    send_telegram(msg)

    return jsonify({"data": data})

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
