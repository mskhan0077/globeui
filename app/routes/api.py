"""JSON API endpoints."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from app.engine.config_eval import evaluate
from app.engine.optimizer import optimize
from app.config import APP_DEFAULTS

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

    return jsonify({"ok": True, "result": result})


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

    try:
        result = optimize(island, load_kW, dfs, weights, lpsp_target=lpsp_target)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

    return jsonify({"ok": True, "result": result})