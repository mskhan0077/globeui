"""Grid-search optimizer + SciPy HiGHS Exact LP over monthly engine."""
from __future__ import annotations

import itertools
import numpy as np
from scipy.optimize import linprog
from . import economics

def get_dynamic_grid(load_kW: float) -> dict:
    """Scale the grid search space dynamically based on target load."""
    max_w_s = max(4000, int(load_kW * 10))
    max_o   = max(1500, int(load_kW * 2))
    max_v   = max(2000, int(load_kW * 4))
    max_b   = max(20000, int(load_kW * 50))
    
    step_w_s = max(500, int(np.ceil((max_w_s / 5) / 100) * 100))
    step_o   = max(500, int(np.ceil((max_o / 3) / 100) * 100))
    step_v   = max(500, int(np.ceil((max_v / 4) / 100) * 100))
    step_b   = max(3000, int(np.ceil((max_b / 6) / 500) * 500))
    
    return {
        "wind_kW":   list(range(0, max_w_s + 1, step_w_s)),
        "solar_kWp": list(range(0, max_w_s + 1, step_w_s)),
        "otec_kW":   list(range(0, max_o + 1, step_o)),
        "wave_kW":   list(range(0, max_v + 1, step_v)), 
        "bess_kWh":  list(range(0, max_b + 1, step_b)),
    }

def solve_monthly_lp(island: str, load_kW: float, dfs: dict, lpsp_target: float) -> dict | None:
    """Mathematically optimal sizing using SciPy HiGHS."""
    w, s, o, v = dfs["wind"].loc[island], dfs["solar"].loc[island], dfs["otec"].loc[island], dfs["wave"].loc[island]
    finance = dfs["finance"]
    
    # Localize Tech Parameters for Brest France
    tech = dfs["tech"].copy()
    if "france" in island.lower() or "brest" in island.lower():
        tech["capex_island_INR"] *= 2.5
        tech["opex_INR_per_unit_yr"] *= 2.5

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

    def calc_a(name, is_solar=False, is_bess=False):
        c_base = float(tech.loc[name, "capex_island_INR"])
        lifetime = float(tech.loc[name, "lifetime_yr"])
        crf_val = economics.crf(r_nom, lifetime)
        
        if is_bess:
            opex_nominal = c_base * float(tech.loc[name, "opex_pct_of_capex"])
            repl_yr = float(finance["bess_replacement_year"])
            pi_bess = float(finance.get("inflation_rate_bess", -0.05))
            repl_future = c_base * float(finance["bess_replacement_cost_fraction"]) * ((1+pi_bess)**repl_yr)
            repl_pv = repl_future / ((1+r_nom)**repl_yr)
            a = c_base * crf_val 
            a += (opex_nominal * pv_factor_opex + repl_pv) * crf_proj
            a -= float(finance["bess_vgf_INR_per_kWh"]) * crf_proj
            return a
        else:
            opex_nominal = float(tech.loc[name, "opex_INR_per_unit_yr"])
            a = c_base * crf_val
            a += opex_nominal * pv_factor_opex * crf_proj
            if is_solar:
                a -= float(finance["fpv_cfa_subsidy_INR_per_kW"]) * crf_proj
            return a

    a_w = calc_a("Wind")
    a_s = calc_a("Floating Solar PV", is_solar=True)
    a_o = calc_a("OTEC")
    a_v = calc_a("Wave")
    a_b = calc_a("BESS", is_bess=True)
    
    pi_diesel = float(finance.get("inflation_rate_diesel", 0.07))
    pv_factor_diesel = economics.growing_annuity_pv(r_nom, pi_diesel, n_proj)
    c_diesel = float(finance["diesel_fuel_cost_INR_per_kWh"]) * pv_factor_diesel * crf_proj
    
    c_curtail = 0.1 

    N = 5 + 9 * T
    c = np.zeros(N)
    c[0:5] = [a_w, a_s, a_o, a_v, a_b]
    
    idx_g   = lambda i, t: 5 + i * T + t
    idx_ch  = lambda t: 5 + 4 * T + t
    idx_dis = lambda t: 5 + 5 * T + t
    idx_soc = lambda t: 5 + 6 * T + t
    idx_u   = lambda t: 5 + 7 * T + t
    idx_k   = lambda t: 5 + 8 * T + t

    for t in range(T):
        c[idx_u(t)] = c_diesel * hours[t]
        c[idx_k(t)] = c_curtail * hours[t]

    A_eq, b_eq, A_ub, b_ub = [], [], [], []

    for i in range(4):
        for t in range(T):
            row = np.zeros(N)
            row[idx_g(i, t)] = 1
            row[i] = -cfs[i][t]
            A_ub.append(row); b_ub.append(0)

    for t in range(T):
        row = np.zeros(N)
        for i in range(4): row[idx_g(i, t)] = 1
        row[idx_dis(t)] = 1; row[idx_ch(t)] = -1; row[idx_k(t)] = -1; row[idx_u(t)] = 1
        A_eq.append(row); b_eq.append(load_kW)

    eta = np.sqrt(float(finance["bess_round_trip_eff"]))
    dod = float(finance["bess_depth_of_discharge"])
    rho = float(finance["bess_max_c_rate"])
    
    sigma_hourly = 0.015
    for t in range(T):
        sigma_monthly = 1.0 - (1.0 - sigma_hourly) ** hours[t]
        row = np.zeros(N)
        row[idx_soc(t)] = 1
        row[idx_soc(T-1 if t == 0 else t-1)] = -(1 - sigma_monthly)
        row[idx_ch(t)] = -eta * hours[t]
        row[idx_dis(t)] = (1.0 / eta) * hours[t]
        A_eq.append(row); b_eq.append(0)

    for t in range(T):
        row = np.zeros(N); row[idx_soc(t)] = 1; row[4] = -dod
        A_ub.append(row); b_ub.append(0)
        row = np.zeros(N); row[idx_ch(t)] = 1; row[4] = -rho
        A_ub.append(row); b_ub.append(0)
        row = np.zeros(N); row[idx_dis(t)] = 1; row[4] = -rho
        A_ub.append(row); b_ub.append(0)
        row = np.zeros(N); row[idx_u(t)] = 1
        A_ub.append(row); b_ub.append(load_kW)

    row = np.zeros(N)
    for t in range(T): row[idx_u(t)] = hours[t]
    A_ub.append(row); b_ub.append(lpsp_target * load_kW * np.sum(hours))

    bounds = [(0, None)] * N
    bounds[0] = (0, max(10000, load_kW * 20.0))  
    bounds[1] = (0, max(10000, load_kW * 20.0))  
    bounds[2] = (0, max(3000, load_kW * 3.0))   
    bounds[3] = (0, max(5000, load_kW * 5.0))   
    bounds[4] = (0, max(50000, load_kW * 50.0)) 

    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
    
    if res.success:
        def snap(val, step): return float(np.ceil(max(val, 0) / step) * step)
        return {
            "wind_kW": snap(res.x[0], 100),
            "solar_kWp": snap(res.x[1], 100),
            "otec_kW": snap(res.x[2], 100),
            "wave_kW": snap(res.x[3], 100),
            "bess_kWh": snap(res.x[4], 500)
        }
    return None


