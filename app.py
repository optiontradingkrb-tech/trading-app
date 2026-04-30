import streamlit as st
import requests

st.set_page_config(layout="wide")

st.title("🔥 AI SCALPING DASHBOARD")

API_URL = "https://trading-app-4-n937.onrender.com/"

# Refresh button
if st.button("🔄 Refresh"):
    st.rerun()

try:
    data = requests.get(API_URL, timeout=10).json()

    if data["status"] == "OK":
        d = data["data"]

        col1, col2, col3 = st.columns(3)

        col1.metric("Signal", d['signal'])
        col2.metric("Win %", f"{d['probability']}%")
        col3.metric("Price", d['price'])

        st.write("📊 Option Bias:", d['oi_bias'])

        if d['signal'] == "NO TRADE":
            st.warning("No clear setup")
        else:
            st.success("High probability trade")

    else:
        st.error(data["message"])

except Exception as e:
    st.error(f"Error: {e}")
