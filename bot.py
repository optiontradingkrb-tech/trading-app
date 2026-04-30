import yfinance as yf
import pandas as pd

def get_latest_signal():
    df = yf.download("^NSEI", period="1d", interval="5m")

    # Safety check
    if df.empty:
        return {
            "signal": "NO DATA",
            "probability": 0,
            "price": 0
        }

    # EMA
    df['ema'] = df['Close'].ewm(span=20).mean()

    # Latest row properly extract
    latest = df.iloc[-1]

    close_price = float(latest['Close'])
    ema_value = float(latest['ema'])

    # Safe comparison
    if close_price > ema_value:
        signal = "CE BUY"
    else:
        signal = "PE BUY"

    return {
        "signal": signal,
        "probability": 65,
        "price": close_price
    }
