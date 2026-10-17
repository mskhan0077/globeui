"""Serves the globe UI (the repo's frontend/ folder) at the site root."""
from flask import Blueprint, current_app, send_from_directory

bp = Blueprint("frontend", __name__)


@bp.get("/")
def index():
    return send_from_directory(current_app.config["FRONTEND_DIR"], "index.html")


@bp.get("/<path:path>")
def files(path):
    # Only reached when no other route (/api, /export, /planner, /static …) matches.
    return send_from_directory(current_app.config["FRONTEND_DIR"], path)
