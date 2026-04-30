import yfinance as yf
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

# OPTION CHAIN (SIMULATED USING VOLUME)
def option_chain_bias(df):
    recent = df.tail(5)

    up_volume = recent[recent['Close'] > recent['Open']]['Volume'].sum()
    down_volume = recent[recent['Close'] < recent['Open']]['Volume'].sum()

    return "BULLISH" if up_volume > down_volume else "BEARISH"


# AI MODEL
def train_ai(df):
    df['target'] = (df['Close'].shift(-1) > df['Close']).astype(int)
    df = df.dropna()

    X = df[['Close', 'Volume']]
    y = df['target']

    model = RandomForestClassifier(n_estimators=50)
    model.fit(X, y)

    return model


def ai_prediction(model, latest):
    prob = model.predict_proba([[latest['Close'], latest['Volume']]])[0][1]
    return round(prob * 100, 2)


# MAIN FUNCTION
def get_latest_signal():
    df = yf.download("^NSEI", period="1d", interval="5m")

    if df.empty:
        return {"signal": "NO DATA", "probability": 0, "price": 0}

    # Fix MultiIndex
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Indicators
    df['ema'] = df['Close'].ewm(span=20).mean()

    # AI Model
    model = train_ai(df)

    latest = df.iloc[-1]

    close_price = float(df['Close'].iloc[-1])
    ema = float(df['ema'].iloc[-1])

    ai_prob = ai_prediction(model, latest)
    oi_bias = option_chain_bias(df)

    # FINAL LOGIC
    if close_price > ema and oi_bias == "BULLISH" and ai_prob > 60:
        signal = "🔥 CE BUY"
    elif close_price < ema and oi_bias == "BEARISH" and ai_prob > 60:
        signal = "🔥 PE BUY"
    else:
        signal = "NO TRADE"

    return {
        "signal": signal,
        "probability": ai_prob,
        "price": close_price,
        "oi_bias": oi_bias
    }
