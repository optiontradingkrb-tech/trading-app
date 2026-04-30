import streamlit as st
import requests

st.title("🔥 LIVE TRADING DASHBOARD")

API_URL = "PASTE_YOUR_RENDER_API_URL"

data = requests.get(API_URL).json()

st.metric("Signal", data['signal'])
st.metric("Win Probability", f"{data['probability']}%")
st.metric("Price", data['price'])