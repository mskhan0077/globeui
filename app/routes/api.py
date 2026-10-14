from flask import Blueprint, current_app, jsonify

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