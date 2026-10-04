"""
canteen_system/web/routes/management.py
-----------------------------------------
Management-facing web routes for the Canteen Management System.

Routes:
    GET/POST  /management/login          — Manager authentication (AuthService.login)
    GET       /management/logout         — Clear management session
    GET       /management/dashboard      — KPI overview
    GET/POST  /management/morning-setup  — Daily quantities (MenuService.set_daily_quantity)
    GET       /management/inventory      — Stock + alerts
    POST      /management/inventory/replenish — Replenish stock (InventoryService.replenish_stock)
    POST      /management/wastage        — EOD wastage (InventoryService.log_eod_wastage)
    GET       /management/analytics      — Analytics page (Chart.js)

Session keys used:
    manager_id    (int)
    manager_name  (str)
    manager_level (str)

Security:
    management_required decorator rejects unauthenticated access.
    Manager ID is never taken from the browser — always from session.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from functools import wraps

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from canteen_system.web.db_setup import request_db
from canteen_system.web.utils import build_services

management_bp = Blueprint("management", __name__, url_prefix="/management")


# ---------------------------------------------------------------------------
# Auth guard decorator
# ---------------------------------------------------------------------------

def management_required(f):
    """Redirect to management login if no authenticated manager session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "manager_id" not in session:
            flash("Please log in to access management.", "warning")
            return redirect(url_for("management.login"))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------------------------

