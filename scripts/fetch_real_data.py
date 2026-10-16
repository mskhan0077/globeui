"""Fetch real 8760 weather and marine data for BlueGrid."""
import pandas as pd
import requests
from pathlib import Path

def fetch_open_meteo_data(lat, lon, year="2023"):
    """Fetches 8760 hourly atmospheric and marine data and merges them."""
    # Fetch Atmospheric Data (Wind, Solar, Temp)
    url_weather = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={year}-01-01&end_date={year}-12-31&hourly=wind_speed_100m,shortwave_radiation,temperature_2m&timezone=Asia%2FKolkata"
    res_weather = requests.get(url_weather).json()
    
    df_weather = pd.DataFrame({
        "timestamp_IST": pd.to_datetime(res_weather["hourly"]["time"]),
        "wind_speed_100m_ms": res_weather["hourly"]["wind_speed_100m"],
        "ghi_w_m2": res_weather["hourly"]["shortwave_radiation"],
        "temp_c": res_weather["hourly"]["temperature_2m"]
    })
    
    # Fetch Marine Data (Waves)
    url_marine = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&start_date={year}-01-01&end_date={year}-12-31&hourly=wave_height,wave_period&timezone=Asia%2FKolkata"
    res_marine = requests.get(url_marine).json()
    
    df_marine = pd.DataFrame({
        "timestamp_IST": pd.to_datetime(res_marine["hourly"]["time"]),
        "wave_height_m": res_marine["hourly"]["wave_height"],
        "wave_period_s": res_marine["hourly"]["wave_period"]
    })
    
    # Fill any missing marine data (e.g., if coordinates are too close to shore) with 0
    df_marine.fillna(0, inplace=True)
    
    # Merge on timestamp
    df_merged = pd.merge(df_weather, df_marine, on="timestamp_IST", how="inner")
    return df_merged

def convert_to_capacity_factors(df):
    """Converts raw physics into Net Capacity Factors."""
    
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
    
    # OTEC CAPACITY FACTOR (Rankine Cycle Thermodynamics)
    # The ocean surface doesn't change temp quickly like the air does.
    # A 24-hour rolling mean of air temp creates a highly accurate SST proxy.
    df["sst_proxy_c"] = df["temp_c"].rolling(window=24, min_periods=1).mean()
    
    t_c = 7.0 # Constant deep water temperature at 1000m
    delta_t = df["sst_proxy_c"] - t_c
    
    # Net Output Factor (NOF) formula
    # NOF = ((delta_T / 22)^2 - 0.30) / (1 - 0.30)
    nof = ((delta_t / 22.0)**2 - 0.30) / (1.0 - 0.30)
    
    # Clip NOF: if pumping takes more energy than generated, NOF = 0
    nof = nof.clip(lower=0.0, upper=1.05) 
    
    # Final CF is Thermodynamic Output * 92% Mechanical Availability
    df["cf_otec"] = nof * 0.92

    # WAVE
    # J = 0.49 * H^2 * T (Wave Power Flux in kW/m)
    df["wave_power_flux"] = 0.49 * (df["wave_height_m"]**2) * df["wave_period_s"]
    
    rated_wave_flux = 25.0 # kW/m
    availability = 0.85
    
    def wave_cf(row):
        h = row["wave_height_m"]
        j = row["wave_power_flux"]
        if h < 0.5 or h > 4.0:
            return 0.0
        return min(1.0, j / rated_wave_flux) * availability
        
    df["cf_wave"] = df.apply(wave_cf, axis=1)

    return df

if __name__ == "__main__":
    print("Fetching actual atmospheric and marine data for Kadmat Island...")
    
    # Fetch and Calculate
    df_hourly = fetch_open_meteo_data(11.13408, 72.43113)
    df_hourly = convert_to_capacity_factors(df_hourly)
    
    # Locate Data Directories dynamically
    project_root = Path(__file__).resolve().parent.parent
    hourly_dir = project_root / "Data" / "processed" / "hourly"
    
    dummy_csv_path = hourly_dir / "kadmat.csv"
    real_csv_path = hourly_dir / "kadmat.csv" # Overwriting the file directly
    
    # Port over the remaining Dummy Data (Load)
    print(f"Reading dummy load data from: {dummy_csv_path}")
    df_dummy = pd.read_csv(dummy_csv_path) 
    df_hourly["load_flat_kW"] = df_dummy["load_flat_kW"]
    
    # Clean up temporary columns
    columns_to_keep = ["timestamp_IST", "cf_wind", "cf_fpv", "cf_otec", "cf_wave", "load_flat_kW"]
    df_hourly = df_hourly[columns_to_keep]
    
    # Save and Inject into App
    df_hourly.to_csv(real_csv_path, index=False)
    print(f"Real API data successfully calculated and injected into: {real_csv_path}")