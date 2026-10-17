"""Single configuration: full evaluation, returns a JSON-safe dict."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import generation, bess, economics, carbon, scoring
from .common import find_hourly_key, localize_tech

def evaluate(island: str, capacities: dict, dfs: dict,
             use_hourly: bool | None = None, fast: bool = False) -> dict:
    """Full pipeline for one configuration."""

    hourly_key = find_hourly_key(island, dfs)
    do_hourly = use_hourly if use_hourly is not None else (hourly_key is not None)
    finance = dfs["finance"]
    tech = localize_tech(dfs["tech"], island)

    hr_result = None

    if not (fast and do_hourly and hourly_key):
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
            "surplus_kWh": float(monthly["curtailed_kWh"].sum()),
            "unmet_kWh": float(monthly["unmet_kWh"].sum()),
        }
    else:
        monthly = None
        annual = {}

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

        annual["hours"] = float(len(gen))
        annual["gen_wind_kWh"] = float(gen_wind.sum())
        annual["gen_fpv_kWh"] = float(gen_fpv.sum())
        annual["gen_otec_kWh"] = float(gen_otec.sum())
        annual["gen_wave_kWh"] = float(gen_wave.sum())
        annual["gen_total_kWh"] = float(gen.sum())
        annual["load_kWh"] = float(load.sum())
        annual["delivered_kWh"] = float(hr_result["delivered_kWh"])
        annual["unmet_kWh"] = float(hr_result["unmet_kWh"])
        annual["surplus_kWh"] = float(hr_result["curtailed_kWh"])

        if not fast and "timestamp_local" in h.columns:
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
                "unmet_kWh": hr_result["hourly_unmet"],
            }).groupby("month_num").sum()

            df_agg = df_agg.reindex(monthly.index, fill_value=0.0)

            for col in df_agg.columns:
                if col in monthly.columns:
                    monthly[col] = df_agg[col].values

            monthly["coverage"] = np.where(
                monthly["load_kWh"] > 0,
                monthly["delivered_kWh"] / monthly["load_kWh"],
                0.0,
            )

    capex, subsidy = economics.compute_capex(capacities, tech, finance, dfs.get("discount"))
    opex = economics.compute_annual_opex(capacities, tech)
    repl = economics.bess_replacement_pv(capex.get("bess_kWh", 0), finance)

    econ = economics.cost_metrics(
        capex, subsidy, opex, repl,
        annual["delivered_kWh"], annual["load_kWh"], annual["unmet_kWh"],
        finance,
    )

    carb = carbon.carbon_metrics(annual["delivered_kWh"], finance)

    lpsp_annual = annual["unmet_kWh"] / max(annual["load_kWh"], 1e-9)
    reliability = {
        "lpsp_annual": lpsp_annual,
        "lpsp_monthly": lpsp_annual,
        "coverage_annual": 1.0 - lpsp_annual,
        "coverage_monthly": 1.0 - lpsp_annual,
    }

    if hr_result:
        reliability["lpsp_hourly"] = hr_result["lpsp"]
        reliability["coverage_hourly"] = 1.0 - hr_result["lpsp"]

    if not fast and monthly is not None:
        reliability["worst_month_coverage"] = (
            float(monthly["coverage"].min()) if "coverage" in monthly else 1.0
        )

    plf_target = annual["delivered_kWh"] / max(
        float(capacities.get("load_kW", 1000.0)) * annual["hours"], 1e-9
    )

    if fast:
        return {
            "annual": annual,
            "econ": econ,
            "carbon": carb,
            "reliability": reliability,
            "plf_target": plf_target,
        }

    stats = {}
    if monthly is not None:
        for tech_name, col_name in [
            ("wind", "gen_wind_kWh"),
            ("solar", "gen_fpv_kWh"),
            ("otec", "gen_otec_kWh"),
            ("wave", "gen_wave_kWh"),
            ("load", "load_kWh"),
        ]:
            if col_name in monthly.columns:
                vals = monthly[col_name].values / 1000.0
                stats[tech_name] = {
                    "mean": float(np.mean(vals)),
                    "median": float(np.median(vals)),
                    "std": float(np.std(vals)),
                    "min": float(np.min(vals)),
                    "max": float(np.max(vals)),
                }


    # Volume discount breakdown (list price vs discounted CAPEX per tech)
    capex_list, _ = economics.compute_capex(capacities, tech, finance)
    disc = dfs.get("discount")
    volume_discount = {}
    for cap_key, tech_name in economics.CAPACITY_TO_TECH.items():
        has_row = disc is not None and tech_name in disc.index
        unit_size = float(disc.loc[tech_name, "typical_unit_size"]) if has_row else 0.0
        list_inr = capex_list[cap_key]
        volume_discount[cap_key] = {
            "tech": tech_name,
            "unit_size": unit_size,
            "unit_basis": str(disc.loc[tech_name, "unit_basis"]) if has_row else "",
            "units": float(capacities.get(cap_key, 0)) / unit_size if unit_size > 0 else 0.0,
            "list_INR": list_inr,
            "discounted_INR": capex[cap_key],
            "discount_pct": 1.0 - capex[cap_key] / list_inr if list_inr > 0 else 0.0,
        }

    result = {
        "island": island,
        "capacities": dict(capacities),
        "monthly": monthly.reset_index().to_dict(orient="records"),
        "stats": stats,
        "annual": annual,
        "capex": capex,
        "volume_discount": volume_discount,
        "econ": econ,
        "carbon": carb,
        "reliability": reliability,
        "plf_target": plf_target,
    }

    # Timezone of the hourly data the result is based on (shown in the planner UI).
    result["timezone"] = "Unknown"
    if do_hourly and hourly_key and "timezone" in dfs["hourly"][hourly_key].columns:
        result["timezone"] = str(dfs["hourly"][hourly_key]["timezone"].iloc[0])

    if hr_result:
        result["hourly"] = {
            "delivered_kWh": hr_result["delivered_kWh"],
            "unmet_kWh": hr_result["unmet_kWh"],
            "curtailed_kWh": hr_result["curtailed_kWh"],
            "lpsp": hr_result["lpsp"],
            "lole_hours": hr_result["lole_hours"],
        }

    dfs_scoring = dict(dfs)
    dfs_scoring["tech"] = tech
    result["tech_scores"] = scoring.technology_scores(island, dfs_scoring)

    return result