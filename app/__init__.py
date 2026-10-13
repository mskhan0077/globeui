from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from .data_loader import load_all

def create_app(test_config: dict | None = None) -> Flask:
    load_dotenv()
    app = Flask(__name__, template_folder="templates", static_folder="static")

    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-only-change-me"),
        DATA_DIR=Path(os.getenv("BLUEGRID_DATA", "Data/processed")),
        JSON_SORT_KEYS=False,
    )

    app.config["DATA"] = load_all(app.config["DATA_DIR"])
    app.config["CACHE"] = {}

    if test_config:
        app.config.update(test_config)

    from .routes.main import bp as main_bp
    from .routes.api import bp as api_bp
    from .routes.export import bp as export_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(export_bp, url_prefix="/export")

    return app