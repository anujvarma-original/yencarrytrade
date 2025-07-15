import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import datetime

# Compute risk level
def compute_risk(vix, fx_vol):
    if vix > 20 and fx_vol > 0.01:
        return "High"
    elif vix > 15:
        return "Medium"
    else:
        return "Low"

# Time window
end_date = datetime.datetime.today()
start_date = end_date - datetime.timedelta(days=180)

# Download data
vix_data = yf.download("^VIX", start=start_date, end=end_date, interval="1wk")["Close"]
fx_data = yf.download("JPY=X", start=start_date, end=end_date, interval="1wk")["Close"]

# Compute FX weekly volatility
fx_vol = fx_data.pct_change().rolling(window=2).std()

# Combine data
combined = pd.DataFrame({
    "VIX": vix_data,
    "FX_vol": fx_vol
}).dropna()

# Risk levels
combined["Risk"] = combined.apply(lambda row: compute_risk(row["VIX"], row["FX_vol"]), axis=1)

# Plotting
plt.figure(figsize=(12, 6))
colors = {"High": "red", "Medium": "orange", "Low": "green"}
for risk_level in combined["Risk"].unique():
    risk_data = combined[combined["Risk"] == risk_level]
    plt.scatter(risk_data.index, risk_data["VIX"], color=colors[risk_level], label=risk_level)

plt.title("Carry Trade Risk Levels Over Time (Past 6 Months)")
plt.xlabel("Date")
plt.ylabel("VIX Value")
plt.legend(title="Risk Level")
plt.grid(True)
plt.tight_layout()
plt.xticks(rotation=45)
plt.show()
