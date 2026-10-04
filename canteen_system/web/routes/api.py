"""
canteen_system/web/routes/api.py
----------------------------------
JSON API endpoints for Chart.js analytics.

Routes:
    GET /api/analytics/rolling-avg   — 7-day rolling average (AnalyticsService)
    GET /api/analytics/peak-hour     — Peak-hour demand (AnalyticsService)

These endpoints are called by JavaScript fetch() from the analytics page.
All management routes require an authenticated management session.
"""

from __future__ import annotations

from functools import wraps

from flask import Blueprint, jsonify, session, redirect, url_for

from canteen_system.web.db_setup import request_db
from canteen_system.web.utils import build_services, serialize_obj
from canteen_system.services.analytics_service import AnalyticsService

api_bp = Blueprint("api", __name__, url_prefix="/api")


def management_required_api(f):
    """Return 401 JSON if no management session (for AJAX endpoints)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "manager_id" not in session:
            return jsonify({"error": "Unauthorised"}), 401
        return f(*args, **kwargs)
    return decorated


@api_bp.route("/analytics/rolling-avg")
@management_required_api
def rolling_avg():
    """
    Return the 7-day rolling average wastage forecast as JSON.
    Calls AnalyticsService.get_rolling_7day_wastage_forecast().
    Response shape: list of {item_id, name, menu_date, quantity_sold, avg_sold, risk}
    """
    try:
        with request_db() as db:
            svc = build_services(db)
            records = svc.analytics.get_rolling_7day_wastage_forecast()

        data = []
        for r in records:
            risk = AnalyticsService.wastage_risk_label(r)
            row = serialize_obj(r)
            row["risk"] = risk
            data.append(row)

        return jsonify(data)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@api_bp.route("/analytics/peak-hour")
@management_required_api
def peak_hour():
    """
    Return today's peak-hour demand as JSON.
    Calls AnalyticsService.get_peak_hour_demand().
    Response shape: list of {hour_of_day, total_orders, total_items}
    """
    try:
        with request_db() as db:
            svc = build_services(db)
            records = svc.analytics.get_peak_hour_demand()

        return jsonify(serialize_obj(records))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@api_bp.route("/inventory/stock")
@management_required_api
def inventory_stock():
    """Return current inventory as JSON for optional live-reload use."""
    try:
        with request_db() as db:
            svc = build_services(db)
            stock = svc.inventory.get_all_stock()

        data = []
        for ingredient in stock:
            data.append({
                "ingredient_id": ingredient.ingredient_id,
                "ingredient_name": ingredient.ingredient_name,
                "current_stock": float(ingredient.current_stock),
                "reorder_threshold": float(ingredient.reorder_threshold),
                "is_low_stock": ingredient.is_low_stock,
            })
        return jsonify(data)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
