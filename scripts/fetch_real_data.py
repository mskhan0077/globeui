import pandas as pd
import requests
from pathlib import Path

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

def convert_to_capacity_factors(df):
    """Converts raw weather physics into Net Capacity Factors."""
    
    # Solar FPV Capacity Factor
    # CF = (GHI / Standard Test Condition Irradiance) * Performance Ratio
    # Standard STC is 1000 W/m2. Assume a PR of 0.80 for floating marine solar.
    STC_W_M2 = 1000.0
    PERFORMANCE_RATIO = 0.80
    
    # Temperature derating: panels lose ~0.4% efficiency per degree over 25C
    temp_penalty = 1 - (0.004 * (df["temp_c"] - 25).clip(lower=0))
    
    df["cf_fpv"] = (df["ghi_w_m2"] / STC_W_M2) * PERFORMANCE_RATIO * temp_penalty
    df["cf_fpv"] = df["cf_fpv"].clip(lower=0.0, upper=1.0)
    
    # Wind Capacity Factor (Simplified Power Curve mapping)
    # Using a standard 1.5MW offshore/island turbine profile
    cut_in = 3.0    # m/s
    rated = 11.0    # m/s
    cut_out = 25.0  # m/s
    
    def wind_power_curve(v):
        if v < cut_in or v > cut_out:
            return 0.0
        elif v >= rated:
            return 1.0
        else:
            # Cubic relationship between cut-in and rated speed
            return ((v**3 - cut_in**3) / (rated**3 - cut_in**3))
            
    df["cf_wind_gross"] = df["wind_speed_100m_ms"].apply(wind_power_curve)
    
    # Apply standard wake, electrical, and availability losses (assume 12% total loss)
    df["cf_wind"] = df["cf_wind_gross"] * 0.88 
    
    return df

if __name__ == "__main__":
    print("Fetching actual data for Kadmat Island... hmmmmm")
    # Kadmat coordinates
    df_hourly = fetch_open_meteo_hourly(11.22, 72.78)
    df_hourly = convert_to_capacity_factors(df_hourly)
    
    # Dynamically find the project root
    project_root = Path(__file__).resolve().parent.parent
    hourly_dir = project_root / "Data" / "processed" / "hourly"
    
    dummy_csv_path = hourly_dir / "kadmat.csv"
    real_csv_path = hourly_dir / "kadmat_real.csv"
    
    print(f"Reading dummy data from: {dummy_csv_path}")
    df_dummy = pd.read_csv(dummy_csv_path) 
    
    # Merge the dummy OTEC, Wave, and Load to match the app's expectations
    df_hourly["cf_otec"] = df_dummy["cf_otec"]
    df_hourly["cf_wave"] = df_dummy["cf_wave"]
    df_hourly["load_flat_kW"] = df_dummy["load_flat_kW"]
    
    # Save the realistic 8760 data back to the app's data folder
    df_hourly.to_csv(real_csv_path, index=False)
    print(f"Real data saved successfully to: {real_csv_path} lalalala!")