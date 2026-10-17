"""Fetch real 8760 weather and marine data for ALL locations in local time."""
import pandas as pd
import numpy as np
import requests
import time
from pathlib import Path

def fetch_open_meteo_data(lat, lon, year="2023"):
    """Fetches 8760 hourly data in automatically resolved Local Time."""
    url_weather = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={year}-01-01&end_date={year}-12-31&hourly=wind_speed_100m,shortwave_radiation,temperature_2m&timezone=auto&wind_speed_unit=ms"
    res_weather = requests.get(url_weather).json()
    
    resolved_tz = res_weather.get("timezone", "UTC")
    
    df_weather = pd.DataFrame({
        "timestamp_local": pd.to_datetime(res_weather["hourly"]["time"]),
        "wind_speed_100m_ms": res_weather["hourly"]["wind_speed_100m"],
        "ghi_w_m2": res_weather["hourly"]["shortwave_radiation"],
        "temp_c": res_weather["hourly"]["temperature_2m"]
    })
    
    url_marine = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&start_date={year}-01-01&end_date={year}-12-31&hourly=wave_height,wave_period&timezone=auto"
    res_marine = requests.get(url_marine).json()
    
    df_marine = pd.DataFrame({
        "timestamp_local": pd.to_datetime(res_marine["hourly"]["time"]),
        "wave_height_m": res_marine["hourly"]["wave_height"],
        "wave_period_s": res_marine["hourly"]["wave_period"]
    })
    
    df_marine.fillna(0, inplace=True)
    df_merged = pd.merge(df_weather, df_marine, on="timestamp_local", how="inner")
    
    # Attach the resolved timezone string (e.g., 'Europe/Paris' or 'Asia/Kolkata')
    df_merged["timezone"] = resolved_tz
    return df_merged

def convert_to_capacity_factors(df):
    """Converts raw physics into Net Capacity Factors."""
    
    # Floating Solar PV
    STC_W_M2 = 1000.0
    df["cf_fpv"] = (df["ghi_w_m2"] / STC_W_M2) * 0.80 * (1 - (0.004 * (df["temp_c"] - 25).clip(lower=0)))
    df["cf_fpv"] = df["cf_fpv"].clip(lower=0.0, upper=1.0)
    
    # Wind Turbine
    cut_in, rated, cut_out = 3.0, 11.0, 25.0
    def wind_curve(v):
        if v < cut_in or v > cut_out: return 0.0
        elif v >= rated: return 1.0
        else: return ((v**3 - cut_in**3) / (rated**3 - cut_in**3))
    df["cf_wind"] = df["wind_speed_100m_ms"].apply(wind_curve) * 0.88 
    
    # OTEC
    df["sst_proxy_c"] = df["temp_c"].rolling(window=24, min_periods=1).mean()
    
    deep_water_temp_c = 7.0 
    delta_t = (df["sst_proxy_c"] - deep_water_temp_c).clip(lower=0.0)
    
    # Gross Output Factor scales with ΔT^2 (Heat transfer * Carnot efficiency)
    gof = (delta_t / 22.0) ** 2
    
    # Parasitic load scales linearly with ΔT (Fixed pump flow rates)
    parasitic = 0.30 * (delta_t / 22.0)
    
    # Net Output Factor cannot be negative
    nof = (gof - parasitic).clip(lower=0.0)
    
    # Scale to 92% availability at the 22°C design point, and CLAMP to max 1.0
    df["cf_otec"] = (nof * (0.92 / 0.70)).clip(lower=0.0, upper=1.0)

    # 4. Wave Energy Converter
    df["wave_power_flux"] = 0.49 * (df["wave_height_m"]**2) * df["wave_period_s"]
    def wave_cf(row):
        h, j = row["wave_height_m"], row["wave_power_flux"]
        if h < 0.5 or h > 4.0: return 0.0
        return min(1.0, j / 25.0) * 0.85
    df["cf_wave"] = df.apply(wave_cf, axis=1)

    return df

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    excel_path = project_root / "Data" / "Dummy" / "BlueGrid_Lakshadweep_Dummy_Data (1).xlsx"
    df_islands = pd.read_excel(excel_path, sheet_name="Islands")
    
    brest_data = {
        "island": "Brest France",
        "lat_deg_N": 48.20, 
        "lon_deg_E": -5.54, 
        "peak_demand_kW_DUMMY": 5000
    }
    df_islands = pd.concat([df_islands, pd.DataFrame([brest_data])], ignore_index=True)
    
    hourly_dir = project_root / "Data" / "processed" / "hourly"
    hourly_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Beginning local-time data extraction for {len(df_islands)} locations...")
    
    for index, row in df_islands.iterrows():
        island_name = row["island"]
        deep_sea_lat = float(row["lat_deg_N"])
        deep_sea_lon = float(row["lon_deg_E"]) + 0.04
        
        try:
            df_hourly = fetch_open_meteo_data(deep_sea_lat, deep_sea_lon)
            df_hourly = convert_to_capacity_factors(df_hourly)
            df_hourly["load_flat_kW"] = float(row.get("peak_demand_kW_DUMMY", 1000))
            
            cols = ["timestamp_local", "timezone", "cf_wind", "cf_fpv", "cf_otec", "cf_wave", "load_flat_kW"]
            csv_path = hourly_dir / f"{island_name.lower().replace(' ', '_')}.csv"
            df_hourly[cols].to_csv(csv_path, index=False)
            time.sleep(1.5)
            
        except Exception as e:
            print(f"  -> Error fetching data for {island_name}: {e}")