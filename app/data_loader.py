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

    hourly: dict[str, pd.DataFrame] = {}
    hourly_dir = d / "hourly"
    if hourly_dir.exists():
        for csv in sorted(hourly_dir.glob("*.csv")):
            clean_key = csv.stem.replace("_", " ").strip().lower()
            
            # Read the CSV without forcing the date parser yet
            df = pd.read_csv(csv)
            
            # Dynamically parse whichever timestamp column exists
            if "timestamp_local" in df.columns:
                df["timestamp_local"] = pd.to_datetime(df["timestamp_local"])
            elif "timestamp_IST" in df.columns:
                # Convert the old IST column and rename it so the engine doesn't break
                df["timestamp_local"] = pd.to_datetime(df["timestamp_IST"])
                
            hourly[clean_key] = df

    return {
        "islands": _read(d, "islands.csv").set_index("island"),
        "tech":    _read(d, "tech_params.csv").set_index("technology"),
        "finance": finance,
        "wind":    _read(d, "wind_monthly.csv").set_index(["island", "month_num"]),
        "solar":   _read(d, "solar_monthly.csv").set_index(["island", "month_num"]),
        "otec":    _read(d, "otec_monthly.csv").set_index(["island", "month_num"]),
        "wave":    _read(d, "wave_monthly.csv").set_index(["island", "month_num"]),
        "hourly":  hourly,
    }