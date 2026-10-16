'''Change this script to fetch real data from the API and save it to a CSV file. We will replace the mock data with actual API calls.'''

import pandas as pd
import requests

def fetch_open_meteo_hourly(lat, lon, year="2023"):
    """Fetches 8760 hourly data for Wind Speed (100m) and Solar GHI."""
    url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={year}-01-01&end_date={year}-12-31&hourly=wind_speed_100m,shortwave_radiation,temperature_2m&timezone=Asia%2FKolkata"
    response = requests.get(url)
    data = response.json()
    
    df = pd.DataFrame({
        "timestamp_IST": pd.to_datetime(data["hourly"]["time"]),
        "wind_speed_100m_ms": data["hourly"]["wind_speed_100m"],
        "ghi_w_m2": data["hourly"]["shortwave_radiation"],
        "temp_c": data["hourly"]["temperature_2m"]
    })
    return df

if __name__ == "__main__":
    print("Fetching actual data for Kadmat Island...")
    # Kadmat coordinates
    df_hourly = fetch_open_meteo_hourly(11.22, 72.78)
    
    # Keep the dummy OTEC, Wave, and Load for now
    df_dummy = pd.read_csv("../data/hourly/kadmat.csv") 
    df_hourly["cf_otec"] = df_dummy["cf_otec"]
    df_hourly["cf_wave"] = df_dummy["cf_wave"]
    df_hourly["load_flat_kW"] = df_dummy["load_flat_kW"]
    
    # Save the real data back to the app's data folder
    df_hourly.to_csv("../data/hourly/kadmat_real.csv", index=False)
    print("Real data saved successfully lalala!")