# enhanced_carry_trade_risk.py
import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import smtplib
from email.mime.text import MIMEText
import os
import numpy as np
import requests

st.set_page_config(page_title="Yen Carry Trade Risk", layout="centered")
st.title("📉 Enhanced Yen Carry Trade Risk Levels")

ALERT_FLAG = "/tmp/last_yen_alert.txt"
end_date = datetime.date.today()
start_date = end_date - datetime.timedelta(days=365)

# Fetch Japan GDP growth directly from FRED API
def get_japan_gdp_growth(api_key):
    try:
        url = f"https://api.stlouisfed.org/fred/series/observations?series_id=JPNNGDP&api_key={api_key}&file_type=json"
        response = requests.get(url)
        data = response.json()["observations"]
        if len(data) >= 5:
            latest = float(data[-1]["value"])
            previous = float(data[-5]["value"])
            return ((latest - previous) / previous) * 100
    except Exception as e:
        st.warning(f"⚠️ GDP API fallback used: {e}")
    return 1.1  # fallback value

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

if "Close" in usd_jpy_data and not usd_jpy_data["Close"].empty:
    df["USD_JPY"] = usd_jpy_data["Close"]
else:
    st.warning("⚠️ USD/JPY data missing. Using fallback value of 145.")
    df["USD_JPY"] = pd.Series([145] * len(df), index=df.index)

# Clean and validate
df.dropna(inplace=True)
if df.empty:
    st.error("📉 Final dataset is empty. Check for failed data sources.")
    st.stop()

# Calculate Interest Rate Differential
df["Rate_Diff"] = df["US_Rate"] - df["Japan_Rate"]

# Get Japan GDP growth
latest_gdp_growth = get_japan_gdp_growth(st.secrets["fred"]["api_key"])

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

# 📊 Inputs + thresholds used for classification
st.subheader("📊 Inputs Used for Risk Analysis (with Triggers)")

# Define thresholds for HIGH risk
thresholds = {
    "VIX": {"value": 20, "direction": "above"},
    "USD/JPY": {"value": 135, "direction": "below"},
    "Rate Differential (US - Japan)": {"value": 0, "direction": "below"},
    "Japan GDP Growth (YoY)": {"value": 1, "direction": "below"},
    "US Inflation (Est.)": {"value": 3, "direction": "above"},
    "BoJ Policy Stance": {"value": "Hawkish"}
}

# Extract values from latest row
input_values = {
    "VIX": latest_row["VIX"],
    "USD/JPY": latest_row["USD_JPY"],
    "Rate Differential (US - Japan)": latest_row["Rate_Diff"],
    "Japan GDP Growth (YoY)": latest_gdp_growth,
    "US Inflation (Est.)": latest_inflation,
    "BoJ Policy Stance": boj_policy_stance
}

# Determine trigger status
trigger_flags = {}
for key, val in input_values.items():
    if key == "BoJ Policy Stance":
        trigger_flags[key] = "⚠️" if val == thresholds[key]["value"] else ""
    else:
        if thresholds[key]["direction"] == "above":
            trigger_flags[key] = "⚠️" if val > thresholds[key]["value"] else ""
        elif thresholds[key]["direction"] == "below":
            trigger_flags[key] = "⚠️" if val < thresholds[key]["value"] else ""

# Construct DataFrame for display
data_rows = []
for key in input_values:
    data_rows.append({
        "Factor": key,
        "Value": f"{input_values[key]:.2f}" if isinstance(input_values[key], (float, int)) else input_values[key],
        "Threshold": f"{thresholds[key]['direction']} {thresholds[key]['value']}" if key != "BoJ Policy Stance" else thresholds[key]["value"],
        "Triggered": trigger_flags[key]
    })

input_df = pd.DataFrame(data_rows)
st.dataframe(input_df.style.apply(
    lambda row: ['background-color: #ffcccc' if row.Triggered == "⚠️" else '' for _ in row],
    axis=1
))

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

    try:
        body = f"""🚨 Carry Trade Risk Alert\n\nRisk Level: {risk_level}\nDate: {date_str}\nVIX: {vix_val:.2f}\nUVXY: {uvxy_val:.2f}\n"""
        # Plaintext fallback without emoji
        fallback_body = f"Carry Trade Risk Alert\n\nRisk Level: {risk_level}\nDate: {date_str}\nVIX: {vix_val:.2f}\nUVXY: {uvxy_val:.2f}"
        try:
            msg = MIMEText(body, _charset="utf-8")
        except UnicodeEncodeError:
            msg = MIMEText(fallback_body, _charset="utf-8")

        msg["Subject"] = f"Carry Trade Risk Alert - {risk_level} on {date_str}"
        msg["From"] = email_cfg["from"]
        msg["To"] = email_cfg["to"]

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(email_cfg["from"], email_cfg["password"])
            server.send_message(msg)
        update_alert_timestamp()
        st.success("📧 Alert email sent for HIGH risk.")
    except Exception as e:
        st.error(f"Failed to send email: {e}")

send_email_alert(current_risk, current_date, latest_row["VIX"], latest_row["UVXY"])
