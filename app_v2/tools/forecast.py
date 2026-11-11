"""Make app_v2/data/forecast.csv: a 48-hour ER arrivals forecast for Ottawa.

Chengjin's Prophet model, with fixes so the output matches the app's file agreement.
Run it on the demo day (Nov 30). It forecasts today 00:00 to tomorrow 23:00.

    pip install prophet pandas requests
    python app_v2/tools/forecast.py

Needs ottawa_er_training_data_2025.csv (columns: timestamp, arrivals,
temperature_c, precipitation_mm) in this tools/ folder.

Changes from the original script:
- Dates are written as YYYY-MM-DD (the app's format), not YYYY/MM/DD.
- Training window keeps all of Oct 31 (the old filter stopped at Oct 31 00:00).
- Negative predictions are set to 0 (Prophet can go below zero at quiet hours).
- Missing weather values are filled so Prophet does not crash.
- The script stops with a clear message if the weather call fails or the output is not 48 hours.
- The file is saved straight into app_v2/data/, whatever folder you run it from.
- truststore is optional: only needed on networks with certificate problems.
"""
from pathlib import Path

import pandas as pd
import requests
from prophet import Prophet

try:
    import truststore  # fixes certificate errors on some corporate/university networks
    truststore.inject_into_ssl()
except ImportError:
    pass

HERE = Path(__file__).parent
TRAINING_FILE = HERE / "ottawa_er_training_data_2025.csv"
OUTPUT_FILE = HERE.parent / "data" / "forecast.csv"

# ---------------------------------------------------------
# 1. TRAIN THE MODEL
# ---------------------------------------------------------
print("Loading historical training data...")
df_train = pd.read_csv(TRAINING_FILE)
df_train["timestamp"] = pd.to_datetime(df_train["timestamp"])

# Jan 1 to Oct 31, 2025, including every hour of Oct 31
train_subset = df_train[
    (df_train["timestamp"] >= "2025-01-01") & (df_train["timestamp"] < "2025-11-01")
].copy()

df_prophet = pd.DataFrame(
    {
        "ds": train_subset["timestamp"],
        "y": train_subset["arrivals"],
        "temperature_c": train_subset["temperature_c"],
        "precipitation_mm": train_subset["precipitation_mm"],
    }
)

print("Training Prophet model...")
model = Prophet(weekly_seasonality=True, daily_seasonality=False, yearly_seasonality=True)
# Within-day pattern (period = 1 day, so this is the hour-of-day shape)
model.add_seasonality(name="hourly", period=1, fourier_order=8)
model.add_regressor("temperature_c")
model.add_regressor("precipitation_mm")
model.fit(df_prophet)

# ---------------------------------------------------------
# 2. GET THE WEATHER FORECAST (Open-Meteo, no key needed)
# ---------------------------------------------------------
params = {
    "latitude": 45.4215,
    "longitude": -75.6972,
    "hourly": ["temperature_2m", "precipitation"],
    "timezone": "America/Toronto",
    "forecast_days": 2,  # today 00:00 to tomorrow 23:00 = 48 hours
}
print("Fetching weather forecast for Ottawa...")
response = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=30)
if response.status_code != 200:
    raise SystemExit(f"Weather request failed ({response.status_code}). No file written.")
weather = response.json()["hourly"]

future = pd.DataFrame(
    {
        "ds": pd.to_datetime(weather["time"]),
        "temperature_c": weather["temperature_2m"],
        "precipitation_mm": weather["precipitation"],
    }
)
future["temperature_c"] = future["temperature_c"].ffill().bfill()
future["precipitation_mm"] = future["precipitation_mm"].fillna(0)

# ---------------------------------------------------------
# 3. PREDICT AND SAVE IN THE APP'S FORMAT
# ---------------------------------------------------------
print("Generating 48-hour forecast...")
forecast = model.predict(future)

out = pd.DataFrame(
    {
        "date": forecast["ds"].dt.strftime("%Y-%m-%d"),
        "hour": forecast["ds"].dt.hour,
        "expected_arrivals": forecast["yhat"].clip(lower=0).round().astype(int),
    }
)

if len(out) != 48 or out.groupby("date")["hour"].nunique().ne(24).any():
    raise SystemExit(f"Expected 48 hours (2 full days), got {len(out)} rows. No file written.")

print(out.to_string(index=False))
out.to_csv(OUTPUT_FILE, index=False)
print(f"\nSaved to {OUTPUT_FILE}")
