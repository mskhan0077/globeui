from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

def _read(d: Path, name: str, **kw) -> pd.DataFrame:
    return pd.read_csv(d / name, **kw)

def load_all(data_dir: str | Path = "data/processed") -> dict:
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
            df = pd.read_csv(csv)
            # Newer files (fetch_real_data.py) are in local time with a timezone column;
            # older ones are labelled timestamp_IST, i.e. Indian Standard Time.
            if "timestamp_local" in df.columns:
                df["timestamp_local"] = pd.to_datetime(df["timestamp_local"])
            elif "timestamp_IST" in df.columns:
                df["timestamp_local"] = pd.to_datetime(df["timestamp_IST"])
                if "timezone" not in df.columns:
                    df["timezone"] = "Asia/Kolkata"
            hourly[clean_key] = df

    # Places outside the workbook (scripts/fetch_extra_places.py) live in extra/
    # with the same file names; append their rows to the workbook tables.
    def table(name: str) -> pd.DataFrame:
        df = _read(d, name)
        extra = d / "extra" / name
        return pd.concat([df, pd.read_csv(extra)], ignore_index=True) if extra.exists() else df

    return {
        "islands": table("islands.csv").set_index("island"),
        "tech":    _read(d, "tech_params.csv").set_index("technology"),
        "discount": _read(d, "discount_params.csv").set_index("technology"),  # volume-discount blocks
        "finance": finance,
        "wind":    table("wind_monthly.csv").set_index(["island", "month_num"]),
        "solar":   table("solar_monthly.csv").set_index(["island", "month_num"]),
        "otec":    table("otec_monthly.csv").set_index(["island", "month_num"]),
        "wave":    table("wave_monthly.csv").set_index(["island", "month_num"]),
        "hourly":  hourly,
    }