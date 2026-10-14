"""JSON API endpoints."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from app.engine.config_eval import evaluate
from app.engine.optimizer import optimize
from app.config import APP_DEFAULTS
import time
import uuid

bp = Blueprint("api", __name__)

@bp.get("/health")
def health():
    d = current_app.config["DATA"]
    return jsonify({
        "ok": True,
        "islands": len(d["islands"]),
        "tech": list(d["tech"].index),
        "hourly_islands": list(d["hourly"].keys()),
        "crf": d["finance"]["capital_recovery_factor"],
    })


@bp.get("/islands")
def islands():
    d = current_app.config["DATA"]
    return jsonify({"ok": True, "islands": sorted(d["islands"].index.tolist())})


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
    weights = body.get("weights", APP_DEFAULTS["weights"])
    lpsp_target = float(body.get("lpsp_target", APP_DEFAULTS["reliability_target_lpsp"]))

    current_app.logger.info(f"OPTIMIZE START: {island} | Target Load: {load_kW} kW | LPSP Target: {lpsp_target}")
    start_time = time.time()

    try:
        result = optimize(island, load_kW, dfs, weights, lpsp_target=lpsp_target)
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

    return jsonify({"ok": True, "result": result})