"""Grid-search optimizer + SciPy HiGHS exact LP over monthly engine."""
from __future__ import annotations

import itertools
import numpy as np
from scipy.optimize import linprog

from . import economics
from .common import SELF_DISCHARGE_PER_HOUR, find_hourly_key, localize_tech


def get_dynamic_grid(load_kW: float) -> dict:
    """Scale the grid search space dynamically based on target load."""
    max_w_s = max(5000, int(load_kW * 15))
    max_o = max(3000, int(load_kW * 3))
    max_v = max(5000, int(load_kW * 5))
    max_b = max(50000, int(load_kW * 100))

    step_w_s = max(500, int(np.ceil((max_w_s / 5) / 100) * 100))
    step_o = max(500, int(np.ceil((max_o / 3) / 100) * 100))
    step_v = max(500, int(np.ceil((max_v / 4) / 100) * 100))
    step_b = max(3000, int(np.ceil((max_b / 6) / 500) * 500))

    return {
        "wind_kW":   list(range(0, max_w_s + 1, step_w_s)),
        "solar_kWp": list(range(0, max_w_s + 1, step_w_s)),
        "otec_kW":   list(range(0, max_o + 1, step_o)),
        "wave_kW":   list(range(0, max_v + 1, step_v)),
        "bess_kWh":  list(range(0, max_b + 1, step_b)),
    }


