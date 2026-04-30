import streamlit as st
import requests
import time

st.set_page_config(layout="wide")

st.title("🔥 AI SCALPING DASHBOARD")

API_URL = "https://trading-app-3-d8u0.onrender.com/"

placeholder = st.empty()

while True:
    data = requests.get(API_URL).json()

    if data["status"] == "OK":
        d = data["data"]

        with placeholder.container():
            col1, col2, col3 = st.columns(3)

            col1.metric("Signal", d['signal'])
            col2.metric("Win %", f"{d['probability']}%")
            col3.metric("Price", d['price'])

            st.write("📊 Option Bias:", d['oi_bias'])

            if d['signal'] == "NO TRADE":
                st.warning("No clear setup")
            else:
                st.success("High probability trade")

    time.sleep(5)
