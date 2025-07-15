import yfinance as yf
import pandas as pd
import datetime
import streamlit as st

# Function to compute risk level
def compute_risk(vix, fx_vol):
    if vix > 20 and fx_vol > 0.01:
        return "High"
    elif vix > 15:
        return "Medium"
    else:
        return "Low"

# Set Streamlit config
st.set_page_config(page_title="Yen Carry Trade Risk Analysis", layout="centered")
st.title("📊 12-Year Carry Trade Risk Analysis (Weekly)")
st.caption("Filtering historical HIGH risk periods with corresponding VIX and UVXY values")

# Time range: last 12 years
end_date = datetime.datetime.today()
start_date = end_date - datetime.timedelta(weeks=52 * 12)

# Download weekly data
with st.spinner("Downloading weekly data from Yahoo Finance..."):
    vix_data = yf.download("^VIX", start=start_date, end=end_date, interval="1wk")["Close"]
    fx_data = yf.download("JPY=X", start=start_date, end=end_date, interval="1wk")["Close"]
    uvxy_data = yf.download("UVXY", start=start_date, end=end_date, interval="1wk")["Close"]

# Compute FX weekly volatility
fx_vol = fx_data.pct_change().rolling(window=2).std()

# Combine into one DataFrame
combined = pd.DataFrame({
    "VIX": vix_data,
    "FX_vol": fx_vol,
    "UVXY": uvxy_data
}).dropna()

# Calculate risk level
combined["Risk"] = combined.apply(lambda row: compute_risk(row["VIX"], row["FX_vol"]), axis=1)

# Filter rows where risk is HIGH
high_risk = combined[combined["Risk"] == "High"].copy()
high_risk.reset_index(inplace=True)
high_risk["Date"] = high_risk["Date"].dt.strftime("%Y-%m-%d")
high_risk["Yen Carry Trade Risk"] = "HIGH"

# Select and rename columns
display_df = high_risk[["Date", "VIX", "UVXY", "Yen Carry Trade Risk"]].copy()
display_df.columns = ["Date", "VIX Value", "UVXY Value", "Yen Carry Trade Risk"]

# Output to console
print("🔺 High Risk Weeks Over the Last 12 Years:")
print(display_df.to_string(index=False))

# Output to Streamlit
if not display_df.empty:
    st.success("High risk events retrieved successfully!")
    st.write("### 📅 Historical High Risk Events")
    st.dataframe(display_df, use_container_width=True)
else:
    st.warning("No HIGH risk events found in the 12-year period.")
