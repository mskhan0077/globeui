"""Scoring matrix — resource, capex, reliability, sustainability."""
from __future__ import annotations

import numpy as np
import pandas as pd
import re


def _parse_trl(val) -> float:
    """Extract the first integer from string TRL values like '6-7' or '9 inland'."""
    if pd.isna(val):
        return 9.0
    match = re.search(r'(\d+)', str(val))
    return float(match.group(1)) if match else 9.0


def technology_scores(island: str, dfs: dict) -> dict:
    """Score each technology 0-10 on the four criteria."""
    tech = dfs["tech"]
    cf_map = {
        "Wind":              dfs["wind"].loc[island, "cf_net_after_losses"].astype(float),
        "Floating Solar PV": dfs["solar"].loc[island, "cf_fpv"].astype(float),
        "OTEC":              dfs["otec"].loc[island, "cf_otec"].astype(float),
        "Wave":              dfs["wave"].loc[island, "cf_wec_net"].astype(float),
    }

    metrics = {}
    for name, cfs in cf_map.items():
        cf_annual = float(cfs.mean())
        
        # FIXED FIRMNESS: Use 10th percentile instead of absolute minimum to prevent 0-scores
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


def weighted_score(scores: dict, weights: dict) -> float:
    return (
        weights["resource"] * scores["resource"]
        + weights["capex"] * scores["capex"]
        + weights["reliability"] * scores["reliability"]
        + weights["sustainability"] * scores["sustainability"]
    )


def config_scores(annual: dict, econ: dict, carbon: dict, reliability: dict,
                  weights: dict, benchmark: dict) -> dict:
    """Score a full configuration, normalizing against a benchmark."""
    gen_total = max(annual["gen_total_kWh"], 1e-9)
    installed_kW = max(benchmark["installed_kW"], 1e-9)
    fleet_cf = gen_total / (installed_kW * 8760.0)
    resource = 10.0 * fleet_cf / max(benchmark["fleet_cf"], 1e-9)

    lcoe = max(econ["LCOE_RE_INR_per_kWh"], 1e-9)
    capex = 10.0 * benchmark["lcoe_min"] / lcoe

    lpsp = min(max(reliability.get("lpsp_hourly", reliability.get("lpsp_annual", 0.0)), 0.0), 1.0)
    reliability_score = 10.0 * (1.0 - lpsp)

    gco2 = carbon["co2_avoided_t"]
    sustain = 10.0 * min(gco2 / max(benchmark["co2_max"], 1e-9), 1.0)

    s = {
        "resource": resource,
        "capex": capex,
        "reliability": reliability_score,
        "sustainability": sustain,
    }
    s["weighted"] = weighted_score(s, weights)
    return s