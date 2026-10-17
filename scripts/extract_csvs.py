"""
scripts/extract_csvs.py

Read the multi-sheet BlueGrid workbook, clean each sheet, recompute derived
columns, and write per-sheet CSVs into Data/processed/.

Run once after cloning, and whenever the workbook changes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

# paths 
ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / "data" / "source" / "BlueGrid_Lakshadweep_Dummy_Data.xlsx"
OUT = ROOT / "data" / "processed"
OUT_HOURLY = OUT / "hourly"


# helpers 
class XlsxReader:
    """Read every sheet once, with formula values (data_only=True)."""

    def __init__(self, path: Path):
        if not path.exists():
            sys.exit(f"[FATAL] workbook not found: {path}")
        self.wb = load_workbook(path, data_only=True, read_only=True)

    def sheet(self, name: str) -> pd.DataFrame:
        if name not in self.wb.sheetnames:
            sys.exit(f"[FATAL] sheet '{name}' not found in workbook. "
                     f"Available: {self.wb.sheetnames}")
        ws = self.wb[name]
        rows = list(ws.values)
        if len(rows) < 2:
            return pd.DataFrame()
        header = [
            (str(c).strip() if c is not None else f"col_{i}")
            for i, c in enumerate(rows[0])
        ]
        df = pd.DataFrame(rows[1:], columns=header)
        return df

    def close(self):
        self.wb.close()


def drop_trailing_notes(df: pd.DataFrame, required: list[str]) -> pd.DataFrame:
    """Keep only rows where every column in `required` is non-null."""
    for col in required:
        if col not in df.columns:
            sys.exit(f"[FATAL] required column '{col}' missing. "
                     f"Columns: {list(df.columns)}")
    mask = df[required].notna().all(axis=1)
    return df.loc[mask].reset_index(drop=True)


def to_float(x, default=None):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def ensure_dirs():
    OUT.mkdir(parents=True, exist_ok=True)
    OUT_HOURLY.mkdir(parents=True, exist_ok=True)


def report(name: str, n: int, expected: int | None = None):
    flag = ""
    if expected is not None and n != expected:
        flag = f"  ⚠ expected {expected}"
    print(f"  {name:24s} {n:>6d} rows{flag}")


# extractors 
def extract_finance(reader: XlsxReader) -> dict:
    """Finance_Params is a key→value sheet. Recompute every derived value."""
    df = reader.sheet("Finance_Params")
    df = df.dropna(subset=["parameter"])
    raw = dict(zip(df["parameter"].astype(str).str.strip(),
                   df["value"]))

    def num(key, default):
        return to_float(raw.get(key), default)

    f: dict[str, float] = {}
    # Raw inputs
    f["target_net_AC_load_kW"]            = num("target_net_AC_load_kW", 1000.0)
    f["project_life_yr"]                  = num("project_life_yr", 25.0)
    f["discount_rate_real"]               = num("discount_rate_real", 0.08)
    f["fx_INR_per_USD"]                   = num("fx_INR_per_USD", 88.0)
    f["diesel_landed_price_INR_per_L"]    = num("diesel_landed_price_INR_per_L", 100.0)
    f["diesel_sfc_L_per_kWh"]             = num("diesel_sfc_L_per_kWh", 0.3)
    f["diesel_co2_kg_per_L"]              = num("diesel_co2_kg_per_L", 2.68)
    f["diesel_reported_CoE_INR_per_kWh"]  = num("diesel_reported_CoE_INR_per_kWh", 28.0)
    f["carbon_price_USD_per_t"]           = num("carbon_price_USD_per_t", 15.0)
    f["grid_EF_CEA_reference_tCO2_per_MWh"] = num("grid_EF_CEA_reference_tCO2_per_MWh", 0.727)
    f["bess_round_trip_eff"]              = num("bess_round_trip_eff", 0.88)
    f["bess_depth_of_discharge"]          = num("bess_depth_of_discharge", 0.9)
    f["bess_max_c_rate"]                  = num("bess_max_c_rate", 0.5)
    f["bess_replacement_year"]            = num("bess_replacement_year", 15.0)
    f["bess_replacement_cost_fraction"]   = num("bess_replacement_cost_fraction", 0.6)
    f["fpv_cfa_subsidy_INR_per_kW"]       = num("fpv_cfa_subsidy_INR_per_kW", 10000.0)
    f["bess_vgf_INR_per_kWh"]             = num("bess_vgf_INR_per_kWh", 1800.0)
    f["apply_subsidies_flag"]             = num("apply_subsidies_flag", 0.0)
    f["reliability_target_LPSP"]          = num("reliability_target_LPSP", 0.01)
    f["otec_design_delta_T_C"]            = num("otec_design_delta_T_C", 22.0)
    f["otec_parasitic_fraction"]          = num("otec_parasitic_fraction", 0.3)
    f["otec_freshwater_m3_day_per_kW"]    = num("otec_freshwater_m3_day_per_kW", 1.5)
    f["wind_hub_height_m"]                = num("wind_hub_height_m", 80.0)
    f["wind_shear_alpha"]                 = num("wind_shear_alpha", 0.11)
    f["pv_temp_coeff_per_C"]              = num("pv_temp_coeff_per_C", -0.0035)
    f["pv_tilt_deg"]                      = num("pv_tilt_deg", 10.0)

    # Derived
    r, n = f["discount_rate_real"], f["project_life_yr"]
    f["capital_recovery_factor"] = r * (1 + r) ** n / ((1 + r) ** n - 1)
    f["diesel_emission_factor_tCO2_per_MWh"] = (
        f["diesel_sfc_L_per_kWh"] * f["diesel_co2_kg_per_L"]
    )
    f["diesel_fuel_cost_INR_per_kWh"] = (
        f["diesel_landed_price_INR_per_L"] * f["diesel_sfc_L_per_kWh"]
    )
    f["carbon_price_INR_per_t"] = (
        f["carbon_price_USD_per_t"] * f["fx_INR_per_USD"]
    )

    with open(OUT / "finance_params.json", "w") as fh:
        json.dump(f, fh, indent=2, sort_keys=True)
    report("finance_params.json", len(f))
    return f


def extract_islands(reader: XlsxReader):
    df = reader.sheet("Islands")
    df = drop_trailing_notes(df, ["island", "lat_deg_N", "lon_deg_E"])
    # numeric coercion
    for col in ["lat_deg_N", "lon_deg_E", "land_area_km2",
                "atoll_lagoon_area_km2", "population_2011_approx",
                "wind_multiplier", "ghi_multiplier", "sst_offset_C",
                "wave_multiplier", "dist_to_1000m_isobath_km_DUMMY",
                "peak_demand_kW_DUMMY"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df.to_csv(OUT / "islands.csv", index=False)
    report("islands.csv", len(df), expected=36)


def extract_tech(reader: XlsxReader, fx: float):
    df = reader.sheet("Tech_Params")
    df = drop_trailing_notes(df, ["technology", "capex_base_value",
                                  "island_cost_factor"])

    def to_inr(value, currency):
        v = to_float(value, 0.0)
        cur = str(currency).strip().upper()
        return v if cur == "INR" else v * fx

    df["capex_island_INR"] = [
        to_inr(b, c) * to_float(fac, 1.0)
        for b, c, fac in zip(df["capex_base_value"],
                             df["capex_base_currency"],
                             df["island_cost_factor"])
    ]
    df["opex_INR_per_unit_yr"] = [
        to_inr(b, c) * to_float(fac, 1.0)
        for b, c, fac in zip(df["opex_base_value"],
                             df["opex_base_currency"],
                             df["island_cost_factor"])
    ]
    df["opex_pct_of_capex"] = (
        df["opex_INR_per_unit_yr"] / df["capex_island_INR"]
    )

    keep = ["technology", "typical_unit_size", "capex_island_INR",
            "opex_INR_per_unit_yr", "opex_pct_of_capex", "lifetime_yr",
            "degradation_per_yr", "availability",
            "lifecycle_gCO2_per_kWh", "TRL"]
    df = df[[c for c in keep if c in df.columns]]
    df.to_csv(OUT / "tech_params.csv", index=False)
    report("tech_params.csv", len(df), expected=6)


def extract_monthly(reader: XlsxReader, sheet: str, filename: str,
                    required: list[str], expected: int | None = 432):
    df = reader.sheet(sheet)
    df = drop_trailing_notes(df, required)
    df.to_csv(OUT / filename, index=False)
    report(filename, len(df), expected=expected)


def extract_hourly(reader: XlsxReader):
    # The workbook's Hourly_Kadmat sheet is synthetic; never overwrite real
    # downloaded data (scripts/fetch_real_data.py) with it.
    target = OUT_HOURLY / "kadmat.csv"
    if target.exists():
        print("  [skip] hourly/kadmat.csv already exists (real data kept)")
        return
    df = reader.sheet("Hourly_Kadmat")
    df = drop_trailing_notes(df, ["island", "timestamp_IST"])
    df.to_csv(target, index=False)
    report("hourly/kadmat.csv", len(df), expected=8760)


# main 
def main():
    ensure_dirs()
    print(f"Reading: {XLSX.name}")
    print(f"Writing: {OUT}\n")

    reader = XlsxReader(XLSX)
    try:
        finance = extract_finance(reader)
        fx = finance["fx_INR_per_USD"]

        extract_islands(reader)
        extract_tech(reader, fx)

        extract_monthly(reader, "Wind_Monthly",  "wind_monthly.csv",
                        ["island", "month_num", "cf_net_after_losses"])
        extract_monthly(reader, "Solar_Monthly", "solar_monthly.csv",
                        ["island", "month_num", "cf_fpv"])
        extract_monthly(reader, "OTEC_Monthly",  "otec_monthly.csv",
                        ["island", "month_num", "cf_otec"])
        extract_monthly(reader, "Wave_Monthly",  "wave_monthly.csv",
                        ["island", "month_num", "cf_wec_net"])
        extract_monthly(reader, "OTEC_Profile",  "otec_profile.csv",
                ["island", "month_num", "depth_m"],
                expected=252)
        extract_monthly(reader, "Turbine_PowerCurve", "turbine_curve.csv",
                        ["wind_speed_ms", "power_kW"], expected=61)

        extract_hourly(reader)
    finally:
        reader.close()

    print("\nDone.")


if __name__ == "__main__":
    main()