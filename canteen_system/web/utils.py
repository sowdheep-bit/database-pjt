"""
canteen_system/web/utils.py
----------------------------
Serialisation helpers and shared utilities for the Flask web layer.

Responsibilities:
  - Convert Decimal → float for JSON responses (MySQL returns Decimal objects)
  - Convert datetime / date → ISO string for JSON responses
  - Build wired service objects from a per-request DatabaseManager

These helpers keep the conversion logic in one place so routes stay clean.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from canteen_system.repositories.customer_repo import CustomerRepository
from canteen_system.repositories.inventory_repo import InventoryRepository
from canteen_system.repositories.menu_repo import MenuRepository
from canteen_system.repositories.order_repo import OrderRepository
from canteen_system.services.analytics_service import AnalyticsService
from canteen_system.services.auth_service import AuthService
from canteen_system.services.inventory_service import InventoryService
from canteen_system.services.menu_service import MenuService
from canteen_system.services.order_service import OrderService


# ---------------------------------------------------------------------------
# JSON serialisation helpers
# ---------------------------------------------------------------------------

def serialize_value(value: Any) -> Any:
    """Convert a single value to a JSON-compatible type."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def serialize_obj(obj: Any) -> Any:
    """
    Recursively convert an object or dataclass to a JSON-serialisable dict.
    Handles:
      - Plain dicts (from raw DB rows)
      - Dataclass instances (convert via __dict__)
      - Lists / tuples (recurse into each element)
      - Scalar types (Decimal, datetime, date → JSON-safe)
    """
    if isinstance(obj, dict):
        return {k: serialize_obj(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [serialize_obj(item) for item in obj]
    if hasattr(obj, "__dataclass_fields__"):
        return {k: serialize_obj(v) for k, v in obj.__dict__.items()}
    return serialize_value(obj)


# ---------------------------------------------------------------------------
# Dependency wiring
# ---------------------------------------------------------------------------

def build_services(db):
    """
    Wire all repositories and services for a given DatabaseManager instance.
    Returns a named tuple-like namespace with all service objects.
    Called once per request with the per-request WebDatabaseManager.
    """
    customer_repo  = CustomerRepository(db)
    inventory_repo = InventoryRepository(db)
    menu_repo      = MenuRepository(db)
    order_repo     = OrderRepository(db)

    auth_svc      = AuthService(db)
    menu_svc      = MenuService(menu_repo)
    order_svc     = OrderService(db, menu_repo, inventory_repo, order_repo)
    inv_svc       = InventoryService(inventory_repo, menu_repo, order_repo)
    analytics_svc = AnalyticsService(order_repo)

    class Services:
        pass

    svc = Services()
    svc.customer_repo  = customer_repo
    svc.auth           = auth_svc
    svc.menu           = menu_svc
    svc.order          = order_svc
    svc.inventory      = inv_svc
    svc.analytics      = analytics_svc
    return svc
