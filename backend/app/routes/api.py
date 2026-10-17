"""JSON API endpoints."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request
import pandas as pd

from app.engine.config_eval import evaluate
from app.engine.optimizer import optimize
from app.engine import economics
from app.config import APP_DEFAULTS
from app.references import citations
import time
import uuid

bp = Blueprint("api", __name__)


@bp.get("/references")
def api_references():
    """Author–date label and link per reference key, for citations like "(IRENA, 2024)"."""
    return jsonify({"ok": True, "citations": citations()})

@bp.get("/health")
def health():
    d = current_app.config["DATA"]
    return jsonify({
        "ok": True,
        "islands": len(d["islands"]),
        "tech": list(d["tech"].index),
        "hourly_islands": list(d["hourly"].keys()),
        "crf": economics.crf(  # at the nominal rate the costs use (DCF model)
            economics.get_nominal_rate(d["finance"]),
            float(d["finance"]["project_life_yr"]),
        ),
    })


@bp.get("/islands")
def islands():
    d = current_app.config["DATA"]
    return jsonify({"ok": True, "islands": sorted(d["islands"].index.tolist())})


@bp.get("/tech")
def tech():
    """Technology parameters (data/processed/tech_params.csv) for the planner's (i) info boxes."""
    t = current_app.config["DATA"]["tech"]
    params = {
        name: {k: (None if pd.isna(v) else v) for k, v in row.items()}
        for name, row in t.iterrows()
    }
    return jsonify({"ok": True, "tech": params})


@bp.get("/finance")
def finance():
    """Finance parameters (data/processed/finance_params.json), for the planner's KPI info boxes."""
    return jsonify({"ok": True, "finance": current_app.config["DATA"]["finance"]})


@bp.get("/defaults")
def defaults():
    return jsonify({"ok": True, "defaults": APP_DEFAULTS})


@bp.post("/evaluate")
def api_evaluate():
    body = request.get_json(force=True) or {}
    dfs = current_app.config["DATA"]

    island = body.get("island")
    if island not in dfs["islands"].index:
        return jsonify({"ok": False, "error": f"unknown island: {island}"}), 400

    caps = body.get("capacities", {})
    capacities = {
        "wind_kW":   float(caps.get("wind_kW", 0)),
        "solar_kWp": float(caps.get("solar_kWp", 0)),
        "otec_kW":   float(caps.get("otec_kW", 0)),
        "wave_kW":   float(caps.get("wave_kW", 0)),
        "bess_kWh":  float(caps.get("bess_kWh", 0)),
        "load_kW":   float(body.get("load_kW", 1000)),
    }

    try:
        result = evaluate(island, capacities, dfs)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

    run_id = str(uuid.uuid4())
    if "CACHE" not in current_app.config:
        current_app.config["CACHE"] = {}
    current_app.config["CACHE"][run_id] = result
    
    return jsonify({"ok": True, "result": result, "run_id": run_id})

@bp.post("/optimize")
def api_optimize():
    body = request.get_json(force=True) or {}
    dfs = current_app.config["DATA"]

    island = body.get("island")
    if island not in dfs["islands"].index:
        return jsonify({"ok": False, "error": f"unknown island: {island}"}), 400

    load_kW = float(body.get("load_kW", 1000))
    # The whole load must be met (LPSP 0), as in the team's main
    lpsp_target = float(APP_DEFAULTS["reliability_target_lpsp"])
    mins = {k: float(body.get(k, APP_DEFAULTS[k]))
            for k in ("min_wind_pct", "min_solar_pct", "min_otec_pct", "min_wave_pct")}

    current_app.logger.info(
        f"OPTIMIZE START: {island} | Target Load: {load_kW} kW | LPSP Target: {lpsp_target:.0%} | "
        f"Min Wind: {mins['min_wind_pct']} | Min Solar: {mins['min_solar_pct']} | "
        f"Min OTEC: {mins['min_otec_pct']} | Min Wave: {mins['min_wave_pct']}"
    )
    start_time = time.time()

    try:
        result = optimize(island, load_kW, dfs, lpsp_target=lpsp_target, **mins)
    except Exception as exc:
        current_app.logger.error(f"OPTIMIZE FAILED: {str(exc)}")
        return jsonify({"ok": False, "error": str(exc)}), 500

    elapsed = time.time() - start_time
    search_size = result.get("search_size", 0)
    feasible_count = len(result.get("feasible", []))
    
    current_app.logger.info(
        f"OPTIMIZE DONE in {elapsed:.2f}s | "
        f"Evaluated {search_size} mixes | Found {feasible_count} feasible options."
    )

    # Kept so the PDF export can list the ranked mixes (/export/pdf/<run_id>?opt=<opt_id>)
    opt_id = str(uuid.uuid4())
    current_app.config.setdefault("OPT_CACHE", {})[opt_id] = {
        "island": island, "load_kW": load_kW, "feasible": result.get("feasible", [])[:10],
        "minimums": {k: v for k, v in mins.items() if v > 0},  # shown in the PDF report
    }

    return jsonify({"ok": True, "result": result, "opt_id": opt_id})

@bp.post("/compare")
def api_compare():
    body = request.get_json(force=True) or {}
    dfs = current_app.config["DATA"]

    caps = body.get("capacities", {})
    capacities = {
        "wind_kW":   float(caps.get("wind_kW", 0)),
        "solar_kWp": float(caps.get("solar_kWp", 0)),
        "otec_kW":   float(caps.get("otec_kW", 0)),
        "wave_kW":   float(caps.get("wave_kW", 0)),
        "bess_kWh":  float(caps.get("bess_kWh", 0)),
        "load_kW":   float(body.get("load_kW", 1000)),
    }

    results = []
    # Evaluate the mix for every island in the dataset
    for island in dfs["islands"].index:
        try:
            res = evaluate(island, capacities, dfs, use_hourly=None)
            results.append({
                "island": island,
                "lcoe": res["econ"]["LCOE_RE_INR_per_kWh"],
                "cos": res["econ"]["cost_of_service_INR_per_kWh"],
                "lpsp": res["reliability"]["lpsp_monthly"],
                "plf": res["plf_target"],
                "capex_INR": res["econ"]["capex_INR"],
                "co2_avoided_t": res["carbon"]["co2_avoided_t"],
            })
        except Exception as e:
            current_app.logger.warning(f"Failed to evaluate {island} for comparison: {e}")

    # Sort the results by LCOE (cheapest first)
    results.sort(key=lambda x: x["lcoe"])
    return jsonify({"ok": True, "result": results})