def solve_monthly_lp(
    island: str,
    load_kW: float,
    dfs: dict,
    lpsp_target: float,
    min_wind_pct: float = 0.0,
    min_solar_pct: float = 0.0,
    min_otec_pct: float = 0.0,
    min_wave_pct: float = 0.0,
) -> dict | None:
    """Mathematically optimal sizing using SciPy HiGHS."""
    w = dfs["wind"].loc[island]
    s = dfs["solar"].loc[island]
    o = dfs["otec"].loc[island]
    v = dfs["wave"].loc[island]
    finance = dfs["finance"]
    tech = localize_tech(dfs["tech"], island)

    hours = w["hours"].astype(float).values
    T = len(hours)
    cfs = [
        w["cf_net_after_losses"].astype(float).values,
        s["cf_fpv"].astype(float).values,
        o["cf_otec"].astype(float).values,
        v["cf_wec_net"].astype(float).values,
    ]

    n_proj = float(finance["project_life_yr"])
    r_nom = economics.get_nominal_rate(finance)
    crf_proj = economics.crf(r_nom, n_proj)

    pi_opex = float(finance.get("inflation_rate_opex", 0.04))
    pv_factor_opex = economics.growing_annuity_pv(r_nom, pi_opex, n_proj)
    apply_subsidies = float(finance.get("apply_subsidies_flag", 0.0)) > 0.5

    def calc_a(name, is_solar=False, is_bess=False):
        capex_unit = float(tech.loc[name, "capex_island_INR"])
        opex_unit = economics.annual_opex_per_unit(tech, name)
        pv_opex_unit = opex_unit * pv_factor_opex

        repl_pv_unit = 0.0
        subsidy_unit = 0.0

        if is_bess:
            repl_yr = float(finance["bess_replacement_year"])
            pi_bess = float(finance.get("inflation_rate_bess", -0.05))
            repl_future = (
                capex_unit
                * float(finance["bess_replacement_cost_fraction"])
                * ((1 + pi_bess) ** repl_yr)
            )
            repl_pv_unit = repl_future / ((1 + r_nom) ** repl_yr)
            if apply_subsidies:
                subsidy_unit = float(finance["bess_vgf_INR_per_kWh"])

        if is_solar and apply_subsidies:
            subsidy_unit = float(finance["fpv_cfa_subsidy_INR_per_kW"])

        return (capex_unit + pv_opex_unit + repl_pv_unit - subsidy_unit) * crf_proj

    a_w = calc_a("Wind")
    a_s = calc_a("Floating Solar PV", is_solar=True)
    a_o = calc_a("OTEC")
    a_v = calc_a("Wave")
    a_b = calc_a("BESS", is_bess=True)

    pi_diesel = float(finance.get("inflation_rate_diesel", 0.07))
    pv_factor_diesel = economics.growing_annuity_pv(r_nom, pi_diesel, n_proj)
    c_diesel = float(finance["diesel_fuel_cost_INR_per_kWh"]) * pv_factor_diesel * crf_proj

    # Heavily penalize curtailment to enforce minimum overgeneration
    c_curtail = 1.0 

    N = 5 + 9 * T
    c = np.zeros(N)
    c[0:5] = [a_w, a_s, a_o, a_v, a_b]

    idx_g = lambda i, t: 5 + i * T + t
    idx_ch = lambda t: 5 + 4 * T + t
    idx_dis = lambda t: 5 + 5 * T + t
    idx_soc = lambda t: 5 + 6 * T + t
    idx_u = lambda t: 5 + 7 * T + t
    idx_k = lambda t: 5 + 8 * T + t

    for t in range(T):
        c[idx_u(t)] = c_diesel * hours[t]
        c[idx_k(t)] = c_curtail * hours[t]

    A_eq, b_eq, A_ub, b_ub = [], [], [], []

    for i in range(4):
        for t in range(T):
            row = np.zeros(N)
            row[idx_g(i, t)] = 1
            row[i] = -cfs[i][t]
            A_ub.append(row)
            b_ub.append(0)

    for t in range(T):
        row = np.zeros(N)
        for i in range(4):
            row[idx_g(i, t)] = 1
        row[idx_dis(t)] = 1
        row[idx_ch(t)] = -1
        row[idx_k(t)] = -1
        row[idx_u(t)] = 1
        A_eq.append(row)
        b_eq.append(load_kW)

    eta = np.sqrt(float(finance["bess_round_trip_eff"]))
    dod = float(finance["bess_depth_of_discharge"])
    rho = float(finance["bess_max_c_rate"])

    for t in range(T):
        sigma_monthly = 1.0 - (1.0 - SELF_DISCHARGE_PER_HOUR) ** hours[t]
        row = np.zeros(N)
        row[idx_soc(t)] = 1
        row[idx_soc(T - 1 if t == 0 else t - 1)] = -(1 - sigma_monthly)
        row[idx_ch(t)] = -eta * hours[t]
        row[idx_dis(t)] = (1.0 / eta) * hours[t]
        A_eq.append(row)
        b_eq.append(0)

    for t in range(T):
        row = np.zeros(N)
        row[idx_soc(t)] = 1
        row[4] = -dod
        A_ub.append(row)
        b_ub.append(0)

        row = np.zeros(N)
        row[idx_ch(t)] = 1
        row[4] = -rho
        A_ub.append(row)
        b_ub.append(0)

        row = np.zeros(N)
        row[idx_dis(t)] = 1
        row[4] = -rho
        A_ub.append(row)
        b_ub.append(0)

        # STRICT MONTHLY RELIABILITY: u[t] = 0
        row = np.zeros(N)
        row[idx_u(t)] = 1
        A_ub.append(row)
        b_ub.append(0.0)

    row = np.zeros(N)
    for t in range(T):
        row[idx_u(t)] = hours[t]
    A_ub.append(row)
    b_ub.append(lpsp_target * load_kW * np.sum(hours))

    # Minimum diversity constraints
    if min_wind_pct > 0:
        row = np.zeros(N)
        row[0] = -1
        A_ub.append(row)
        b_ub.append(-min_wind_pct * load_kW)

    if min_solar_pct > 0:
        row = np.zeros(N)
        row[1] = -1
        A_ub.append(row)
        b_ub.append(-min_solar_pct * load_kW)

    if min_otec_pct > 0:
        row = np.zeros(N)
        row[2] = -1
        A_ub.append(row)
        b_ub.append(-min_otec_pct * load_kW)

    if min_wave_pct > 0:
        row = np.zeros(N)
        row[3] = -1
        A_ub.append(row)
        b_ub.append(-min_wave_pct * load_kW)

    bounds = [(0, None)] * N
    bounds[0] = (0, max(10000, load_kW * 20.0))
    bounds[1] = (0, max(10000, load_kW * 20.0))
    bounds[2] = (0, max(3000, load_kW * 3.0))
    bounds[3] = (0, max(5000, load_kW * 5.0))
    bounds[4] = (0, max(50000, load_kW * 100.0))

    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")

    if res.success:
        def snap(val, step):
            return float(np.ceil(max(val, 0) / step) * step)

        return {
            "wind_kW": snap(res.x[0], 100),
            "solar_kWp": snap(res.x[1], 100),
            "otec_kW": snap(res.x[2], 100),
            "wave_kW": snap(res.x[3], 100),
            "bess_kWh": snap(res.x[4], 500),
        }
    return None


def _iter_combos(grid: dict):
    keys = list(grid.keys())
    for values in itertools.product(*(grid[k] for k in keys)):
        yield dict(zip(keys, values))


