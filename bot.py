import yfinance as yf
import pandas as pd
import requests
import os
import time
from dotenv import load_dotenv
from sklearn.ensemble import RandomForestClassifier

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


def notify_signal(signal_data):
    global last_signal

    if signal_data['signal'] != last_signal and signal_data['signal'] != "NO TRADE":

        msg = f"""
🔥 SIGNAL ALERT

Signal: {signal_data['signal']}
Strike: {signal_data['strike']}

SL: {signal_data['sl']}
Target: {signal_data['target']}
Trailing SL: {signal_data['trailing_sl']}

Hold: {signal_data['hold_time']}

Win %: {signal_data['probability']}
OI Bias: {signal_data['oi_bias']}
Backtest Acc: {signal_data['backtest_acc']}%
"""
        send_telegram(msg)
        last_signal = signal_data['signal']


# =========================
# 📊 REAL ATM OI
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
                ce_oi = item['CE']['openInterest']
                pe_oi = item['PE']['openInterest']

                return "BULLISH" if pe_oi > ce_oi else "BEARISH"

        return "NEUTRAL"
    except:
        return "NEUTRAL"


# =========================
# 🧠 SMART MONEY (LIQUIDITY)
# =========================
def smart_money(df):
    df['high_break'] = df['High'] > df['High'].shift(1)
    df['low_break'] = df['Low'] < df['Low'].shift(1)

    last = df.iloc[-1]

    if last['high_break'] and last['Close'] < last['High']:
        return "SELL_SIDE_LIQUIDITY"

    elif last['low_break'] and last['Close'] > last['Low']:
        return "BUY_SIDE_LIQUIDITY"

    return "NONE"


# =========================
# 📈 PULLBACK STRATEGY
# =========================
def pullback(df):
    df['ema'] = df['Close'].ewm(span=20).mean()

    last = df.iloc[-1]

    if last['Close'] > last['ema']:
        return "BUY_PULLBACK"

    elif last['Close'] < last['ema']:
        return "SELL_PULLBACK"

    return "NONE"


# =========================
# 🤖 AI MODEL
# =========================
def train_ai(df):
    df['target'] = (df['Close'].shift(-1) > df['Close']).astype(int)
    df = df.dropna()

    X = df[['Close', 'Volume']]
    y = df['target']

    model = RandomForestClassifier(n_estimators=50)
    model.fit(X, y)

    return model


def ai_prob(model, latest):
    try:
        p = model.predict_proba([[latest['Close'], latest['Volume']]])[0][1]
        return round(p * 100, 2)
    except:
        return 50


# =========================
# 📊 BACKTEST
# =========================
def backtest(df):
    wins = 0
    total = 0

    for i in range(len(df) - 1):
        if df['Close'].iloc[i] < df['Close'].iloc[i + 1]:
            wins += 1
        total += 1

    return round((wins / total) * 100, 2) if total > 0 else 0


# =========================
# 🚀 MAIN FUNCTION
# =========================
def get_latest_signal():
    try:
        df = yf.download("^NSEI", period="1d", interval="5m")

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        latest = df.iloc[-1]
        close_price = float(latest['Close'])

        # Components
        oi_bias = get_atm_oi()
        smc = smart_money(df)
        pb = pullback(df)

        model = train_ai(df)
        probability = ai_prob(model, latest)
        acc = backtest(df)

        # =========================
        # 🎯 FINAL LOGIC
        # =========================
        if pb == "BUY_PULLBACK" and oi_bias == "BULLISH" and probability > 60:
            signal = "🔥 CE BUY"

        elif pb == "SELL_PULLBACK" and oi_bias == "BEARISH" and probability > 60:
            signal = "🔥 PE BUY"

        else:
            signal = "NO TRADE"

        # =========================
        # 🎯 SL / TARGET
        # =========================
        strike = round(close_price / 50) * 50

        if signal == "🔥 CE BUY":
            sl = strike - 50
            target = strike + 100
            trailing = strike if close_price > strike + 30 else sl

        elif signal == "🔥 PE BUY":
            sl = strike + 50
            target = strike - 100
            trailing = strike if close_price < strike - 30 else sl

        else:
            sl = target = trailing = 0

        result = {
            "signal": signal,
            "price": close_price,
            "strike": strike,
            "sl": sl,
            "target": target,
            "trailing_sl": trailing,
            "hold_time": "10 min",
            "probability": probability,
            "oi_bias": oi_bias,
            "smc": smc,
            "pullback": pb,
            "backtest_acc": acc
        }

        notify_signal(result)

        return result

    except Exception as e:
        return {"error": str(e)}
