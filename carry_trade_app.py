# carry_trade_app.py
import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import smtplib
from email.mime.text import MIMEText
import os

st.set_page_config(page_title="Yen Carry Trade Risk", layout="centered")
st.title("📉 12-Month VIX & UVXY Carry Trade Risk Levels")

# File to track alert history
ALERT_FLAG = "/tmp/last_yen_alert.txt"

# Define time range
end_date = datetime.date.today()
start_date = end_date - datetime.timedelta(days=365)

# Download data
vix_data = yf.download("^VIX", start=start_date, end=end_date, interval="1wk")
uvxy_data = yf.download("UVXY", start=start_date, end=end_date, interval="1wk")

# Prepare DataFrame
df = pd.DataFrame(index=vix_data.index)
df["VIX"] = vix_data["Close"]
df["UVXY"] = uvxy_data["Close"]
df.dropna(inplace=True)

# Risk classification
def classify_risk(vix):
    if vix > 20:
        return "HIGH"
    elif vix > 15:
        return "MEDIUM"
    else:
        return "LOW"

df["Risk"] = df["VIX"].apply(classify_risk)
df = df.reset_index()
df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")

# Compute current risk (most recent entry)
latest_row = df.iloc[-1]
current_risk = latest_row["Risk"]
current_date = latest_row["Date"]

# Display current risk
risk_color = {
    "HIGH": "red",
    "MEDIUM": "orange",
    "LOW": "green"
}
st.markdown(f"### 🟢 Current Carry Trade Risk: <span style='color:{risk_color[current_risk]}'>{current_risk}</span>", unsafe_allow_html=True)

# Sort by recent date and filter
filtered_df = df[df["Risk"].isin(["HIGH", "MEDIUM"])].sort_values("Date", ascending=False)
filtered_df = filtered_df[["Date", "VIX", "UVXY", "Risk"]]

# Style rows by risk
def highlight_risk(row):
    if row["Risk"] == "HIGH":
        return ["background-color: #ffcccc"] * len(row)
    elif row["Risk"] == "MEDIUM":
        return ["background-color: #fff3cd"] * len(row)
    else:
        return [""] * len(row)

styled_df = filtered_df.style.apply(highlight_risk, axis=1).format({
    "VIX": "{:.2f}",
    "UVXY": "{:.2f}"
})

# Show in Streamlit
st.subheader("📅 Recent HIGH & MEDIUM Risk Events")
st.dataframe(styled_df, use_container_width=True)

# Print to console
print("\nCarry Trade Risk - Recent HIGH and MEDIUM Events:")
print(filtered_df.to_string(index=False))

# ---- Email Alert for HIGH risk ----
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

    email_cfg = st.secrets["email"]  # ensure these secrets exist: from, to, password

    body = f"""🚨 Carry Trade Risk Alert

Risk Level: {risk_level}
Date: {date_str}
VIX: {vix_val:.2f}
UVXY: {uvxy_val:.2f}
"""

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

# Trigger alert
send_email_alert(current_risk, current_date, latest_row["VIX"], latest_row["UVXY"])