def _iter_combos(grid: dict):
    keys = list(grid.keys())
    for values in itertools.product(*(grid[k] for k in keys)):
        yield dict(zip(keys, values))

def optimize(island: str, load_kW: float, dfs: dict, weights: dict,
             lpsp_target: float = 0.05) -> dict:
    """Run exact LP to find optimal, then enumerate dynamic grid for alternatives."""
    from .config_eval import evaluate

    grid = get_dynamic_grid(load_kW)
    results: list[dict] = []

    # FAST PATH: Pre-calculate CF sums for pruning 
    island_norm = island.replace("_", " ").strip().lower()
    hourly_key = None
    if "hourly" in dfs:
        for k in dfs["hourly"].keys():
            k_norm = str(k).replace("_", " ").strip().lower()
            if island_norm == k_norm or island_norm in k_norm or k_norm in island_norm:
                hourly_key = k
                break

    if hourly_key:
        h = dfs["hourly"][hourly_key]
        cf_sums = {
            "wind_kW": h["cf_wind"].sum(),
            "solar_kWp": h["cf_fpv"].sum(),
            "otec_kW": h["cf_otec"].sum(),
            "wave_kW": h["cf_wave"].sum()
        }
    else:
        cf_sums = {k: 0 for k in ["wind_kW", "solar_kWp", "otec_kW", "wave_kW"]}

    load_annual = load_kW * 8760
    min_gen_needed = load_annual * (1 - lpsp_target)

    # Exact Math Optimization
    lp_caps = solve_monthly_lp(island, load_kW, dfs, lpsp_target)
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
                    "feasible": True,
                    "is_lp_optimal": True 
                })
        except Exception:
            pass

    # Grid Search Enumeration
    for caps in _iter_combos(grid):
        caps = {**caps, "load_kW": load_kW}
        
        # PRUNING: check if physical max generation is enough
        total_gen = sum(caps[k] * cf_sums[k] for k in cf_sums)
        if total_gen < min_gen_needed:
            continue
            
        try:
            # FAST EVALUATION: Skip Pandas/UI formatting
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
            "feasible": True,
            "is_lp_optimal": False
        })

    feasible = [r for r in results if r.get("feasible", False)]
    infeasible = [r for r in results if not r.get("feasible", True)]

    def score(row):
        return (1.0 / max(row["lcoe"], 1e-6)) + 0.1 * (1.0 / max(row["capex_INR"] / 1e7, 1e-6))

    feasible_sorted = sorted(feasible, key=score, reverse=True)
    infeasible.sort(key=lambda r: r["lpsp"])

    return {
        "island": island,
        "load_kW": load_kW,
        "recommended": feasible_sorted[0] if feasible_sorted else None,
        "feasible": feasible_sorted[:20],
        "infeasible": infeasible[:10],
        "search_size": len(results),
    }