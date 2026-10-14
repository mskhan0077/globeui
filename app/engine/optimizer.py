"""Grid-search optimizer over monthly engine."""
from __future__ import annotations

import itertools
import numpy as np


DEFAULT_GRID = {
    "wind_kW":   [0, 500, 1000, 1500, 2000, 2500, 3000],
    "solar_kWp": [0, 500, 1000, 1500, 2000, 2500, 3000],
    "otec_kW":   [0, 500, 1000, 1500],
    "wave_kW":   [0],
    "bess_kWh":  [0, 1000, 3000, 5000, 8000],
}


def _iter_combos(grid: dict):
    keys = list(grid.keys())
    for values in itertools.product(*(grid[k] for k in keys)):
        yield dict(zip(keys, values))


def optimize(island: str, load_kW: float, dfs: dict, weights: dict,
             lpsp_target: float = 0.01, grid: dict | None = None) -> dict:
    """Enumerate grid, evaluate each mix, return ranked feasible list."""
    from .config_eval import evaluate

    grid = grid or DEFAULT_GRID
    results: list[dict] = []

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
        })

    feasible = [r for r in results if r["feasible"]]
    infeasible = [r for r in results if not r["feasible"]]

    def score(row):
        # cheap, deterministic score: low LCOE, high coverage, low capex
        return (
            0.5 * (1.0 / max(row["lcoe"], 1e-6))
            + 0.3 * row["coverage"]
            + 0.2 * (1.0 / max(row["capex_INR"] / 1e7, 1e-6))
        )

    feasible.sort(key=score, reverse=True)
    infeasible.sort(key=lambda r: r["lpsp"])

    return {
        "island": island,
        "load_kW": load_kW,
        "recommended": feasible[0] if feasible else None,
        "feasible": feasible[:20],
        "infeasible": infeasible[:10],
        "search_size": len(results),
    }