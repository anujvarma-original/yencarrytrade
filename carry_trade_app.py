# carry_trade_app.py
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from sklearn.ensemble import RandomForestClassifier
from joblib import load
from twilio.rest import Client

# Load or simulate model (replace with actual trained model path)
def load_model():
    try:
        return load("carry_model.joblib")
    except:
        # Simulated placeholder classifier
        class DummyModel:
            def predict(self, X):
                return [
                    "High" if float(vix) > 20 and float(vol) > 0.01 else "Low"
                    for vix, vol in zip(X["VIX"].values, X["FX_vol"].values)
                ]
        return DummyModel()

# Get current market data
def fetch_data():
    fx = yf.download("JPY=X", period="90d", interval="1d")["Close"]
    vix = yf.download("^VIX", period="90d", interval="1d")["Close"]

    log_returns = np.log(fx / fx.shift(1))
    fx_vol = log_returns.rolling(window=30).std().iloc[-1] * np.sqrt(252)

    jpy_rate = 0.1  # Simulated
    usd_rate = 5.25  # Simulated
    IRD = usd_rate - jpy_rate

    vix_today = vix.iloc[-1]

    X_today = pd.DataFrame.from_dict({
        "IRD": [IRD],
        "FX_vol": [fx_vol],
        "VIX": [vix_today],
        "JPY_USD_roc": [log_returns.iloc[-1]]
    })

    return X_today

# Send SMS alert if risk is HIGH
def send_sms_alert(risk_level):
    if risk_level != "High":
        return

    twilio_sid = st.secrets["twilio"]["account_sid"]
    twilio_token = st.secrets["twilio"]["auth_token"]
    from_number = st.secrets["twilio"]["from_number"]
    to_number = st.secrets["twilio"]["to_number"]

    client = Client(twilio_sid, twilio_token)
    client.messages.create(
        body="⚠️ Alert: Today's carry trade risk is HIGH.",
        from_=from_number,
        to=to_number
    )

# Streamlit app
st.title("Yen Carry Trade Risk Tracker")
st.markdown("Updated daily with live FX and VIX data")

model = load_model()
data_today = fetch_data()
risk_prediction = model.predict(data_today)[0]
send_sms_alert(risk_prediction)

st.metric(label="Today's Carry Trade Risk", value=risk_prediction)
st.write("**Inputs:**")
st.dataframe(data_today.round(4))
