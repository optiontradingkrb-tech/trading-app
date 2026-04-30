import streamlit as st
import requests

st.set_page_config(layout="wide")

st.title("🔥 AI TRADING PRO DASHBOARD")

API = "https://trading-app-4-n937.onrender.com/"

try:
    data = requests.get(API, timeout=10).json()

    if "data" in data:
        d = data["data"]

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Signal", d['signal'])
        col2.metric("Win %", f"{d['probability']}%")
        col3.metric("Price", d['price'])
        col4.metric("Strike", d['strike'])

        st.divider()

        col5, col6, col7 = st.columns(3)
        col5.metric("SL", d['sl'])
        col6.metric("Target", d['target'])
        col7.metric("Trailing SL", d['trailing_sl'])

        st.divider()

        st.success(f"OI Bias: {d['oi_bias']}")
        st.info(f"SMC: {d['smc']}")
        st.warning(f"Pullback: {d['pullback']}")

        st.write(f"LSTM: {d['lstm']}")
        st.write(f"Backtest Accuracy: {d['backtest_acc']}%")

        st.components.v1.html("""
        <iframe src="https://s.tradingview.com/widgetembed/?symbol=NSE:NIFTY&interval=5&theme=dark"
        width="100%" height="500"></iframe>
        """, height=500)

    else:
        st.error("API format issue")

except Exception as e:
    st.error(f"Error: {e}")
