# yen_carry_trade_risk.py (fixed ambiguous Series truth value error)

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime

# Streamlit setup
st.set_page_config(page_title="Yen Carry Trade Risk", layout="centered")
st.title("\U0001F4B4 Current Yen Carry Trade Risk")

# Function to classify risk level
def classify_risk(vix, fx_vol):
    if vix > 20 and fx_vol > 0.01:
        return "HIGH"
    elif vix > 15:
        return "MEDIUM"
    else:
        return "LOW"

# Fetch recent data (last 3 months)
end = datetime.date.today()
start = end - datetime.timedelta(days=90)

vix_data = yf.download("^VIX", start=start, end=end, interval="1d")
fx_data = yf.download("JPY=X", start=start, end=end, interval="1d")

if vix_data.empty or fx_data.empty:
    st.error("Failed to download data from Yahoo Finance.")
    raise SystemExit("Data fetch failed")

# Calculate rolling volatility of FX
fx_data["log_ret"] = np.log(fx_data["Close"] / fx_data["Close"].shift(1))
fx_data["FX_vol"] = fx_data["log_ret"].rolling(window=20).std() * np.sqrt(252)

# Current VIX and FX Volatility (extract last value)
vix_today = vix_data["Close"].iloc[-1]
fx_vol_today = fx_data["FX_vol"].iloc[-1]

# Compute risk
risk_level = classify_risk(vix_today, fx_vol_today)

# Output
st.subheader("Today's Carry Trade Risk")
st.write("VIX:", round(vix_today, 2))
st.write("FX Volatility:", round(fx_vol_today, 4))
st.markdown("### Risk Level: **{}**".format(risk_level))

print("--- Yen Carry Trade Risk ---")
print("Date:", end)
print("VIX:", round(vix_today, 2))
print("FX Volatility:", round(fx_vol_today, 4))
print("Risk Level:", risk_level)
