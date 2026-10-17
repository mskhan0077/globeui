"""Annualized cost model with Inflation and DCF."""
from __future__ import annotations

import numpy as np


CAPACITY_TO_TECH = {
    "wind_kW":   "Wind",
    "solar_kWp": "Floating Solar PV",
    "otec_kW":   "OTEC",
    "wave_kW":   "Wave",
    "bess_kWh":  "BESS",
}

def crf(rate: float, years: float) -> float:
    """Capital recovery factor."""
    return rate * (1 + rate) ** years / ((1 + rate) ** years - 1)

def growing_annuity_pv(rate_nom: float, rate_inf: float, years: float) -> float:
    """Present value of a growing annuity (1 unit per year)."""
    if abs(rate_nom - rate_inf) < 1e-6:
        return years / (1 + rate_nom)
    return (1 - ((1 + rate_inf) / (1 + rate_nom)) ** years) / (rate_nom - rate_inf)

def get_nominal_rate(finance: dict) -> float:
    r_real = float(finance["discount_rate_real"])
    pi_gen = float(finance.get("inflation_rate_general", 0.05))
    return (1 + r_real) * (1 + pi_gen) - 1

def compute_capex(capacities: dict, tech, finance: dict) -> tuple[dict, float]:
    """Return ({cap_key: INR}, subsidy_INR)."""
    capex = {}
    for cap_key, tech_name in CAPACITY_TO_TECH.items():
        unit_cost = float(tech.loc[tech_name, "capex_island_INR"])
        capex[cap_key] = float(capacities[cap_key]) * unit_cost

    subsidy = 0.0
    if float(finance.get("apply_subsidies_flag", 0.0)) > 0.5:
        subsidy = (
            float(capacities["solar_kWp"]) * float(finance["fpv_cfa_subsidy_INR_per_kW"])
            + float(capacities["bess_kWh"]) * float(finance["bess_vgf_INR_per_kWh"])
        )
    return capex, subsidy

def compute_annual_opex(capacities: dict, tech) -> float:
    om = 0.0
    for cap_key, tech_name in CAPACITY_TO_TECH.items():
        if "opex_INR_per_unit_yr" in tech.columns:
            om += float(capacities[cap_key]) * float(tech.loc[tech_name, "opex_INR_per_unit_yr"])
    return om

def bess_replacement_pv(capex_bess_INR: float, finance: dict) -> float:
    """Present value of the one-time BESS replacement."""
    r_nom = get_nominal_rate(finance)
    pi_bess = float(finance.get("inflation_rate_bess", -0.05))
    repl_yr = float(finance["bess_replacement_year"])
    cost_fraction = float(finance["bess_replacement_cost_fraction"])
    
    # Future cost escalates (or deflates) over time
    future_cost = capex_bess_INR * cost_fraction * ((1 + pi_bess) ** repl_yr)
    return future_cost / ((1 + r_nom) ** repl_yr)

def cost_metrics(
    capex: dict,
    subsidy_INR: float,
    opex_annual_INR: float,
    bess_repl_pv_INR: float,
    delivered_kWh: float,
    load_kWh: float,
    unmet_kWh: float,
    finance: dict,
) -> dict:
    n = float(finance["project_life_yr"])
    r_nom = get_nominal_rate(finance)
    crf_val = crf(r_nom, n)

    capex_total = sum(capex.values()) - subsidy_INR
    
    # PV of OPEX (Escalating)
    pi_opex = float(finance.get("inflation_rate_opex", 0.04))
    pv_factor_opex = growing_annuity_pv(r_nom, pi_opex, n)
    pv_opex = opex_annual_INR * pv_factor_opex

    # PV of Diesel (Escalating)
    pi_diesel = float(finance.get("inflation_rate_diesel", 0.07))
    pv_factor_diesel = growing_annuity_pv(r_nom, pi_diesel, n)
    pv_diesel = unmet_kWh * float(finance["diesel_fuel_cost_INR_per_kWh"]) * pv_factor_diesel

    # Total PV and EAC
    total_pv = capex_total + bess_repl_pv_INR + pv_opex + pv_diesel
    eac_total = total_pv * crf_val

    # LCOE uses Equivalent Annual Cost / Annual Energy
    lcoe_re = (capex_total + bess_repl_pv_INR) * crf_val + (pv_opex * crf_val)
    lcoe_re = lcoe_re / max(delivered_kWh, 1e-9)
    
    cos = eac_total / max(load_kWh, 1e-9)

    return {
        "capex_INR": capex_total,
        "subsidy_INR": subsidy_INR,
        "opex_annual_INR": opex_annual_INR, # Nominal Year 1
        "bess_repl_pv_INR": bess_repl_pv_INR,
        "annualized_capital_INR": capex_total * crf_val,
        "diesel_fuel_cost_INR": pv_diesel * crf_val, # Levelized annual diesel
        "LCOE_RE_INR_per_kWh": lcoe_re,
        "cost_of_service_INR_per_kWh": cos,
        "crf": crf_val,
        "nominal_discount_rate": r_nom
    }