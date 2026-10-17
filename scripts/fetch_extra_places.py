"""Add places that aren't in the Lakshadweep workbook (e.g. Brest) to the planner.

Reads data/source/extra_places.csv. Each place's hourly data is
data/processed/hourly/<name>.csv: an existing file is used as is (e.g. data
supplied by the team); a missing one, or every one with --fetch, is downloaded
from Open-Meteo at the place's resource point and converted to capacity factors
with the same physics as fetch_real_data.py. Then writes

  data/processed/extra/*.csv           monthly rows (from the hourly data) + island
                                       list entry, merged into the workbook data by
                                       the backend

Kept separate from extract_csvs.py output so re-extracting the workbook doesn't
drop these places. Costs and finance parameters are the dataset's (Lakshadweep,
INR) - only the renewable resource is place-specific.

Run from backend/:  uv run python ../scripts/fetch_extra_places.py [--fetch]
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_real_data import convert_to_capacity_factors, fetch_open_meteo_data  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "source" / "extra_places.csv"
HOURLY = ROOT / "data" / "processed" / "hourly"
EXTRA = ROOT / "data" / "processed" / "extra"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def file_stem(name: str) -> str:
    """Same naming as fetch_real_data.py, so the backend matches it to the place."""
    return name.lower().replace(" ", "_")


def timestamps(df: pd.DataFrame) -> pd.Series:
    """Hourly timestamps: new files have timestamp_local, older ones timestamp_IST."""
    col = "timestamp_local" if "timestamp_local" in df.columns else "timestamp_IST"
    return pd.to_datetime(df[col])


def load_or_fetch(row, path: Path, refresh: bool) -> pd.DataFrame:
    if path.exists() and not refresh:
        print(f"    using existing {path.relative_to(ROOT)}")
        return pd.read_csv(path)
    print(f"    fetching Open-Meteo data at ({row.resource_lat}, {row.resource_lon})...")
    df = convert_to_capacity_factors(fetch_open_meteo_data(row.resource_lat, row.resource_lon))
    df["load_flat_kW"] = 1000.0
    cols = ["timestamp_local", "timezone", "cf_wind", "cf_fpv", "cf_otec", "cf_wave", "load_flat_kW"]
    df[cols].to_csv(path, index=False)
    time.sleep(1.5)  # be gentle with the free API
    return df[cols]


def monthly(df: pd.DataFrame, name: str, columns: dict[str, str]) -> pd.DataFrame:
    """Monthly means of hourly columns, renamed to the workbook's monthly column names."""
    m = df.groupby(timestamps(df).dt.month)
    out = pd.DataFrame({
        "island": name,
        "month_num": m.size().index.astype(float),
        "month": [MONTHS[i - 1] for i in m.size().index],
        "hours": m.size().values.astype(float),
    })
    for src, dst in columns.items():
        out[dst] = m[src].mean().round(4).values
    return out


def main():
    refresh = "--fetch" in sys.argv[1:]
    places = pd.read_csv(SOURCE)
    HOURLY.mkdir(parents=True, exist_ok=True)
    EXTRA.mkdir(parents=True, exist_ok=True)
    tables = {"wind": [], "solar": [], "otec": [], "wave": []}

    for i, row in places.iterrows():
        name = row["island"]
        print(f"[{i + 1}/{len(places)}] {name}")
        df = load_or_fetch(row, HOURLY / f"{file_stem(name)}.csv", refresh)

        tables["wind"].append(monthly(df, name, {"cf_wind": "cf_net_after_losses"}))
        tables["solar"].append(monthly(df, name, {"cf_fpv": "cf_fpv"}))
        tables["otec"].append(monthly(df, name, {"cf_otec": "cf_otec"}))
        tables["wave"].append(monthly(df, name, {"cf_wave": "cf_wec_net"}))
        means = {k: round(float(df[k].mean()), 3) for k in ["cf_wind", "cf_fpv", "cf_otec", "cf_wave"]}
        print(f"    annual capacity factors: {means}")

    places[["island", "group", "lat_deg_N", "lon_deg_E"]].to_csv(EXTRA / "islands.csv", index=False)
    for key, frames in tables.items():
        pd.concat(frames).to_csv(EXTRA / f"{key}_monthly.csv", index=False)
    print(f"Wrote {len(places)} place(s) to {EXTRA.relative_to(ROOT)} and {HOURLY.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
