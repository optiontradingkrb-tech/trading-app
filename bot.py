import yfinance as yf
import pandas as pd
import requests
import os
import numpy as np
from dotenv import load_dotenv
from sklearn.ensemble import RandomForestClassifier

# LSTM
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

last_signal = None

# =========================
# 🔔 TELEGRAM
# =========================
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except:
        pass


def notify_signal(data):
    global last_signal

    if data['signal'] != last_signal and data['signal'] != "NO TRADE":
        msg = f"""
🔥 SIGNAL ALERT

Signal: {data['signal']}
Strike: {data['strike']}

SL: {data['sl']}
Target: {data['target']}
Trailing SL: {data['trailing_sl']}

Hold: {data['hold_time']}

Win %: {data['probability']}
OI Bias: {data['oi_bias']}
SMC: {data['smc']}
Backtest: {data['backtest_acc']}%
"""
        send_telegram(msg)
        last_signal = data['signal']


# =========================
# 📊 NSE OI (ATM)
# =========================
def get_atm_oi():
    try:
        url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
        headers = {"User-Agent": "Mozilla/5.0"}

        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers)
        data = session.get(url, headers=headers).json()

        underlying = data['records']['underlyingValue']
        atm = round(underlying / 50) * 50

        for item in data['records']['data']:
            if item['strikePrice'] == atm:
                ce = item['CE']['openInterest']
                pe = item['PE']['openInterest']
                return "BULLISH" if pe > ce else "BEARISH"

        return "NEUTRAL"
    except:
        return "NEUTRAL"


# =========================
# 🧠 SMART MONEY
# =========================
def smart_money(df):
    df['high_break'] = df['High'] > df['High'].shift(1)
    df['low_break'] = df['Low'] < df['Low'].shift(1)

    last = df.iloc[-1]

    if last['high_break'] and last['Close'] < last['High']:
        return "SELL_LIQUIDITY"
    elif last['low_break'] and last['Close'] > last['Low']:
        return "BUY_LIQUIDITY"

    return "NONE"


# =========================
# 📈 PULLBACK
# =========================
def pullback(df):
    df['ema'] = df['Close'].ewm(span=20).mean()
    last = df.iloc[-1]

    if last['Close'] > last['ema']:
        return "BUY"
    elif last['Close'] < last['ema']:
        return "SELL"
    return "NONE"


# =========================
# 🤖 RANDOM AI
# =========================
def train_rf(df):
    df['target'] = (df['Close'].shift(-1) > df['Close']).astype(int)
    df = df.dropna()

    X = df[['Close', 'Volume']]
    y = df['target']

    model = RandomForestClassifier(n_estimators=50)
    model.fit(X, y)
    return model


def rf_prob(model, latest):
    try:
        p = model.predict_proba([[latest['Close'], latest['Volume']]])[0][1]
        return round(p * 100, 2)
    except:
        return 50


# =========================
# 🧠 LSTM MODEL
# =========================
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


def lstm_bias(df):
    try:
        model = train_lstm(df)
        last = df['Close'].values[-10:].reshape(1,10,1)
        pred = model.predict(last, verbose=0)[0][0]
        return "BULLISH" if pred > df['Close'].iloc[-1] else "BEARISH"
    except:
        return "NEUTRAL"


# =========================
# 📊 BACKTEST
# =========================
def backtest(df):
    wins = 0
    total = 0

    for i in range(len(df)-1):
        if df['Close'].iloc[i] < df['Close'].iloc[i+1]:
            wins += 1
        total += 1

    return round((wins/total)*100,2) if total else 0


# =========================
# 🚀 MAIN
# =========================
def get_latest_signal():
    try:
        df = yf.download("^NSEI", period="1d", interval="5m")

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        latest = df.iloc[-1]
        price = float(latest['Close'])

        oi = get_atm_oi()
        smc = smart_money(df)
        pb = pullback(df)

        rf_model = train_rf(df)
        prob = rf_prob(rf_model, latest)

        lstm = lstm_bias(df)
        acc = backtest(df)

        # =========================
        # 🎯 SIGNAL
        # =========================
        if pb == "BUY" and oi == "BULLISH" and lstm == "BULLISH" and prob > 60:
            signal = "🔥 CE BUY"
        elif pb == "SELL" and oi == "BEARISH" and lstm == "BEARISH" and prob > 60:
            signal = "🔥 PE BUY"
        else:
            signal = "NO TRADE"

        # =========================
        # 🎯 SL TARGET
        # =========================
        strike = round(price/50)*50

        if signal == "🔥 CE BUY":
            sl = strike - 50
            target = strike + 100
            trailing = strike if price > strike + 30 else sl
        elif signal == "🔥 PE BUY":
            sl = strike + 50
            target = strike - 100
            trailing = strike if price < strike - 30 else sl
        else:
            sl = target = trailing = 0

        result = {
            "signal": signal,
            "price": price,
            "strike": strike,
            "sl": sl,
            "target": target,
            "trailing_sl": trailing,
            "hold_time": "10 min",
            "probability": prob,
            "oi_bias": oi,
            "smc": smc,
            "pullback": pb,
            "lstm": lstm,
            "backtest_acc": acc
        }

        notify_signal(result)
        return result

    except Exception as e:
        return {"error": str(e)}
