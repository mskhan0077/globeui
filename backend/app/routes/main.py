from flask import Blueprint, current_app, render_template, request
from app.config import APP_DEFAULTS
from app.references import numbered

bp = Blueprint("main", __name__)

@bp.get("/planner")
def index():
    """Planner page. ?island=<name> preselects an island; ?embed=1 renders it
    without the header and with a transparent background, for the globe overlay."""
    table = current_app.config["DATA"]["islands"]
    islands = sorted(table.index.tolist())
    places = {name: [float(r.lat_deg_N), float(r.lon_deg_E)] for name, r in table.iterrows()}
    selected = request.args.get("island", "Kadmat")
    if selected not in islands:
        selected = "Kadmat"
    return render_template(
        "index.html",
        islands=islands,
        places=places,
        selected=selected,
        defaults=APP_DEFAULTS,
        embed=request.args.get("embed") == "1",
    )


@bp.get("/about")
def about():
    return render_template("about.html")


@bp.get("/references")
def references():
    return render_template("references.html", references=numbered())
