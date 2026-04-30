import yfinance as yf
import pandas as pd

def get_latest_signal():
    df = yf.download("^NSEI", period="1d", interval="5m")

    # Safety
    if df.empty:
        return {
            "signal": "NO DATA",
            "probability": 0,
            "price": 0
        }

    # Flatten columns (VERY IMPORTANT FIX)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # EMA
    df['ema'] = df['Close'].ewm(span=20).mean()

    # Extract latest safely
    latest_close = df['Close'].iloc[-1]
    latest_ema = df['ema'].iloc[-1]

    # Convert safely
    close_price = float(latest_close)
    ema_value = float(latest_ema)

    # Signal
    if close_price > ema_value:
        signal = "CE BUY"
    else:
        signal = "PE BUY"

    return {
        "signal": signal,
        "probability": 65,
        "price": close_price
    }
