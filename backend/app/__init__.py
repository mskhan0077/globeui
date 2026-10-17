from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from .data_loader import load_all

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = REPO_ROOT / "data" / "processed"
FRONTEND_DIR = REPO_ROOT / "frontend"

def create_app(test_config: dict | None = None) -> Flask:
    load_dotenv()
    app = Flask(__name__, template_folder="templates", static_folder="static")

    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-only-change-me"),
        DATA_DIR=Path(os.getenv("BLUEGRID_DATA", DEFAULT_DATA_DIR)),
        FRONTEND_DIR=FRONTEND_DIR,
        JSON_SORT_KEYS=False,
    )

    app.config["DATA"] = load_all(app.config["DATA_DIR"])
    app.config["CACHE"] = {}

    if test_config:
        app.config.update(test_config)

    from .routes.main import bp as main_bp
    from .routes.api import bp as api_bp
    from .routes.export import bp as export_bp
    from .routes.frontend import bp as frontend_bp

    app.register_blueprint(frontend_bp)  # globe UI at /
    app.register_blueprint(main_bp)      # classic planner at /planner
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(export_bp, url_prefix="/export")

    return app