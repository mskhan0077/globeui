from flask import Blueprint, current_app, render_template
from app.config import APP_DEFAULTS

bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    islands = sorted(current_app.config["DATA"]["islands"].index.tolist())
    return render_template("index.html", islands=islands, defaults=APP_DEFAULTS)


@bp.get("/about")
def about():
    return render_template("about.html")