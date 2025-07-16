# carry_trade_app.py (final correction to email metrics formatting)
import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import smtplib
from email.mime.text import MIMEText
import os
import matplotlib.pyplot as plt

st.set_page_config(page_title="Yen Carry Trade Risk Monitor", layout="centered")
st.title("\U0001F4B4 Yen Carry Trade Risk - Live Tracker")
FLAG_FILE = "/tmp/last_alert_yencarrytrade.txt"

def compute_risk(vix, fx_vol):
    if vix > 20 and fx_vol > 0.01:
        return "HIGH"
    elif vix > 15:
        return "MEDIUM"
    else:
        return "LOW"

def should_send_alert():
    if not os.path.exists(FLAG_FILE):
        return True
    try:
        with open(FLAG_FILE, "r") as f:
            last_time = datetime.datetime.fromisoformat(f.read().strip())
        return (datetime.datetime.utcnow() - last_time).total_seconds() > 43200
    except:
        return True

def update_alert_timestamp():
    with open(FLAG_FILE, "w") as f:
        f.write(datetime.datetime.utcnow().isoformat())

def send_email_alert(risk_level, data_today):
    if not should_send_alert():
        return

    email_cfg = st.secrets["email"]
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    if isinstance(data_today, pd.DataFrame):
        data_today = data_today.iloc[0]

    metrics = []
    for col, val in data_today.items():
        try:
            val_formatted = f"{float(val):.4f}"
        except (ValueError, TypeError):
            val_formatted = str(val)
        metrics.append(f"{col}: {val_formatted}")

    metrics_str = "\n".join(metrics)

    body = f"""\u26a0\ufe0f Carry Trade Risk Alert

Risk Level: {risk_level.upper()}
Timestamp: {timestamp}

\ud83d\udcca Market Inputs:
{metrics_str}
"""

    msg = MIMEText(body)
    msg["Subject"] = f"Carry Trade Risk Alert: {risk_level.upper()}"
    msg["From"] = email_cfg["from"]
    msg["To"] = email_cfg["to"]

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(email_cfg["from"], email_cfg["password"])
        server.send_message(msg)

    update_alert_timestamp()