@management_bp.route("/login", methods=["GET", "POST"])
def login():
    if "manager_id" in session:
        return redirect(url_for("management.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password are required.", "error")
            return render_template("management/login.html")

        try:
            with request_db() as db:
                svc = build_services(db)
                manager = svc.auth.login(username, password)

            if manager:
                session["manager_id"] = manager.manager_id
                session["manager_name"] = manager.full_name
                session["manager_level"] = manager.access_level
                flash(f"Welcome, {manager.full_name}!", "success")
                return redirect(url_for("management.dashboard"))
            else:
                flash("Invalid username or password.", "error")
        except Exception as exc:
            flash(f"Login error: {exc}", "error")

    return render_template("management/login.html")


@management_bp.route("/logout")
def logout():
    session.pop("manager_id", None)
    session.pop("manager_name", None)
    session.pop("manager_level", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("management.login"))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@management_bp.route("/dashboard")
@management_required
def dashboard():
    """KPI overview: today's menu status, stock alerts, recent orders count."""
    try:
        with request_db() as db:
            svc = build_services(db)

            today_menu = svc.menu.get_today_menu()
            alerts = svc.inventory.get_recent_alerts(limit=5)
            all_stock = svc.inventory.get_all_stock()

            # Quick stats from DB
            orders_today = db.execute_query(
                "SELECT COUNT(*) AS cnt FROM Orders WHERE DATE(OrderTimestamp) = CURDATE()"
            )
            orders_count = orders_today[0]["cnt"] if orders_today else 0

            revenue_today = db.execute_query(
                """
                SELECT COALESCE(SUM(m.CostPrice * o.QuantityOrdered), 0) AS total
                FROM Orders o
                JOIN MenuItems m ON o.ItemID = m.ItemID
                WHERE DATE(o.OrderTimestamp) = CURDATE()
                """
            )
            revenue = float(revenue_today[0]["total"]) if revenue_today else 0.0

        low_stock_count = sum(1 for i in all_stock if i.is_low_stock)

        return render_template(
            "management/dashboard.html",
            today_menu=today_menu,
            alerts=alerts,
            orders_count=orders_count,
            revenue=revenue,
            low_stock_count=low_stock_count,
            menu_item_count=len(today_menu),
        )
    except Exception as exc:
        flash(f"Dashboard error: {exc}", "error")
        return render_template(
            "management/dashboard.html",
            today_menu=[],
            alerts=[],
            orders_count=0,
            revenue=0.0,
            low_stock_count=0,
            menu_item_count=0,
        )


# ---------------------------------------------------------------------------
# Morning Setup
# ---------------------------------------------------------------------------

@management_bp.route("/morning-setup", methods=["GET", "POST"])
@management_required
def morning_setup():
    """
    GET:  Display all menu items with a form to set today's quantities.
    POST: Call MenuService.set_daily_quantity() for each submitted item.
    """
    if request.method == "POST":
        item_id_str = request.form.get("item_id", "").strip()
        quantity_str = request.form.get("quantity", "").strip()

        if not item_id_str.isdigit() or not quantity_str.isdigit():
            flash("Invalid item ID or quantity.", "error")
            return redirect(url_for("management.morning_setup"))

        item_id = int(item_id_str)
        quantity = int(quantity_str)

        try:
            with request_db() as db:
                svc = build_services(db)
                svc.menu.set_daily_quantity(item_id, quantity)
            flash(f"Quantity updated for item {item_id}.", "success")
        except ValueError as exc:
            flash(str(exc), "error")
        except Exception as exc:
            flash(f"Could not update menu: {exc}", "error")

        return redirect(url_for("management.morning_setup"))

    # GET — load items and today's current quantities
    try:
        with request_db() as db:
            svc = build_services(db)
            all_items = svc.menu.get_all_menu_items()
            today_menu = svc.menu.get_today_menu()

        today_set = {item.item_id: item for item in today_menu}
        return render_template(
            "management/morning_setup.html",
            all_items=all_items,
            today_set=today_set,
        )
    except Exception as exc:
        flash(f"Could not load menu items: {exc}", "error")
        return render_template(
            "management/morning_setup.html",
            all_items=[],
            today_set={},
        )


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

@management_bp.route("/inventory")
@management_required
def inventory():
    """Display current stock levels and recent low-stock alerts."""
    try:
        with request_db() as db:
            svc = build_services(db)
            stock = svc.inventory.get_all_stock()
            alerts = svc.inventory.get_recent_alerts(limit=20)
        return render_template(
            "management/inventory.html",
            stock=stock,
            alerts=alerts,
        )
    except Exception as exc:
        flash(f"Could not load inventory: {exc}", "error")
        return render_template("management/inventory.html", stock=[], alerts=[])


@management_bp.route("/inventory/replenish", methods=["POST"])
@management_required
def replenish():
    """Replenish an ingredient's stock via InventoryService.replenish_stock()."""
    ingredient_id_str = request.form.get("ingredient_id", "").strip()
    amount_str = request.form.get("amount", "").strip()

    if not ingredient_id_str.isdigit():
        flash("Invalid ingredient ID.", "error")
        return redirect(url_for("management.inventory"))

    try:
        amount = Decimal(amount_str)
    except (InvalidOperation, ValueError):
        flash("Amount must be a valid positive number.", "error")
        return redirect(url_for("management.inventory"))

    try:
        with request_db() as db:
            svc = build_services(db)
            svc.inventory.replenish_stock(int(ingredient_id_str), amount)
        flash(f"Stock replenished by {amount} units.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    except Exception as exc:
        flash(f"Replenishment failed: {exc}", "error")

    return redirect(url_for("management.inventory"))


# ---------------------------------------------------------------------------
# End-of-Day Wastage
# ---------------------------------------------------------------------------

@management_bp.route("/wastage", methods=["POST"])
@management_required
def log_wastage():
    """Trigger end-of-day wastage logging via InventoryService.log_eod_wastage()."""
    try:
        with request_db() as db:
            svc = build_services(db)
            count = svc.inventory.log_eod_wastage()
        if count == 0:
            flash("No wastage to log today (either nothing was prepared or already logged).", "info")
        else:
            flash(f"Wastage logged for {count} item(s) today.", "success")
    except Exception as exc:
        flash(f"Wastage logging failed: {exc}", "error")

    return redirect(url_for("management.dashboard"))


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

@management_bp.route("/analytics")
@management_required
def analytics():
    """
    Analytics page with Chart.js charts.
    Data is fetched via the /api/analytics/* endpoints using JavaScript fetch().
    This route just renders the page shell with the charts.
    """
    return render_template("management/analytics.html")
