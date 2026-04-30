# bot.py
import os
import logging
import requests
import pandas as pd
import numpy as np
from flask import Flask, jsonify
from datetime import datetime, timedelta
from functools import lru_cache
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Cache for option chain (30 seconds)
_cache_oi = {'data': None, 'expiry': 0}

# Telegram
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
last_signal = None

def send_telegram(msg):
    if TELEGRAM_TOKEN and CHAT_ID:
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                          json={"chat_id": CHAT_ID, "text": msg}, timeout=3)
        except:
            pass

def get_nifty_price():
    """Get current price only (fast)"""
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI"
        params = {"interval": "1m", "range": "1d"}
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, params=params, timeout=5)
        return resp.json()['chart']['result'][0]['meta']['regularMarketPrice']
    except:
        return None

def get_ai_bias(price):
    """Calculate MA10 and RSI from daily data"""
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI"
        params = {"interval": "1d", "range": "1mo"}
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, params=params, timeout=5)
        data = resp.json()
        closes = [c for c in data['chart']['result'][0]['indicators']['quote'][0]['close'] if c]
        if len(closes) < 20:
            return "NEUTRAL"
        series = pd.Series(closes[-30:])
        ma10 = series.rolling(10).mean().iloc[-1]
        delta = series.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_val = rsi.iloc[-1]
        if price and price > ma10 and rsi_val > 50:
            return "BULLISH"
        else:
            return "BEARISH"
    except:
        return "NEUTRAL"

def get_option_chain(spot):
    """Cached option chain (30 sec TTL)"""
    now = time.time()
    if _cache_oi['data'] and (now - _cache_oi['expiry']) < 30:
        return _cache_oi['data']
    try:
        sess = requests.Session()
        sess.headers.update({'User-Agent': 'Mozilla/5.0'})
        sess.get('https://www.nseindia.com', timeout=5)
        resp = sess.get('https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY', timeout=5)
        data = resp.json()
        records = data['records']['data']
        total_ce = sum(item.get('CE', {}).get('openInterest', 0) for item in records)
        total_pe = sum(item.get('PE', {}).get('openInterest', 0) for item in records)
        strikes = [item['strikePrice'] for item in records if 'strikePrice' in item]
        atm = min(strikes, key=lambda x: abs(x - spot)) if strikes else round(spot/50)*50
        if total_pe > total_ce:
            bias = "PUT WRITING (Bullish)"
        elif total_ce > total_pe:
            bias = "CALL WRITING (Bearish)"
        else:
            bias = "NEUTRAL"
        result = (bias, atm, total_ce, total_pe)
        _cache_oi['data'] = result
        _cache_oi['expiry'] = now
        return result
    except:
        return ("ERROR", round(spot/50)*50, 0, 0)

@app.route('/')
def signal():
    try:
        price = get_nifty_price()
        if not price:
            return jsonify({"error": "Price fetch failed"}), 503
        ai_bias = get_ai_bias(price)
        oi_bias, atm, ce_oi, pe_oi = get_option_chain(price)
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
        sl = round(price - 20, 2)
        target = round(price + 40, 2)
        trail = round(price - 10, 2)
        global last_signal
        if signal != last_signal and signal != "HOLD":
            send_telegram(f"🚀 {signal}\nPrice: {price}\nTarget: {target}\nSL: {sl}")
            last_signal = signal
        return jsonify({
            "signal": signal,
            "price": round(price, 2),
            "strike": atm,
            "sl": sl,
            "target": target,
            "trailing_sl": trail,
            "oi_bias": oi_bias,
            "ai_bias": ai_bias,
            "probability": 65 if signal != "HOLD" else 50,
            "ce_oi": int(ce_oi),
            "pe_oi": int(pe_oi)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
