"""Single configuration: full evaluation, returns a JSON-safe dict."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import generation, bess, economics, carbon, scoring


def evaluate(island: str, capacities: dict, dfs: dict,
             use_hourly: bool | None = None) -> dict:
    """Full pipeline for one configuration."""

    # 1. Base Generation (Fallback to rough monthly model)
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

    # 2. Hourly Refinement (Identify 8760 file via robust matching)
    island_norm = island.replace("_", " ").strip().lower()
    hourly_key = None
    if "hourly" in dfs:
        for k in dfs["hourly"].keys():
            k_norm = str(k).replace("_", " ").strip().lower()
            if island_norm == k_norm or island_norm in k_norm or k_norm in island_norm:
                hourly_key = k
                break

    do_hourly = use_hourly if use_hourly is not None else (hourly_key is not None)
    finance = dfs["finance"]
    hr_result = None

    # 3. High-Fidelity Override (If real 8760 API data exists)
    if do_hourly and hourly_key:
        h = dfs["hourly"][hourly_key]
        
        gen_wind = float(capacities.get("wind_kW", 0)) * h["cf_wind"].to_numpy()
        gen_fpv = float(capacities.get("solar_kWp", 0)) * h["cf_fpv"].to_numpy()
        gen_otec = float(capacities.get("otec_kW", 0)) * h["cf_otec"].to_numpy()
        gen_wave = float(capacities.get("wave_kW", 0)) * h["cf_wave"].to_numpy()
        gen = gen_wind + gen_fpv + gen_otec + gen_wave
        
        target_load = float(capacities.get("load_kW", 1000.0))
        load = np.full(len(gen), target_load)
        
        hr_result = bess.dispatch_hourly(
            gen, load, float(capacities.get("bess_kWh", 0)),
            rte=float(finance["bess_round_trip_eff"]),
            dod=float(finance["bess_depth_of_discharge"]),
            c_rate=float(finance["bess_max_c_rate"]),
        )
        
        annual["gen_wind_kWh"] = float(gen_wind.sum())
        annual["gen_fpv_kWh"] = float(gen_fpv.sum())
        annual["gen_otec_kWh"] = float(gen_otec.sum())
        annual["gen_wave_kWh"] = float(gen_wave.sum())
        annual["gen_total_kWh"] = float(gen.sum())
        annual["load_kWh"] = float(load.sum())
        annual["delivered_kWh"] = float(hr_result["delivered_kWh"])
        annual["unmet_kWh"] = float(hr_result["unmet_kWh"])
        annual["surplus_kWh"] = float(hr_result["curtailed_kWh"])
        
        # OVERRIDE the monthly dataframe directly
        if "timestamp_local" in h.columns:
            df_agg = pd.DataFrame({
                "month_num": h["timestamp_local"].dt.month,
                "gen_wind_kWh": gen_wind,
                "gen_fpv_kWh": gen_fpv,
                "gen_otec_kWh": gen_otec,
                "gen_wave_kWh": gen_wave,
                "gen_total_kWh": gen,
                "load_kWh": load,
                "delivered_kWh": hr_result["hourly_delivered"],
                "surplus_kWh": hr_result["hourly_curtailed"],
                "unmet_kWh": hr_result["hourly_unmet"]
            }).groupby("month_num").sum()
            
            # Reindex to safely fill missing months with 0 without breaking alignment
            df_agg = df_agg.reindex(monthly.index, fill_value=0.0)
            
            for col in df_agg.columns:
                if col in monthly.columns:
                    monthly[col] = df_agg[col].values

    # 4. Economics (Calculated AFTER hourly dispatch for exact LCOE/CoS)
    capex, subsidy = economics.compute_capex(capacities, dfs["tech"], finance)
    opex = economics.compute_annual_opex(capacities, dfs["tech"])
    repl = economics.bess_replacement_pv(capex.get("bess_kWh", 0), finance)

    econ = economics.cost_metrics(
        capex, subsidy, opex, repl,
        annual["delivered_kWh"], annual["load_kWh"], annual["unmet_kWh"],
        finance,
    )
    
    # 5. Carbon Metrics
    carb = carbon.carbon_metrics(annual["delivered_kWh"], finance)

    # 6. Reliability Metrics
        # 6. Reliability Metrics
    lpsp_annual = annual["unmet_kWh"] / max(annual["load_kWh"], 1e-9)
    reliability = {
        "lpsp_annual": lpsp_annual, 
        "lpsp_monthly": lpsp_annual, # Kept for backward compatibility
        "coverage_annual": 1.0 - lpsp_annual,
        "coverage_monthly": 1.0 - lpsp_annual,
        "worst_month_coverage": float(monthly["coverage"].min()) if "coverage" in monthly else 1.0,
    }

    if hr_result:
        reliability["lpsp_hourly"] = hr_result["lpsp"]
        reliability["coverage_hourly"] = 1.0 - hr_result["lpsp"]

    # 7. Build Final Result
    result = {
        "island": island,
        "capacities": dict(capacities),
        "monthly": monthly.reset_index().to_dict(orient="records"),
        "annual": annual,
        "capex": capex,
        "econ": econ,
        "carbon": carb,
        "reliability": reliability,
        "plf_target": annual["delivered_kWh"] / (float(capacities.get("load_kW", 1000.0)) * 8760.0),
    }

    resolved_tz = "Unknown"
    if do_hourly and hourly_key and "timezone" in dfs["hourly"][hourly_key].columns:
        resolved_tz = dfs["hourly"][hourly_key]["timezone"].iloc[0]
        
    result["timezone"] = resolved_tz

    if hr_result:
        result["hourly"] = {
            "delivered_kWh": hr_result["delivered_kWh"],
            "unmet_kWh": hr_result["unmet_kWh"],
            "curtailed_kWh": hr_result["curtailed_kWh"],
            "lpsp": hr_result["lpsp"],
            "lole_hours": hr_result["lole_hours"],
            "soc_kWh": hr_result["soc_kWh"],
        }

    result["tech_scores"] = scoring.technology_scores(island, dfs)

    return result