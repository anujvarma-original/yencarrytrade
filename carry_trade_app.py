# yencarrytrade.py (patched for scalar value DataFrame fix and historical high-risk tracking)
import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import matplotlib.pyplot as plt

# Set Streamlit page config
st.set_page_config(page_title="Yen Carry Trade Risk Monitor", layout="centered")
st.title("💴 Yen Carry Trade Risk - 12 Year Highs")

# Function to compute risk level
def compute_risk(vix, fx_vol):
    if vix > 20 and fx_vol > 0.01:
        return "HIGH"
    elif vix > 15:
        return "MEDIUM"
    else:
        return "LOW"

# Download historical data for VIX and USD/JPY
end = datetime.date.today()
start = end - datetime.timedelta(days=365 * 12)

vix_data = yf.download("^VIX", start=start, end=end, interval="1wk")
uvxy_data = yf.download("UVXY", start=start, end=end, interval="1wk")
fx_data = yf.download("JPY=X", start=start, end=end, interval="1wk")

if vix_data.empty or fx_data.empty or uvxy_data.empty:
    st.error("Failed to download market data.")
    st.stop()

# Calculate FX weekly returns as volatility proxy
fx_data["FX_vol"] = fx_data["Close"].pct_change().rolling(window=4).std()

# Align all dataframes on date index
data = pd.DataFrame(index=vix_data.index)
data["VIX"] = vix_data["Close"]
data["UVXY"] = uvxy_data["Close"]
data["FX_vol"] = fx_data["FX_vol"]
data = data.dropna()

# Compute risk level for each week
data["Risk"] = data.apply(lambda row: compute_risk(row["VIX"], row["FX_vol"]), axis=1)

# Filter only HIGH risk dates
data_high = data[data["Risk"] == "HIGH"]

# Build display table for HIGH risk instances
display_rows = []
for idx, row in data_high.iterrows():
    display_rows.append({
        "Date": idx.strftime("%Y-%m-%d"),
        "VIX Value": round(row["VIX"], 2),
        "UVXY Value": round(row["UVXY"], 2),
        "Yen Carry Trade Risk": "HIGH"
    })

# Convert to DataFrame
risk_df = pd.DataFrame(display_rows)

# Show the table in Streamlit and console
if not risk_df.empty:
    st.subheader("📅 All Dates With HIGH Risk (Last 12 Years)")
    st.dataframe(risk_df, use_container_width=True)
    print("\nYen Carry Trade - HIGH Risk Events")
    print(risk_df.to_string(index=False))
else:
    st.info("No HIGH risk levels detected in the past 12 years.")
    print("No HIGH risk levels detected.")
