import yfinance as yf
import pandas as pd
import requests
from sklearn.ensemble import RandomForestClassifier

# =========================
# 🔔 TELEGRAM SETTINGS
# =========================
TELEGRAM_TOKEN = "8718242394:AAEL2N5Uc02lmTNrpTsd0kwXXLNSlqej8pA"
CHAT_ID = "8353258184"

last_signal = None

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except:
        pass


def notify_signal(signal_data):
    global last_signal

    signal = signal_data['signal']

    if signal != last_signal and signal != "NO TRADE":
        message = f"""
🔥 SIGNAL ALERT

Signal: {signal_data['signal']}
Strike Price: {signal_data['strike']}

SL: {signal_data['sl']}
Target: {signal_data['target']}

Win %: {signal_data['probability']}
OI Bias: {signal_data['oi_bias']}
"""
        send_telegram(message)
        last_signal = signal


# =========================
# 📊 OPTION BIAS (SIMULATED)
# =========================
def option_chain_bias(df):
    recent = df.tail(5)

    up_volume = recent[recent['Close'] > recent['Open']]['Volume'].sum()
    down_volume = recent[recent['Close'] < recent['Open']]['Volume'].sum()

    return "BULLISH" if up_volume > down_volume else "BEARISH"


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


def ai_prediction(model, latest):
    try:
        prob = model.predict_proba([[latest['Close'], latest['Volume']]])[0][1]
        return round(prob * 100, 2)
    except:
        return 50


# =========================
# 🚀 MAIN FUNCTION
# =========================
def get_latest_signal():
    try:
        df = yf.download("^NSEI", period="1d", interval="5m")

        if df.empty:
            return {"signal": "NO DATA", "probability": 0, "price": 0, "oi_bias": "NA"}

        # Fix MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Indicator
        df['ema'] = df['Close'].ewm(span=20).mean()

        # Train AI
        model = train_ai(df)

        # Latest
        latest = df.iloc[-1]

        close_price = float(df['Close'].iloc[-1])
        ema_value = float(df['ema'].iloc[-1])

        ai_prob = ai_prediction(model, latest)
        oi_bias = option_chain_bias(df)

        # =========================
        # 🎯 SIGNAL LOGIC
        # =========================
        if close_price > ema_value and oi_bias == "BULLISH" and ai_prob > 60:
            signal = "🔥 CE BUY"
        elif close_price < ema_value and oi_bias == "BEARISH" and ai_prob > 60:
            signal = "🔥 PE BUY"
        else:
            signal = "NO TRADE"

        # =========================
        # 🎯 SL & TARGET
        # =========================
        strike_price = round(close_price / 50) * 50

        if signal == "🔥 CE BUY":
            sl = strike_price - 50
            target = strike_price + 100

        elif signal == "🔥 PE BUY":
            sl = strike_price + 50
            target = strike_price - 100

        else:
            sl = 0
            target = 0

        result = {
            "signal": signal,
            "probability": ai_prob,
            "price": close_price,
            "strike": strike_price,
            "sl": sl,
            "target": target,
            "oi_bias": oi_bias
        }

        # 🔔 Telegram Alert
        notify_signal(result)

        return result

    except Exception as e:
        return {
            "signal": "ERROR",
            "probability": 0,
            "price": 0,
            "strike": 0,
            "sl": 0,
            "target": 0,
            "oi_bias": "NA",
            "error": str(e)
        }
