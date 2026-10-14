"""Grid-search optimizer + SciPy HiGHS Exact LP over monthly engine."""
from __future__ import annotations

import itertools
import numpy as np
from scipy.optimize import linprog
from . import economics


def get_dynamic_grid(load_kW: float) -> dict:
    """Scale the grid search space dynamically based on target load."""
    max_w_s = max(3000, int(load_kW * 4))
    max_o   = max(1500, int(load_kW * 1.5))
    max_b   = max(10000, int(load_kW * 12))
    
    # Target roughly 5-6 points per dimension
    step_w_s = max(500, int(np.ceil((max_w_s / 5) / 100) * 100))
    step_o   = max(500, int(np.ceil((max_o / 3) / 100) * 100))
    step_b   = max(1000, int(np.ceil((max_b / 5) / 500) * 500))
    
    return {
        "wind_kW":   list(range(0, max_w_s + 1, step_w_s)),
        "solar_kWp": list(range(0, max_w_s + 1, step_w_s)),
        "otec_kW":   list(range(0, max_o + 1, step_o)),
        "wave_kW":   [0],
        "bess_kWh":  list(range(0, max_b + 1, step_b)),
    }


def solve_monthly_lp(island: str, load_kW: float, dfs: dict, lpsp_target: float) -> dict | None:
    """Mathematically optimal sizing using SciPy HiGHS."""
    w, s, o, v = dfs["wind"].loc[island], dfs["solar"].loc[island], dfs["otec"].loc[island], dfs["wave"].loc[island]
    tech, finance = dfs["tech"], dfs["finance"]

    hours = w["hours"].astype(float).values
    T = len(hours)
    cfs = [
        w["cf_net_after_losses"].astype(float).values,
        s["cf_fpv"].astype(float).values,
        o["cf_otec"].astype(float).values,
        v["cf_wec_net"].astype(float).values,
    ]

    r = float(finance["discount_rate_real"])
    n_proj = float(finance["project_life_yr"])
    crf_proj = economics.crf(r, n_proj)

    def calc_a(name, is_solar=False, is_bess=False):
        c_base = float(tech.loc[name, "capex_island_INR"])
        lifetime = float(tech.loc[name, "lifetime_yr"])
        crf_val = economics.crf(r, lifetime)
        if is_bess:
            opex = c_base * float(tech.loc[name, "opex_pct_of_capex"])
            repl_yr = float(finance["bess_replacement_year"])
            repl_pv = c_base * float(finance["bess_replacement_cost_fraction"]) / (1+r)**repl_yr
            return c_base * crf_val + opex + repl_pv * crf_proj - float(finance["bess_vgf_INR_per_kWh"]) * crf_proj
        else:
            opex = float(tech.loc[name, "opex_INR_per_unit_yr"])
            a = c_base * crf_val + opex
            if is_solar:
                a -= float(finance["fpv_cfa_subsidy_INR_per_kW"]) * crf_proj
            return a

    a_w = calc_a("Wind")
    a_s = calc_a("Floating Solar PV", is_solar=True)
    a_o = calc_a("OTEC")
    a_v = calc_a("Wave")
    a_b = calc_a("BESS", is_bess=True)
    c_diesel = float(finance["diesel_fuel_cost_INR_per_kWh"])

    # Variables: 5 capacities + T*(g_w, g_s, g_o, g_v, ch, dis, soc, u, k) = 5 + 9T
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

    A_eq, b_eq, A_ub, b_ub = [], [], [], []

    # 1. Gen limits: g_i[t] <= CF_i[t] * P_i
    for i in range(4):
        for t in range(T):
            row = np.zeros(N)
            row[idx_g(i, t)] = 1
            row[i] = -cfs[i][t]
            A_ub.append(row)
            b_ub.append(0)

    # 2. Bus balance: sum(g) + dis - ch - k + u = L
    for t in range(T):
        row = np.zeros(N)
        for i in range(4): row[idx_g(i, t)] = 1
        row[idx_dis(t)] = 1; row[idx_ch(t)] = -1; row[idx_k(t)] = -1; row[idx_u(t)] = 1
        A_eq.append(row)
        b_eq.append(load_kW)

    # 3. SOC tracking
    eta = np.sqrt(float(finance["bess_round_trip_eff"]))
    for t in range(T):
        row = np.zeros(N)
        row[idx_soc(t)] = 1
        row[idx_soc(T-1 if t == 0 else t-1)] = -1
        row[idx_ch(t)] = -eta * hours[t]
        row[idx_dis(t)] = (1.0 / eta) * hours[t]
        A_eq.append(row)
        b_eq.append(0)

    # 4. Envelopes & Power Limits
    dod = float(finance["bess_depth_of_discharge"])
    rho = float(finance["bess_max_c_rate"])
    for t in range(T):
        row = np.zeros(N); row[idx_soc(t)] = 1; row[4] = -dod
        A_ub.append(row); b_ub.append(0)
        row = np.zeros(N); row[idx_ch(t)] = 1; row[4] = -rho
        A_ub.append(row); b_ub.append(0)
        row = np.zeros(N); row[idx_dis(t)] = 1; row[4] = -rho
        A_ub.append(row); b_ub.append(0)
        row = np.zeros(N); row[idx_u(t)] = 1
        A_ub.append(row); b_ub.append(load_kW)

    # 5. Annual LPSP target
    row = np.zeros(N)
    for t in range(T): row[idx_u(t)] = hours[t]
    A_ub.append(row)
    b_ub.append(lpsp_target * load_kW * np.sum(hours))

    # DYNAMIC BOUNDS BASED ON LOAD
    bounds = [(0, None)] * N
    bounds[0] = (0, max(3000, load_kW * 5))  # Wind
    bounds[1] = (0, max(3000, load_kW * 5))  # Solar
    bounds[2] = (0, max(1500, load_kW * 2))  # OTEC
    bounds[3] = (0, max(1000, load_kW * 1))  # Wave
    bounds[4] = (0, max(10000, load_kW * 15)) # BESS

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
             lpsp_target: float = 0.01) -> dict:
    """Run exact LP to find optimal, then enumerate dynamic grid for alternatives."""
    from .config_eval import evaluate

    grid = get_dynamic_grid(load_kW)
    results: list[dict] = []

    # 1. Exact Math Optimization
    lp_caps = solve_monthly_lp(island, load_kW, dfs, lpsp_target)
    if lp_caps:
        lp_caps["load_kW"] = load_kW
        try:
            r = evaluate(island, lp_caps, dfs, use_hourly=False)
            lpsp = r["reliability"]["lpsp_monthly"]
            results.append({
                "capacities": {k: lp_caps.get(k, 0) for k in grid.keys()},
                "lcoe": r["econ"]["LCOE_RE_INR_per_kWh"],
                "cos": r["econ"]["cost_of_service_INR_per_kWh"],
                "lpsp": lpsp,
                "coverage": 1.0 - lpsp,
                "plf": r["plf_target"],
                "co2_avoided_t": r["carbon"]["co2_avoided_t"],
                "capex_INR": r["econ"]["capex_INR"],
                "feasible": lpsp <= lpsp_target,
                "is_lp_optimal": True
            })
        except Exception:
            pass

    # 2. Grid Search Enumeration
    for caps in _iter_combos(grid):
        caps = {**caps, "load_kW": load_kW}
        try:
            r = evaluate(island, caps, dfs, use_hourly=False)
        except Exception:
            continue
        lpsp = r["reliability"]["lpsp_monthly"]
        results.append({
            "capacities": {k: caps[k] for k in grid.keys()},
            "lcoe": r["econ"]["LCOE_RE_INR_per_kWh"],
            "cos": r["econ"]["cost_of_service_INR_per_kWh"],
            "lpsp": lpsp,
            "coverage": 1.0 - lpsp,
            "plf": r["plf_target"],
            "co2_avoided_t": r["carbon"]["co2_avoided_t"],
            "capex_INR": r["econ"]["capex_INR"],
            "feasible": lpsp <= lpsp_target,
            "is_lp_optimal": False
        })

    feasible = [r for r in results if r["feasible"]]
    infeasible = [r for r in results if not r["feasible"]]

    def score(row):
        return (
            0.5 * (1.0 / max(row["lcoe"], 1e-6))
            + 0.3 * row["coverage"]
            + 0.2 * (1.0 / max(row["capex_INR"] / 1e7, 1e-6))
        )

    # Force the LP Optimal mix to stay at rank #1
    lp_mixes = [r for r in feasible if r["is_lp_optimal"]]
    grid_mixes = [r for r in feasible if not r["is_lp_optimal"]]
    
    grid_mixes.sort(key=score, reverse=True)
    feasible_sorted = lp_mixes + grid_mixes
    infeasible.sort(key=lambda r: r["lpsp"])

    return {
        "island": island,
        "load_kW": load_kW,
        "recommended": feasible_sorted[0] if feasible_sorted else None,
        "feasible": feasible_sorted[:20],
        "infeasible": infeasible[:10],
        "search_size": len(results),
    }