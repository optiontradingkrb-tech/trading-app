# app.py
import streamlit as st
import requests
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Options Trading Dashboard", layout="wide")

# Backend API URL (set env variable BACKEND_URL on Render)
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:5000")

st.title("📈 AI-Powered Options Trading System")
st.markdown("**Real-time NIFTY signals based on Option Chain + AI (MA/RSI)**")

# Fetch data from Flask API
@st.cache_data(ttl=30)  # refresh every 30 sec
def fetch_signal():
    try:
        resp = requests.get(f"{BACKEND_URL}/", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Failed to fetch signal: {e}")
        return None

data = fetch_signal()

if data and "error" not in data:
    col1, col2 = st.columns(2)

    with col1:
        st.metric("📊 NIFTY Price", f"{data['price']:.2f}")
        st.metric("🎯 Signal", data['signal'], delta="Action")
        st.metric("🛑 Stop Loss", f"{data['sl']:.2f}")
        st.metric("🎯 Target", f"{data['target']:.2f}")
        st.metric("🔁 Trailing SL", f"{data['trailing_sl']:.2f}")

    with col2:
        st.metric("📈 OI Bias", data['oi_bias'])
        st.metric("🧠 AI Bias", data['ai_bias'])
        st.metric("📊 Confidence", f"{data['probability']}%")
        st.metric("⚡ ATM Strike", data['strike'])

    # TradingView Chart Embed
    st.subheader("Live NIFTY Chart")
    tv_widget = """
    <iframe src="https://www.tradingview.com/widgetembed/?frameElementId=tradingview_123&symbol=NSE:NIFTY&interval=5&hidesidetoolbar=0&symboledit=1&saveimage=1&toolbarbg=f1f3f6&studies=RSI&theme=light&style=1&timezone=Etc/UTC" 
    width="100%" height="500" frameborder="0" allowtransparency="true" scrolling="no"></iframe>
    """
    st.components.v1.html(tv_widget, height=520)

    # Timestamp
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Auto-refresh every 30s")
else:
    st.error("No signal data available. Check backend API.")

# Sidebar with info
st.sidebar.markdown("## ℹ️ Strategy Logic")
st.sidebar.info(
    """
    - **AI**: Price > MA10 & RSI > 50 → BULLISH ; else BEARISH
    - **Option OI**: PUT OI > CALL OI → Bullish ; CALL OI > PUT OI → Bearish
    - **Final Signal**: BUY CALL if both Bullish, BUY PUT if both Bearish, else AI bias
    - **Risk Management**: SL = Price-20, Target = Price+40, Trailing = Price-10
    """
)
st.sidebar.markdown("---")
st.sidebar.markdown("Built with Flask + Streamlit + NSE Option Chain")