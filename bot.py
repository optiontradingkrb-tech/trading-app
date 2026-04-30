import requests
import pandas as pd
import ta
import time

# ================= CONFIG =================
INDEX_API = "https://nse-api-ruby.vercel.app/index?symbol=NIFTY%2050"
OPTION_API = "https://nse-api-ruby.vercel.app/option-chain?symbol=NIFTY"

TELEGRAM_TOKEN = "YOUR_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

# ================= TELEGRAM =================
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except:
        pass

# ================= DATA =================
def fetch_data():
    data = requests.get(INDEX_API).json()
    df = pd.DataFrame(data['data'])
    return df

def fetch_option_chain():
    return requests.get(OPTION_API).json()

# ================= INDICATORS =================
def apply_indicators(df):
    df['EMA9'] = ta.trend.ema_indicator(df['close'], 9)
    df['EMA21'] = ta.trend.ema_indicator(df['close'], 21)
    df['RSI'] = ta.momentum.rsi(df['close'], 14)
    df['ATR'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], 14)
    return df

# ================= SMART MONEY =================
def smart_money(df):
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    if latest['low'] < prev['low'] and latest['close'] > prev['low']:
        return "BUY"

    if latest['high'] > prev['high'] and latest['close'] < prev['high']:
        return "SELL"

    return None

# ================= OPTION CHAIN =================
def option_bias():
    data = fetch_option_chain()
    records = data['records']['data']

    call_oi = 0
    put_oi = 0

    for r in records:
        if 'CE' in r and 'PE' in r:
            call_oi += r['CE']['openInterest']
            put_oi += r['PE']['openInterest']

    if put_oi > call_oi:
        return "BULLISH", put_oi, call_oi
    elif call_oi > put_oi:
        return "BEARISH", put_oi, call_oi
    return "NEUTRAL", put_oi, call_oi

# ================= HOLD TIME =================
def hold_time(atr):
    if atr > 25:
        return "5 min"
    elif atr > 15:
        return "10 min"
    return "Avoid"

# ================= STRATEGY =================
def strategy(df):
    latest = df.iloc[-1]

    trend_bull = latest['close'] > latest['EMA9'] > latest['EMA21']
    trend_bear = latest['close'] < latest['EMA9'] < latest['EMA21']

    avg_vol = df['volume'].rolling(10).mean().iloc[-1]
    vol_spike = latest['volume'] > avg_vol * 1.5

    momentum_bull = latest['RSI'] > 55 and vol_spike
    momentum_bear = latest['RSI'] < 45 and vol_spike

    smart = smart_money(df)
    bias, put_oi, call_oi = option_bias()

    # Confidence Score
    score = 0

    if trend_bull or trend_bear: score += 25
    if momentum_bull or momentum_bear: score += 25
    if smart: score += 25
    if bias != "NEUTRAL": score += 25

    signal = "NO TRADE"

    if trend_bull and momentum_bull and smart == "BUY" and bias == "BULLISH":
        signal = "🔥 STRONG CE BUY"

    elif trend_bear and momentum_bear and smart == "SELL" and bias == "BEARISH":
        signal = "🔥 STRONG PE BUY"

    return signal, score, bias, latest

# ================= MAIN LOOP =================
def run():
    last_signal = None

    while True:
        try:
            df = fetch_data()
            df = apply_indicators(df)

            signal, score, bias, latest = strategy(df)

            atr = latest['ATR']
            hold = hold_time(atr)

            if signal != last_signal and signal != "NO TRADE" and score >= 75:
                msg = f"""
🚀 SIGNAL ALERT

📊 {signal}
💰 Price: {latest['close']}
📈 RSI: {round(latest['RSI'],2)}
📊 Bias: {bias}
⏱ Hold: {hold}
🎯 Confidence: {score}%

⚠️ Follow SL strictly
"""
                print(msg)
                send_telegram(msg)

                last_signal = signal

            time.sleep(60)

        except Exception as e:
            print("Error:", e)
            time.sleep(30)

# ================= START =================
run()