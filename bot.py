import yfinance as yf
import pandas as pd

def get_latest_signal():
    df = yf.download("^NSEI", period="1d", interval="5m")

    df['ema'] = df['Close'].ewm(span=20).mean()

    latest = df.iloc[-1]

    if latest['Close'] > latest['ema']:
        signal = "CE BUY"
    else:
        signal = "PE BUY"

    return {
        "signal": signal,
        "probability": 65,
        "price": float(latest['Close'])
    }
