import truststore
# Inject truststore to bypass corporate certificate verification errors
truststore.inject_into_ssl()
import pandas as pd
import requests
from prophet import Prophet
# ---------------------------------------------------------
# 1. RETRAIN OR LOAD MODEL (or use your pre-trained object)
# ---------------------------------------------------------
print("Loading historical training data...")
df_train = pd.read_csv("ottawa_er_training_data_2025.csv")
df_train["timestamp"] = pd.to_datetime(df_train["timestamp"])
# Filter training window (Jan 1 to Oct 31, 2025)
train_subset = df_train[
(df_train["timestamp"] >= "2025-01-01")
& (df_train["timestamp"] <= "2025-10-31")
].copy()
df_prophet = pd.DataFrame(
{
"ds": train_subset["timestamp"],
"y": train_subset["arrivals"],
"temperature_c": train_subset["temperature_c"],
"precipitation_mm": train_subset["precipitation_mm"],
}
)
print("Initializing and training Prophet model...")
model = Prophet(
weekly_seasonality=True, daily_seasonality=False, yearly_seasonality=True
)
model.add_seasonality(name="hourly", period=1, fourier_order=8)
model.add_regressor("temperature_c")
model.add_regressor("precipitation_mm")
model.fit(df_prophet)
print("\nModel ready for live forecasting!")
# ---------------------------------------------------------
# 2. FETCH REAL-TIME WEATHER FORECAST FROM OPEN-METEO
# ---------------------------------------------------------
OTTAWA_LAT = 45.4215
OTTAWA_LON = -75.6972
url = "https://api.open-meteo.com/v1/forecast"
params = {
"latitude": OTTAWA_LAT,
"longitude": OTTAWA_LON,
"hourly": ["temperature_2m", "precipitation"],
"timezone": "America/Toronto",
"forecast_days": 2, # Fetches current hour + next 47 hours
}
print("Fetching live weather forecast for Ottawa...")
response = requests.get(url, params=params)
if response.status_code == 200:
    weather_data = response.json()["hourly"]
    # Build future dataframe directly from live weather API output
    future = pd.DataFrame(
        {
            "ds": pd.to_datetime(weather_data["time"]),
            "temperature_c": weather_data["temperature_2m"],
            "precipitation_mm": weather_data["precipitation"],
        }
    )
# ---------------------------------------------------------
# 3. GENERATE LIVE PREDICTIONS
# ---------------------------------------------------------
    print("Generating 48-hour emergency room patient surge forecast...")
    forecast = model.predict(future)

    # Merge predictions with timestamps
    live_results = pd.merge(
        future[["ds"]],
        forecast[["ds", "yhat"]],
        on="ds",
        how="inner",
    )
    # Reformat columns to match your exact requested structure
    live_results["date"] = live_results["ds"].dt.strftime("%Y/%m/%d")
    live_results["hour"] = live_results["ds"].dt.hour
    live_results["expected_arrivals"] = live_results["yhat"].round().astype(int)
    # Select only the 3 required columns
    final_output = live_results[["date", "hour", "expected_arrivals"]]
# ---------------------------------------------------------
# 4. OUTPUT & EXPORT RESULTS
# ---------------------------------------------------------
    print("\n--- Next 24 Hours ER Patient Forecast ---")
    print(final_output.head(24).to_string(index=False))
    output_filename = "forecast.csv"
    final_output.to_csv(output_filename, index=False)
    print(f"\nLive forecast successfully saved to '{output_filename}'")
else:
        print(f"Failed to fetch live weather data: {response.status_code}")