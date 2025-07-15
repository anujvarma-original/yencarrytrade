# yencarrytrade.py (updated with sorting, chart, color-coded risk, and email alerts)
import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import smtplib
from email.mime.text import MIMEText
import os

# Set Streamlit page config
st.set_page_config(page_title="Yen Carry Trade Risk Monitor", layout="centered")
st.title("💴 Yen Carry Trade Risk - 12 Year Highs")

FLAG_FILE = "/tmp/last_alert_yencarrytrade.txt"

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

# Check if it's time to send alert
def should_send_alert():
    if not os.path.exists(FLAG_FILE):
        return True
    try:
        with open(FLAG_FILE, "r") as f:
            last_time = datetime.datetime.fromisoformat(f.read().strip())
        return (datetime.datetime.utcnow() - last_time).total_seconds() > 43200  # 12 hours
    except:
        return True

# Update alert timestamp
def update_alert_timestamp():
    with open(FLAG_FILE, "w") as f:
        f.write(datetime.datetime.utcnow().isoformat())

# Send email alert
def send_email_alert(risk_level, data_today):
    if not should_send_alert():
        return

    email_cfg = st.secrets["email"]

    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    metrics = "\n".join(
        f"{col}: {data_today[col].values[0]:.4f}" for col in data_today.columns
    )

    body = f"""⚠️ Carry Trade Risk Alert

Risk Level: {risk_level.upper()}
Timestamp: {timestamp}

📊 Market Inputs:
{metrics}
"""

    msg = MIMEText(body)
    msg["Subject"] = f"Carry Trade Risk Alert: {risk_level.upper()}"
    msg["From"] = email_cfg["from"]
    msg["To"] = email_cfg["to"]

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(email_cfg["from"], email_cfg["password"])
        server.send_message(msg)

    update_alert_timestamp()

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

# Display current risk
current_risk = data.iloc[0]["Risk"]
current_date = data.index[0].strftime("%Y-%m-%d")
st.subheader(f"📊 Current Risk as of {current_date}")

color_map = {"HIGH": "🔴 HIGH", "MEDIUM": "🟡 MEDIUM", "LOW": "🟢 LOW"}
st.markdown(f"### **Current Carry Trade Risk: {color_map.get(current_risk, current_risk)}**")

# Send email alert if eligible
send_email_alert(current_risk, data.iloc[[0]].copy())

# Display chart for last 12 months
st.subheader("📈 Risk Trend Over Last 12 Months")
data_12mo = data.sort_index().last("365D").copy()
data_12mo["Risk_Level"] = data_12mo["Risk"].map({"HIGH": 3, "MEDIUM": 2, "LOW": 1})

fig, ax = plt.subplots(figsize=(10, 3))
ax.plot(data_12mo.index, data_12mo["Risk_Level"], drawstyle='steps-post')
ax.set_yticks([1, 2, 3])
ax.set_yticklabels(["LOW", "MEDIUM", "HIGH"])
ax.set_title("Carry Trade Risk Levels Over Last 12 Months")
ax.set_xlabel("Date")
ax.set_ylabel("Risk Level")
plt.grid(True)
st.pyplot(fig)

# Display HIGH risk instances
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
