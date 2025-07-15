# yencarrytrade.py (updated with sorting and color-coded risk)
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

# Function to color risk levels
def risk_color(risk):
    if risk == "HIGH":
        return "background-color: #ffcccc"  # Red
    elif risk == "MEDIUM":
        return "background-color: #ffffcc"  # Yellow
    elif risk == "LOW":
        return "background-color: #ccffcc"  # Green
    else:
        return ""

# Download historical data
end = datetime.date.today()
start = end - datetime.timedelta(days=365 * 12)

vix_data = yf.download("^VIX", start=start, end=end, interval="1wk")
uvxy_data = yf.download("UVXY", start=start, end=end, interval="1wk")
fx_data = yf.download("JPY=X", start=start, end=end, interval="1wk")

if vix_data.empty or fx_data.empty or uvxy_data.empty:
    st.error("Failed to download market data.")
    st.stop()

# Calculate FX volatility
fx_data["FX_vol"] = fx_data["Close"].pct_change().rolling(window=4).std()

# Align and merge data
data = pd.DataFrame(index=vix_data.index)
data["VIX"] = vix_data["Close"]
data["UVXY"] = uvxy_data["Close"]
data["FX_vol"] = fx_data["FX_vol"]
data = data.dropna()

# Compute risk level
data["Risk"] = data.apply(lambda row: compute_risk(row["VIX"], row["FX_vol"]), axis=1)

# Sort by most recent date
data = data.sort_index(ascending=False)

# Display most recent week's risk with color
current_risk = data.iloc[0]["Risk"]
current_date = data.index[0].strftime("%Y-%m-%d")
st.subheader(f"📊 Current Risk as of {current_date}")

color_map = {"HIGH": "🔴 HIGH", "MEDIUM": "🟡 MEDIUM", "LOW": "🟢 LOW"}
st.markdown(f"### **Current Carry Trade Risk: {color_map.get(current_risk, current_risk)}**")

# Filter HIGH risk only and display
data_high = data[data["Risk"] == "HIGH"].copy()
data_high.reset_index(inplace=True)
data_high.rename(columns={"index": "Date"}, inplace=True)
data_high["Date"] = data_high["Date"].dt.strftime("%Y-%m-%d")

if not data_high.empty:
    st.subheader("📅 All Dates With HIGH Risk (Last 12 Years)")
    styled_df = data_high[["Date", "VIX", "UVXY", "FX_vol", "Risk"]].style.applymap(risk_color, subset=["Risk"])
    st.dataframe(styled_df, use_container_width=True)
else:
    st.info("No HIGH risk levels detected in the past 12 years.")
