# carry_trade_app.py (fixed: date conflict + sorting + color-coded display)

import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

st.set_page_config(page_title="Yen Carry Trade Risk", layout="centered")
st.title("📉 12-Month VIX & UVXY Carry Trade Risk Levels")

# Define date range
end_date = datetime.date.today()
start_date = end_date - datetime.timedelta(days=365)

# Download data
vix_data = yf.download("^VIX", start=start_date, end=end_date, interval="1wk")
uvxy_data = yf.download("UVXY", start=start_date, end=end_date, interval="1wk")

# Build DataFrame
df = pd.DataFrame(index=vix_data.index)
df["VIX"] = vix_data["Close"]
df["UVXY"] = uvxy_data["Close"]
df.dropna(inplace=True)

# Classify risk level
def classify_risk(vix):
    if vix > 20:
        return "HIGH"
    elif vix > 15:
        return "MEDIUM"
    else:
        return "LOW"

df["Risk"] = df["VIX"].apply(classify_risk)

# Reset index to fix 'Date' ambiguity and allow sorting
df = df.reset_index()
df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")

# Filter only HIGH and MEDIUM, sort by descending date
df = df[df["Risk"].isin(["HIGH", "MEDIUM"])]
df = df.sort_values("Date", ascending=False)

# Reorder columns
df = df[["Date", "VIX", "UVXY", "Risk"]]

# Style the dataframe
def highlight_row(row):
    if row["Risk"] == "HIGH":
        return ["background-color: #ffcccc"] * len(row)
    elif row["Risk"] == "MEDIUM":
        return ["background-color: #fff3cd"] * len(row)
    else:
        return [""] * len(row)

styled_df = df.style.apply(highlight_row, axis=1).format({
    "VIX": "{:.2f}",
    "UVXY": "{:.2f}"
})

# Display in browser
st.subheader("📅 Weekly Carry Trade Risk Flags (VIX > 15)")
st.dataframe(styled_df, use_container_width=True)

# Also print in console (optional)
print("\nCarry Trade Risk Levels - Last 12 Months (HIGH and MEDIUM only):")
print(df.to_string(index=False))
