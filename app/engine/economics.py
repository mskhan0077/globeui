"""Annualized cost model."""
from __future__ import annotations

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
    return (
        capex_bess_INR
        * float(finance["bess_replacement_cost_fraction"])
        / (1 + float(finance["discount_rate_real"])) ** float(finance["bess_replacement_year"])
    )

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
    r = float(finance["discount_rate_real"])
    n = float(finance["project_life_yr"])
    crf_val = crf(r, n)

    capex_total = sum(capex.values()) - subsidy_INR
    a_cap = (capex_total + bess_repl_pv_INR) * crf_val

    diesel_cost = unmet_kWh * float(finance["diesel_fuel_cost_INR_per_kWh"])

    lcoe_re = (a_cap + opex_annual_INR) / max(delivered_kWh, 1e-9)
    cos = (a_cap + opex_annual_INR + diesel_cost) / max(load_kWh, 1e-9)

    return {
        "capex_INR": capex_total,
        "subsidy_INR": subsidy_INR,
        "opex_annual_INR": opex_annual_INR,
        "bess_repl_pv_INR": bess_repl_pv_INR,
        "annualized_capital_INR": a_cap,
        "diesel_fuel_cost_INR": diesel_cost,
        "LCOE_RE_INR_per_kWh": lcoe_re,
        "cost_of_service_INR_per_kWh": cos,
        "crf": crf_val,
    }