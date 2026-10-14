"""Single configuration: full evaluation, returns a JSON-safe dict."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import generation, bess, economics, carbon, scoring


def evaluate(island: str, capacities: dict, dfs: dict,
             use_hourly: bool | None = None) -> dict:
    """Full pipeline for one configuration."""

    monthly = generation.monthly_generation(island, capacities, dfs)
    annual = {
        "hours": float(monthly["hours"].sum()),
        "gen_wind_kWh": float(monthly["gen_wind_kWh"].sum()),
        "gen_fpv_kWh": float(monthly["gen_fpv_kWh"].sum()),
        "gen_otec_kWh": float(monthly["gen_otec_kWh"].sum()),
        "gen_wave_kWh": float(monthly["gen_wave_kWh"].sum()),
        "gen_total_kWh": float(monthly["gen_total_kWh"].sum()),
        "load_kWh": float(monthly["load_kWh"].sum()),
        "delivered_kWh": float(monthly["delivered_kWh"].sum()),
        "surplus_kWh": float(monthly["surplus_kWh"].sum()),
        "unmet_kWh": float(monthly["unmet_kWh"].sum()),
    }

    finance = dfs["finance"]
    capex, subsidy = economics.compute_capex(capacities, dfs["tech"], finance)
    opex = economics.compute_annual_opex(capacities, dfs["tech"])
    repl = economics.bess_replacement_pv(capex["bess_kWh"], finance)

    econ = economics.cost_metrics(
        capex, subsidy, opex, repl,
        annual["delivered_kWh"], annual["load_kWh"], annual["unmet_kWh"],
        finance,
    )
    carb = carbon.carbon_metrics(annual["delivered_kWh"], finance)

    lpsp_monthly = annual["unmet_kWh"] / max(annual["load_kWh"], 1e-9)
    reliability = {
        "lpsp_monthly": lpsp_monthly,
        "coverage_monthly": 1.0 - lpsp_monthly,
        "worst_month_coverage": float(monthly["coverage"].min()),
    }

    result = {
        "island": island,
        "capacities": dict(capacities),
        "monthly": monthly.reset_index().to_dict(orient="records"),
        "annual": annual,
        "capex": capex,
        "econ": econ,
        "carbon": carb,
        "reliability": reliability,
        "plf_target": annual["delivered_kWh"] / (float(capacities["load_kW"]) * 8760.0),
    }

    # Hourly refinement (Kadmat only)
    do_hourly = use_hourly
    
    # Robustly find the hourly key for the island (handles "kadmat", "Kadmat", "Hourly_Kadmat", etc.)
    hourly_key = None
    if "hourly" in dfs:
        for k in dfs["hourly"].keys():
            if island.lower() in k.lower():
                hourly_key = k
                break

    if do_hourly is None:
        do_hourly = hourly_key is not None

    if do_hourly and hourly_key:
        h = dfs["hourly"][hourly_key]
        gen = (
            float(capacities["wind_kW"]) * h["cf_wind"].to_numpy()
            + float(capacities["solar_kWp"]) * h["cf_fpv"].to_numpy()
            + float(capacities["otec_kW"]) * h["cf_otec"].to_numpy()
            + float(capacities["wave_kW"]) * h["cf_wave"].to_numpy()
        )
        load = h["load_flat_kW"].to_numpy()
        hr = bess.dispatch_hourly(
            gen, load, float(capacities["bess_kWh"]),
            rte=float(finance["bess_round_trip_eff"]),
            dod=float(finance["bess_depth_of_discharge"]),
            c_rate=float(finance["bess_max_c_rate"]),
        )
        result["hourly"] = {
            "delivered_kWh": hr["delivered_kWh"],
            "unmet_kWh": hr["unmet_kWh"],
            "curtailed_kWh": hr["curtailed_kWh"],
            "lpsp": hr["lpsp"],
            "lole_hours": hr["lole_hours"],
            "soc_kWh": hr["soc_kWh"],
        }
        reliability["lpsp_hourly"] = hr["lpsp"]

    result["tech_scores"] = scoring.technology_scores(island, dfs)

    return result