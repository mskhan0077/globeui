"""Technology viability scores."""
from __future__ import annotations

import numpy as np
import pandas as pd
import re

from .common import find_hourly_key

def _parse_trl(val) -> float:
    """Extract the first integer from string TRL values like '6-7' or '9 inland'."""
    if pd.isna(val):
        return 9.0
    match = re.search(r'(\d+)', str(val))
    return float(match.group(1)) if match else 9.0

def technology_scores(island: str, dfs: dict) -> dict:
    """Score each technology 0-10 on the four criteria."""
    tech = dfs["tech"]
    hourly_key = find_hourly_key(island, dfs)

    if hourly_key:
        h = dfs["hourly"][hourly_key]
        cf_map = {
            "Wind":              h["cf_wind"].astype(float),
            "Floating Solar PV": h["cf_fpv"].astype(float),
            "OTEC":              h["cf_otec"].astype(float),
            "Wave":              h["cf_wave"].astype(float),
        }
    else:
        cf_map = {
            "Wind":              dfs["wind"].loc[island, "cf_net_after_losses"].astype(float),
            "Floating Solar PV": dfs["solar"].loc[island, "cf_fpv"].astype(float),
            "OTEC":              dfs["otec"].loc[island, "cf_otec"].astype(float),
            "Wave":              dfs["wave"].loc[island, "cf_wec_net"].astype(float),
        }

    metrics = {}
    for name, cfs in cf_map.items():
        cf_annual = float(cfs.mean())
        cf_floor = float(np.percentile(cfs, 10))
        firmness = cf_floor / max(cf_annual, 1e-9)

        metrics[name] = {
            "cf_annual": cf_annual,
            "cf_min": float(cfs.min()),
            "cf_max": float(cfs.max()),
            "firmness": firmness,
            "capex_INR_per_kW": float(tech.loc[name, "capex_island_INR"]),
            "gco2": float(tech.loc[name, "lifecycle_gCO2_per_kWh"]),
            "trl": _parse_trl(tech.loc[name, "TRL"]),
        }

    cf_max = max(m["cf_annual"] for m in metrics.values())
    capex_min = min(m["capex_INR_per_kW"] for m in metrics.values())
    gco2_max = max(m["gco2"] for m in metrics.values())

    out = {}
    for name, m in metrics.items():
        out[name] = {
            "resource": 100.0 * m["cf_annual"] / max(cf_max, 1e-9),
            "capex": 100.0 * capex_min / max(m["capex_INR_per_kW"], 1e-9),
            "reliability": 100.0 * m["firmness"] * (m["trl"] / 9.0),
            "sustainability": 100.0 * (1.0 - m["gco2"] / max(gco2_max, 1e-9)),
            **m,
        }
    return out