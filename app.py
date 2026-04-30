# app.py
import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime

st.set_page_config(page_title="AI Options Trader", layout="wide", page_icon="📈")

# Custom CSS for better look
st.markdown("""
<style>
.big-font { font-size:24px !important; font-weight: bold; }
.metric-card { background-color: #f0f2f6; border-radius: 10px; padding: 15px; }
.stButton button { width: 100%; }
</style>
""", unsafe_allow_html=True)

BACKEND_URL = st.secrets.get("BACKEND_URL", os.getenv("BACKEND_URL", "http://localhost:5000"))

# Auto-refresh every 30 seconds
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

# Force refresh every 30 sec
if time.time() - st.session_state.last_refresh > 30:
    st.session_state.last_refresh = time.time()
    st.rerun()

@st.cache_data(ttl=28)
def fetch_signal():
    try:
        resp = requests.get(f"{BACKEND_URL}/", timeout=8)
        resp.raise_for_status()
        return resp.json()
    except:
        return None

data = fetch_signal()

# Header
col1, col2, col3 = st.columns([1,3,1])
with col2:
    st.title("🚀 AI-Powered Options Trading")
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')} | Auto-refresh every 30s")

if data and "error" not in data:
    # Main metrics row
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("📊 NIFTY", f"{data['price']:.2f}", delta=None)
    with m2:
        color = "🟢" if "BUY CALL" in data['signal'] else "🔴" if "BUY PUT" in data['signal'] else "⚪"
        st.metric(f"{color} SIGNAL", data['signal'])
    with m3:
        st.metric("📈 OI Bias", data['oi_bias'].split()[0])
    with m4:
        st.metric("🧠 AI Bias", data['ai_bias'])

    st.markdown("---")
    
    # Risk & Levels
    colA, colB, colC, colD = st.columns(4)
    with colA:
        st.info(f"🎯 **Target**\n{data['target']:.2f}")
    with colB:
        st.warning(f"🛑 **Stop Loss**\n{data['sl']:.2f}")
    with colC:
        st.success(f"🔁 **Trailing SL**\n{data['trailing_sl']:.2f}")
    with colD:
        st.metric("⚡ ATM Strike", data['strike'])

    # Option OI Analysis
    st.subheader("📊 Option Open Interest Analysis")
    oi_df = pd.DataFrame({
        "Type": ["CALL OI", "PUT OI"],
        "Open Interest": [data['ce_oi'], data['pe_oi']]
    })
    col_chart, col_text = st.columns([2,1])
    with col_chart:
        st.bar_chart(oi_df.set_index("Type"))
    with col_text:
        if data['pe_oi'] > data['ce_oi']:
            st.success("✅ **Put OI > Call OI → Bullish sentiment**")
        else:
            st.error("❌ **Call OI > Put OI → Bearish sentiment**")
    
    # Additional analysis
    st.subheader("📈 30-Second Analysis")
    if data['signal'] == "BUY CALL":
        st.markdown("**Recommendation:** 🟢 Buy Call Option")
        st.progress(0.75, text="Probability: 75%")
        st.caption("Strategy: Target +40, SL -20, trail after +10")
    elif data['signal'] == "BUY PUT":
        st.markdown("**Recommendation:** 🔴 Buy Put Option")
        st.progress(0.70, text="Probability: 70%")
        st.caption("Strategy: Target -40, SL +20, trail after -10")
    else:
        st.markdown("**Recommendation:** ⚪ HOLD / No clear signal")
        st.progress(0.5, text="Probability: 50%")

    # TradingView Chart
    st.subheader("📉 Live NIFTY Chart")
    tv_html = """
    <iframe src="https://www.tradingview.com/widgetembed/?frameElementId=tradingview&symbol=NSE:NIFTY&interval=5&hidesidetoolbar=0&symboledit=1&saveimage=1&toolbarbg=f1f3f6&studies=RSI&theme=light&style=1&timezone=Etc/UTC" 
    width="100%" height="450" frameborder="0"></iframe>
    """
    st.components.v1.html(tv_html, height=480)
    
    # Auto-refresh countdown
    placeholder = st.empty()
    remaining = 30 - (time.time() - st.session_state.last_refresh)
    if remaining > 0:
        placeholder.info(f"🔄 Auto-refresh in {int(remaining)} seconds...")
    else:
        placeholder.info("🔄 Refreshing now...")

else:
    st.error("❌ Failed to fetch data from backend. Check API or network.")
    st.info("Backend URL: " + BACKEND_URL)
    if st.button("🔄 Retry Now"):
        st.rerun()
