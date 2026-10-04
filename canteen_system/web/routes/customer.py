"""
canteen_system/web/routes/customer.py
---------------------------------------
Customer-facing web routes for the Canteen Management System.

Routes:
    GET/POST  /customer/login       — Customer ID lookup or new registration
    GET/POST  /customer/register    — Registration form (also redirects from login)
    GET       /customer/menu        — Today's menu
    POST      /customer/order       — Place an order (calls OrderService.place_order)
    GET       /customer/orders      — Order history for the logged-in customer
    GET       /customer/orders/<id> — Single order detail
    GET       /customer/logout      — Clear customer session

Session keys used:
    customer_id   (int)
    customer_name (str)

Security: No customer can view another customer's orders.
Business logic stays in services — no SQL in this file.
"""

from __future__ import annotations

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

customer_bp = Blueprint("customer", __name__, url_prefix="/customer")


# ---------------------------------------------------------------------------
# Auth guard decorator
# ---------------------------------------------------------------------------

def customer_required(f):
    """Redirect to customer login if not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "customer_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("customer.login"))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Login / Registration
# ---------------------------------------------------------------------------

@customer_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    GET:  Show the customer login / identification form.
    POST: Look up customer by ID. If found → set session. If not → redirect to register.
    """
    if "customer_id" in session:
        return redirect(url_for("customer.menu"))

    if request.method == "POST":
        customer_id_str = request.form.get("customer_id", "").strip()
        if not customer_id_str.isdigit():
            flash("Please enter a valid numeric Customer ID.", "error")
            return render_template("customer/login.html")

        customer_id = int(customer_id_str)
        with request_db() as db:
            svc = build_services(db)
            customer = svc.customer_repo.find_by_id(customer_id)

        if customer:
            session["customer_id"] = customer.customer_id
            session["customer_name"] = customer.full_name
            flash(f"Welcome back, {customer.full_name}!", "success")
            return redirect(url_for("customer.menu"))
        else:
            flash(f"No customer found with ID {customer_id}. Please register.", "info")
            return redirect(url_for("customer.register"))

    return render_template("customer/login.html")


@customer_bp.route("/register", methods=["GET", "POST"])
def register():
    """
    GET:  Show registration form.
    POST: Create a new customer and set session.
    """
    if "customer_id" in session:
        return redirect(url_for("customer.menu"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        customer_type = request.form.get("customer_type", "").strip()
        contact_number = request.form.get("contact_number", "").strip()

        # Input validation (CustomerType validation here since CLI had it in UI layer)
        if not full_name:
            flash("Full name is required.", "error")
            return render_template("customer/register.html")
        if customer_type not in ("Student", "Staff"):
            flash("Customer type must be Student or Staff.", "error")
            return render_template("customer/register.html")

        try:
            with request_db() as db:
                svc = build_services(db)
                customer = svc.customer_repo.create(full_name, customer_type, contact_number)

            session["customer_id"] = customer.customer_id
            session["customer_name"] = customer.full_name
            flash(
                f"Account created! Your Customer ID is {customer.customer_id}. "
                "Keep this number to log in again.",
                "success",
            )
            return redirect(url_for("customer.menu"))
        except Exception as exc:
            flash(f"Registration failed: {exc}", "error")
            return render_template("customer/register.html")

    return render_template("customer/register.html")


# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------

@customer_bp.route("/menu")
@customer_required
def menu():
    """Display today's available menu items."""
    try:
        with request_db() as db:
            svc = build_services(db)
            menu_items = svc.menu.get_today_menu()
        return render_template("customer/menu.html", menu_items=menu_items)
    except Exception as exc:
        flash(f"Could not load menu: {exc}", "error")
        return render_template("customer/menu.html", menu_items=[])


# ---------------------------------------------------------------------------
# Order placement
# ---------------------------------------------------------------------------

@customer_bp.route("/order", methods=["POST"])
@customer_required
def place_order():
    """
    Place an order for the logged-in customer.
    Calls OrderService.place_order() — ACID transaction with FOR UPDATE locks.
    """
    item_id_str = request.form.get("item_id", "").strip()
    quantity_str = request.form.get("quantity", "").strip()

    if not item_id_str.isdigit() or not quantity_str.isdigit():
        flash("Invalid order data.", "error")
        return redirect(url_for("customer.menu"))

    item_id = int(item_id_str)
    quantity = int(quantity_str)
    customer_id = session["customer_id"]

    try:
        with request_db() as db:
            svc = build_services(db)
            result_msg = svc.order.place_order(customer_id, item_id, quantity)

        if result_msg.startswith("Order placed"):
            flash(result_msg, "success")
        else:
            flash(result_msg, "error")
    except Exception as exc:
        flash(f"Order failed: {exc}", "error")

    return redirect(url_for("customer.orders"))


# ---------------------------------------------------------------------------
# Order history
# ---------------------------------------------------------------------------

@customer_bp.route("/orders")
@customer_required
def orders():
    """Show all orders for the current customer."""
    customer_id = session["customer_id"]
    try:
        with request_db() as db:
            # Query orders for this customer only
            rows = db.execute_query(
                """
                SELECT o.OrderID, o.QuantityOrdered, o.OrderTimestamp,
                       m.Name AS ItemName, m.CostPrice
                FROM Orders o
                JOIN MenuItems m ON o.ItemID = m.ItemID
                WHERE o.CustomerID = %s
                ORDER BY o.OrderTimestamp DESC
                """,
                (customer_id,),
            )
        return render_template("customer/orders.html", orders=rows or [])
    except Exception as exc:
        flash(f"Could not load orders: {exc}", "error")
        return render_template("customer/orders.html", orders=[])


@customer_bp.route("/orders/<int:order_id>")
@customer_required
def order_detail(order_id: int):
    """Show details of a single order — only if it belongs to this customer."""
    customer_id = session["customer_id"]
    try:
        with request_db() as db:
            rows = db.execute_query(
                """
                SELECT o.OrderID, o.QuantityOrdered, o.OrderTimestamp,
                       m.Name AS ItemName, m.CostPrice, m.Category
                FROM Orders o
                JOIN MenuItems m ON o.ItemID = m.ItemID
                WHERE o.OrderID = %s AND o.CustomerID = %s
                """,
                (order_id, customer_id),
            )
        if not rows:
            flash("Order not found or does not belong to your account.", "error")
            return redirect(url_for("customer.orders"))
        return render_template("customer/order_detail.html", order=rows[0])
    except Exception as exc:
        flash(f"Could not load order: {exc}", "error")
        return redirect(url_for("customer.orders"))


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

@customer_bp.route("/logout")
def logout():
    session.pop("customer_id", None)
    session.pop("customer_name", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))
