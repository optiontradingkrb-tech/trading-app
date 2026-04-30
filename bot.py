import yfinance as yf
import pandas as pd
import requests
from sklearn.ensemble import RandomForestClassifier

# =========================
# 🔔 TELEGRAM SETTINGS
# =========================
TELEGRAM_TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

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

    # Only send new signal (avoid spam)
    if signal != last_signal and signal != "NO TRADE":
        message = f"""
🔥 SIGNAL ALERT

Signal: {signal}
Price: {signal_data['price']}
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

        # Safety check
        if df.empty:
            return {"signal": "NO DATA", "probability": 0, "price": 0, "oi_bias": "NA"}

        # Fix multi-index issue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Indicator
        df['ema'] = df['Close'].ewm(span=20).mean()

        # Train AI
        model = train_ai(df)

        # Latest data
        latest = df.iloc[-1]

        close_price = float(df['Close'].iloc[-1])
        ema_value = float(df['ema'].iloc[-1])

        ai_prob = ai_prediction(model, latest)
        oi_bias = option_chain_bias(df)

        # =========================
        # 🎯 FINAL SIGNAL LOGIC
        # =========================
        if close_price > ema_value and oi_bias == "BULLISH" and ai_prob > 60:
            signal = "🔥 CE BUY"
        elif close_price < ema_value and oi_bias == "BEARISH" and ai_prob > 60:
            signal = "🔥 PE BUY"
        else:
            signal = "NO TRADE"

        result = {
            "signal": signal,
            "probability": ai_prob,
            "price": close_price,
            "oi_bias": oi_bias
        }

        # 🔔 Send Telegram Alert
        notify_signal(result)

        return result

    except Exception as e:
        return {
            "signal": "ERROR",
            "probability": 0,
            "price": 0,
            "oi_bias": "NA",
            "error": str(e)
        }
