# enhanced_carry_trade_risk.py
import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import smtplib
from email.mime.text import MIMEText
import os
import numpy as np
from fredapi import Fred

st.set_page_config(page_title="Yen Carry Trade Risk", layout="centered")
st.title("📉 Enhanced Yen Carry Trade Risk Levels")

ALERT_FLAG = "/tmp/last_yen_alert.txt"
end_date = datetime.date.today()
start_date = end_date - datetime.timedelta(days=365)

# FRED API setup
fred = Fred(api_key=st.secrets["fred"]["api_key"])

# Download market data
def safe_download(ticker, *args, **kwargs):
    try:
        df = yf.download(ticker, *args, **kwargs)
        if df.empty:
            st.warning(f"⚠️ Data for {ticker} is empty.")
        return df
    except Exception as e:
        st.warning(f"⚠️ Failed to download {ticker}: {e}")
        return pd.DataFrame()

vix_data = safe_download("^VIX", start=start_date, end=end_date, interval="1wk")
uvxy_data = safe_download("UVXY", start=start_date, end=end_date, interval="1wk")
us_rate = safe_download("^IRX", start=start_date, end=end_date, interval="1wk")

# Attempt to get Japan Rate
japan_rate_data = safe_download("JP3YT=RR", start=start_date, end=end_date, interval="1wk")
if "Close" in japan_rate_data and not japan_rate_data["Close"].empty:
    japan_rate = japan_rate_data["Close"]
else:
    st.warning("⚠️ Japan rate data not available. Using fallback value of 0.1%.")
    japan_rate = pd.Series([0.1] * len(vix_data), index=vix_data.index)

usd_jpy_data = safe_download("JPY=X", start=start_date, end=end_date, interval="1wk")

# Prepare DataFrame
df = pd.DataFrame(index=vix_data.index)
df["VIX"] = vix_data["Close"]
df["UVXY"] = uvxy_data["Close"]
df["US_Rate"] = us_rate["Close"]
df["Japan_Rate"] = japan_rate
if "Close" in usd_jpy_data:
    df["USD_JPY"] = usd_jpy_data["Close"]
df.dropna(inplace=True)

# Stop early if data is empty
if df.empty:
    st.error("📉 No data available to compute risk — likely due to missing data sources.")
    st.stop()

# Calculate Interest Rate Differential
df["Rate_Diff"] = df["US_Rate"] - df["Japan_Rate"]

# Get Japan GDP growth from FRED (fallback value included)
try:
    gdp_series = fred.get_series('JPNNGDP')
    latest_gdp_growth = (gdp_series[-1] - gdp_series[-5]) / gdp_series[-5] * 100
except Exception as e:
    latest_gdp_growth = 1.1
    st.warning(f"GDP data fallback due to error: {e}")

# Static macro indicators
latest_inflation = 2.5  # Replace with API if needed
boj_policy_stance = "Dovish"  # Options: Dovish, Hawkish

# Enhanced Risk Classification
def classify_enhanced_risk(vix, rate_diff, usd_jpy, inflation, gdp, policy_stance):
    if vix > 20 or rate_diff < 0 or usd_jpy < 135 or inflation > 3 or gdp < 1 or policy_stance == "Hawkish":
        return "HIGH"
    elif vix > 15 or rate_diff < 1 or usd_jpy < 140:
        return "MEDIUM"
    else:
        return "LOW"

df = df.reset_index()
df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
df["Risk"] = df.apply(lambda row: classify_enhanced_risk(
    row["VIX"],
    row["Rate_Diff"],
    row["USD_JPY"],
    latest_inflation,
    latest_gdp_growth,
    boj_policy_stance
), axis=1)

latest_row = df.iloc[-1]
current_risk = latest_row["Risk"]
current_date = latest_row["Date"]

risk_color = {
    "HIGH": "red",
    "MEDIUM": "orange",
    "LOW": "green"
}

st.markdown(f"### 🟢 Current Carry Trade Risk: <span style='color:{risk_color[current_risk]}'>{current_risk}</span>", unsafe_allow_html=True)

filtered_df = df[df["Risk"].isin(["HIGH", "MEDIUM"])].sort_values("Date", ascending=False)
filtered_df = filtered_df[["Date", "VIX", "UVXY", "USD_JPY", "Rate_Diff", "Risk"]]

def highlight_risk(row):
    if row["Risk"] == "HIGH":
        return ["background-color: #ffcccc"] * len(row)
    elif row["Risk"] == "MEDIUM":
        return ["background-color: #fff3cd"] * len(row)
    else:
        return [""] * len(row)

styled_df = filtered_df.style.apply(highlight_risk, axis=1).format({
    "VIX": "{:.2f}",
    "UVXY": "{:.2f}",
    "USD_JPY": "{:.2f}",
    "Rate_Diff": "{:.2f}"
})

st.subheader("🗓️ Recent HIGH & MEDIUM Risk Events")
st.dataframe(styled_df, use_container_width=True)

print("\nCarry Trade Risk - Recent HIGH and MEDIUM Events:")
print(filtered_df.to_string(index=False))

def should_send_alert():
    if not os.path.exists(ALERT_FLAG):
        return True
    try:
        with open(ALERT_FLAG, "r") as f:
            last_time = datetime.datetime.fromisoformat(f.read().strip())
        return (datetime.datetime.utcnow() - last_time).total_seconds() > 43200
    except:
        return True

def update_alert_timestamp():
    with open(ALERT_FLAG, "w") as f:
        f.write(datetime.datetime.utcnow().isoformat())

def send_email_alert(risk_level, date_str, vix_val, uvxy_val):
    if risk_level != "HIGH" or not should_send_alert():
        return

    email_cfg = st.secrets["email"]

    body = f"""\ud83d\udea8 Carry Trade Risk Alert\n\nRisk Level: {risk_level}\nDate: {date_str}\nVIX: {vix_val:.2f}\nUVXY: {uvxy_val:.2f}\n"""

    msg = MIMEText(body)
    msg["Subject"] = f"Carry Trade Risk Alert - {risk_level} on {date_str}"
    msg["From"] = email_cfg["from"]
    msg["To"] = email_cfg["to"]

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(email_cfg["from"], email_cfg["password"])
            server.send_message(msg)
        update_alert_timestamp()
        st.success("📧 Alert email sent for HIGH risk.")
    except Exception as e:
        st.error(f"Failed to send email: {e}")

send_email_alert(current_risk, current_date, latest_row["VIX"], latest_row["UVXY"])
