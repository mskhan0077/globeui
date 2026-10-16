from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

def _read(d: Path, name: str, **kw) -> pd.DataFrame:
    return pd.read_csv(d / name, **kw)

def load_all(data_dir: str | Path = "Data/processed") -> dict:
    d = Path(data_dir)
    if not d.exists():
        raise FileNotFoundError(
            f"Processed data folder not found: {d.resolve()}\n"
            "Run:  python scripts/extract_csvs.py"
        )

    with open(d / "finance_params.json") as fh:
        finance = json.load(fh)

    # 1. Load Hourly API Data
    hourly: dict[str, pd.DataFrame] = {}
    hourly_dir = d / "hourly"
    if hourly_dir.exists():
        for csv in sorted(hourly_dir.glob("*.csv")):
            clean_key = csv.stem.replace("_", " ").strip().title()
            
            df = pd.read_csv(csv)
            # Safely parse timestamps whether they are the old IST format or new Local Time
            if "timestamp_local" in df.columns:
                df["timestamp_local"] = pd.to_datetime(df["timestamp_local"])
            elif "timestamp_IST" in df.columns:
                df["timestamp_local"] = pd.to_datetime(df["timestamp_IST"])
                
            hourly[clean_key] = df

    # 2. Load Master CSVs
    dfs = {
        "islands": _read(d, "islands.csv").set_index("island"),
        "tech":    _read(d, "tech_params.csv").set_index("technology"),
        "finance": finance,
        "wind":    _read(d, "wind_monthly.csv").set_index(["island", "month_num"]),
        "solar":   _read(d, "solar_monthly.csv").set_index(["island", "month_num"]),
        "otec":    _read(d, "otec_monthly.csv").set_index(["island", "month_num"]),
        "wave":    _read(d, "wave_monthly.csv").set_index(["island", "month_num"]),
        "hourly":  hourly,
    }

    # 3. AUTO-DISCOVERY: Inject any missing hourly islands into the master datasets
    missing_islands = [k for k in hourly.keys() if k not in dfs["islands"].index]
    
    if missing_islands:
        # A. Add to Islands list (This pushes it to the UI dropdown)
        new_islands = pd.DataFrame([
            {"island": idx, "lat_deg_N": 0.0, "lon_deg_E": 0.0, "peak_demand_kW_DUMMY": 1000.0} 
            for idx in missing_islands
        ]).set_index("island")
        dfs["islands"] = pd.concat([dfs["islands"], new_islands])

        # B. Add dummy monthly rows to prevent KeyErrors in the fallback engine
        # (The 8760 hourly arrays will overwrite these 0s during evaluation)
        months = list(range(1, 13))
        hours = [744, 672, 744, 720, 744, 720, 744, 744, 720, 744, 720, 744]
        
        wind_rows, solar_rows, otec_rows, wave_rows = [], [], [], []
        for idx in missing_islands:
            for m, h in zip(months, hours):
                wind_rows.append({"island": idx, "month_num": m, "hours": h, "cf_net_after_losses": 0.0})
                solar_rows.append({"island": idx, "month_num": m, "hours": h, "cf_fpv": 0.0})
                otec_rows.append({"island": idx, "month_num": m, "hours": h, "cf_otec": 0.0})
                wave_rows.append({"island": idx, "month_num": m, "hours": h, "cf_wec_net": 0.0})
        
        def append_rows(original_df, new_rows):
            new_df = pd.DataFrame(new_rows).set_index(["island", "month_num"])
            return pd.concat([original_df, new_df])

        dfs["wind"] = append_rows(dfs["wind"], wind_rows)
        dfs["solar"] = append_rows(dfs["solar"], solar_rows)
        dfs["otec"] = append_rows(dfs["otec"], otec_rows)
        dfs["wave"] = append_rows(dfs["wave"], wave_rows)

    return dfs