# bot.py
import os
import json
import logging
import requests
import pandas as pd
import numpy as np
from flask import Flask, jsonify
from datetime import datetime, timedelta
import time

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ---------- Flask App ----------
app = Flask(__name__)

# ---------- Telegram ----------
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
last_signal_sent = None

def send_telegram_alert(message):
    """Send alert via Telegram if credentials exist."""
    if TELEGRAM_TOKEN and CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
            requests.post(url, json=payload, timeout=5)
            logger.info("Telegram alert sent")
        except Exception as e:
            logger.error(f"Telegram error: {e}")
    else:
        logger.info("Telegram credentials missing, skipping alert")

# ---------- Market Data (Yahoo Finance via requests) ----------
def get_nifty_price_and_history():
    """
    Fetch current NIFTY price and historical daily closes for MA/RSI.
    Returns: (current_price, ma10, rsi, ai_bias)
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    # Get current price (1min interval)
    try:
        url_curr = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI"
        params_curr = {"interval": "1m", "range": "1d"}
        resp_curr = requests.get(url_curr, headers=headers, params=params_curr, timeout=10)
        data = resp_curr.json()
        current_price = data['chart']['result'][0]['meta']['regularMarketPrice']
    except Exception as e:
        logger.error(f"Failed to fetch current price: {e}")
        current_price = None

    # Get historical daily data for MA/RSI
    try:
        params_hist = {"interval": "1d", "range": "1mo"}
        resp_hist = requests.get(url_curr, headers=headers, params=params_hist, timeout=10)
        hist_data = resp_hist.json()
        quotes = hist_data['chart']['result'][0]['indicators']['quote'][0]
        closes = [c for c in quotes['close'] if c is not None]
        timestamps = hist_data['chart']['result'][0]['timestamp']
        closes = closes[-min(30, len(closes)):]  # last 30 days max
        if len(closes) < 20:
            logger.warning("Insufficient historical data for RSI/MA")
            return current_price, None, None, "NEUTRAL"

        series = pd.Series(closes)
        # MA10
        ma10 = series.rolling(window=10).mean().iloc[-1]
        # RSI 14
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_value = rsi.iloc[-1]

        # AI Bias
        if current_price and ma10 and rsi_value > 50 and current_price > ma10:
            ai_bias = "BULLISH"
        else:
            ai_bias = "BEARISH"

        return current_price, ma10, rsi_value, ai_bias
    except Exception as e:
        logger.error(f"Historical data error: {e}")
        return current_price, None, None, "NEUTRAL"

# ---------- NSE Option Chain ----------
def get_nse_option_chain(spot_price):
    """
    Fetch real option chain, compute total Put OI, Call OI and ATM strike.
    Returns: (oi_bias, atm_strike, total_call_oi, total_put_oi)
    """
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        })
        # First hit homepage to set cookies
        session.get('https://www.nseindia.com', timeout=10)
        url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
        response = session.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        records = data['records']['data']
        total_ce_oi = 0
        total_pe_oi = 0
        strikes = []
        for item in records:
            if 'CE' in item and 'openInterest' in item['CE']:
                total_ce_oi += item['CE']['openInterest']
            if 'PE' in item and 'openInterest' in item['PE']:
                total_pe_oi += item['PE']['openInterest']
            if 'strikePrice' in item:
                strikes.append(item['strikePrice'])

        # OI Bias
        if total_pe_oi > total_ce_oi:
            oi_bias = "PUT WRITING (Bullish)"
        elif total_ce_oi > total_pe_oi:
            oi_bias = "CALL WRITING (Bearish)"
        else:
            oi_bias = "NEUTRAL"

        # ATM Strike (nearest to spot)
        atm_strike = min(strikes, key=lambda x: abs(x - spot_price)) if strikes else None
        return oi_bias, atm_strike, total_ce_oi, total_pe_oi
    except Exception as e:
        logger.error(f"Option chain error: {e}")
        return "ERROR", None, 0, 0

# ---------- Signal Logic ----------
def generate_signal(ai_bias, oi_bias, current_price, atm_strike):
    """Combine biases and return trade signal."""
    if ai_bias == "BULLISH" and "Bullish" in oi_bias:
        signal = "BUY CALL"
    elif ai_bias == "BEARISH" and "Bearish" in oi_bias:
        signal = "BUY PUT"
    elif ai_bias == "BULLISH":
        signal = "BUY CALL"
    elif ai_bias == "BEARISH":
        signal = "BUY PUT"
    else:
        signal = "HOLD"

    # Risk management levels
    sl = round(current_price - 20, 2) if current_price else 0
    target = round(current_price + 40, 2) if current_price else 0
    trailing_sl = round(current_price - 10, 2) if current_price else 0
    return signal, sl, target, trailing_sl

# ---------- Flask API Endpoint ----------
@app.route('/', methods=['GET'])
def get_signal():
    global last_signal_sent
    try:
        # Get market data
        current_price, ma10, rsi, ai_bias = get_nifty_price_and_history()
        if current_price is None:
            return jsonify({"error": "Failed to fetch NIFTY price"}), 500

        # Get option chain
        oi_bias, atm_strike, ce_oi, pe_oi = get_nse_option_chain(current_price)
        if atm_strike is None:
            atm_strike = round(current_price / 50) * 50  # fallback

        # Combine signals
        signal, sl, target, trailing_sl = generate_signal(ai_bias, oi_bias, current_price, atm_strike)

        # Telegram alert if signal changed
        if signal != last_signal_sent and signal != "HOLD":
            msg = f"🚀 NEW SIGNAL: {signal}\n💰 Price: {current_price}\n🎯 Target: {target}\n🛑 SL: {sl}\n📊 AI: {ai_bias}\n📈 OI: {oi_bias}"
            send_telegram_alert(msg)
            last_signal_sent = signal

        response = {
            "signal": signal,
            "price": round(current_price, 2),
            "strike": atm_strike,
            "sl": sl,
            "target": target,
            "trailing_sl": trailing_sl,
            "oi_bias": oi_bias,
            "ai_bias": ai_bias,
            "probability": 60  # fixed for demo
        }
        return jsonify(response)
    except Exception as e:
        logger.exception("Unexpected error")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)