def optimize(
    island: str,
    load_kW: float,
    dfs: dict,
    lpsp_target: float = 0.0,
    min_wind_pct: float = 0.0,
    min_solar_pct: float = 0.0,
    min_otec_pct: float = 0.0,
    min_wave_pct: float = 0.0,
) -> dict:
    """Run exact LP to find optimal, then enumerate dynamic grid for alternatives."""
    from .config_eval import evaluate

    min_wind_pct = min(max(float(min_wind_pct), 0.0), 1.0)
    min_solar_pct = min(max(float(min_solar_pct), 0.0), 1.0)
    min_otec_pct = min(max(float(min_otec_pct), 0.0), 1.0)
    min_wave_pct = min(max(float(min_wave_pct), 0.0), 1.0)

    grid = get_dynamic_grid(load_kW)
    results: list[dict] = []

    hourly_key = find_hourly_key(island, dfs)
    if hourly_key:
        h = dfs["hourly"][hourly_key]
        cf_sums = {
            "wind_kW": h["cf_wind"].sum(),
            "solar_kWp": h["cf_fpv"].sum(),
            "otec_kW": h["cf_otec"].sum(),
            "wave_kW": h["cf_wave"].sum(),
        }
    else:
        cf_sums = {k: 0 for k in ["wind_kW", "solar_kWp", "otec_kW", "wave_kW"]}

    load_annual = load_kW * 8760
    min_gen_needed = load_annual * (1 - lpsp_target)

    lp_caps = solve_monthly_lp(
        island, load_kW, dfs, lpsp_target, 
        min_wind_pct, min_solar_pct, min_otec_pct, min_wave_pct
    )
    if lp_caps:
        lp_caps["load_kW"] = load_kW
        try:
            r = evaluate(island, lp_caps, dfs, use_hourly=True, fast=True)
            lpsp = r["reliability"].get("lpsp_hourly", r["reliability"].get("lpsp_annual", 1.0))

            if lpsp <= lpsp_target + 1e-4:
                results.append({
                    "capacities": {k: lp_caps.get(k, 0) for k in grid.keys()},
                    "lcoe": r["econ"]["LCOE_RE_INR_per_kWh"],
                    "cos": r["econ"]["cost_of_service_INR_per_kWh"],
                    "lpsp": lpsp,
                    "coverage": 1.0 - lpsp,
                    "plf": r["plf_target"],
                    "co2_avoided_t": r["carbon"]["co2_avoided_t"],
                    "capex_INR": r["econ"]["capex_INR"],
                    "overgen_ratio": r["annual"]["surplus_kWh"] / max(r["annual"]["load_kWh"], 1e-9),
                })
        except Exception:
            pass

    for caps in _iter_combos(grid):
        caps = {**caps, "load_kW": load_kW}

        if min_wind_pct > 0 and caps["wind_kW"] < min_wind_pct * load_kW:
            continue
        if min_solar_pct > 0 and caps["solar_kWp"] < min_solar_pct * load_kW:
            continue
        if min_otec_pct > 0 and caps["otec_kW"] < min_otec_pct * load_kW:
            continue
        if min_wave_pct > 0 and caps["wave_kW"] < min_wave_pct * load_kW:
            continue

        total_gen = sum(caps[k] * cf_sums[k] for k in cf_sums)
        if total_gen < min_gen_needed:
            continue

        try:
            r = evaluate(island, caps, dfs, use_hourly=True, fast=True)
        except Exception:
            continue

        lpsp = r["reliability"].get("lpsp_hourly", r["reliability"].get("lpsp_annual", 1.0))
        if lpsp > lpsp_target + 1e-4:
            continue

        results.append({
            "capacities": {k: caps[k] for k in grid.keys()},
            "lcoe": r["econ"]["LCOE_RE_INR_per_kWh"],
            "cos": r["econ"]["cost_of_service_INR_per_kWh"],
            "lpsp": lpsp,
            "coverage": 1.0 - lpsp,
            "plf": r["plf_target"],
            "co2_avoided_t": r["carbon"]["co2_avoided_t"],
            "capex_INR": r["econ"]["capex_INR"],
            "overgen_ratio": r["annual"]["surplus_kWh"] / max(r["annual"]["load_kWh"], 1e-9),
        })

    def score(row):
        # Balance LCOE and Overgeneration. 
        # We want lowest LCOE and lowest overgeneration.
        # If overgen is 0.1 (10%), it increases the effective cost by 10%.
        # This prevents the optimizer from picking a massive solar+bess system that costs 5% less but overgenerates 200%.
        return (1.0 / max(row["lcoe"], 1e-6)) / (1.0 + row["overgen_ratio"])

    feasible_sorted = sorted(results, key=score, reverse=True)

    return {
        "island": island,
        "load_kW": load_kW,
        "recommended": feasible_sorted[0] if feasible_sorted else None,
        "feasible": feasible_sorted[:20],
        "search_size": len(results),
    }