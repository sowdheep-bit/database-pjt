"""
canteen_system/web/app.py
--------------------------
Flask application factory for the Canteen Management System web interface.

Architecture:
  Browser → Flask (this file) → Existing Services → Existing Repositories → MySQL

The Flask layer is strictly a presentation/routing layer.
All business logic lives in the existing service layer.
All database access goes through the existing repository layer.
No SQL is written here.

Startup:
    python run_web.py          (from project root)
  or
    flask --app canteen_system.web.app run

Environment variables (see .env.example):
    DB_HOST, DB_USER, DB_PASSWORD, DB_PORT, DB_NAME
    FLASK_SECRET_KEY
"""

from __future__ import annotations

import os
import sys

# Ensure project root is on sys.path when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from decimal import Decimal
from functools import wraps

from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from canteen_system.web.db_setup import init_db_pool, request_db
from canteen_system.web.utils import build_services, serialize_obj
from canteen_system.services.analytics_service import AnalyticsService

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> Flask:
    """Create and configure the Flask application."""
    load_dotenv()

    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-insecure-change-me")

    # Initialise the DB pool once at startup (reads from env vars)
    try:
        init_db_pool()
    except Exception as exc:
        print(f"[FATAL] Cannot initialise database pool: {exc}", file=sys.stderr)
        print("[FATAL] Set DB_HOST, DB_USER, DB_PASSWORD in .env and retry.", file=sys.stderr)
        raise

    # Register blueprints
    from canteen_system.web.routes.customer import customer_bp
    from canteen_system.web.routes.management import management_bp
    from canteen_system.web.routes.api import api_bp

    app.register_blueprint(customer_bp)
    app.register_blueprint(management_bp)
    app.register_blueprint(api_bp)

    # ---------------------------------------------------------------------------
    # Root route — landing page
    # ---------------------------------------------------------------------------

    @app.route("/")
    def index():
        return render_template("index.html")

    # ---------------------------------------------------------------------------
    # Generic error handlers
    # ---------------------------------------------------------------------------

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    return app
