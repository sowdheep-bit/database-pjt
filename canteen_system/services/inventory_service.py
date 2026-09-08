"""
services/inventory_service.py
------------------------------
Business logic for inventory management in the Canteen System.

Responsibilities:
  - Retrieve current stock levels and recent alerts for display
  - Replenish stock with basic input validation
  - End-of-day wastage logging (idempotent — skips already-logged items)
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from canteen_system.models.inventory import AlertRecord, Ingredient
from canteen_system.repositories.inventory_repo import InventoryRepository
from canteen_system.repositories.menu_repo import MenuRepository
from canteen_system.repositories.order_repo import OrderRepository


class InventoryService:
    def __init__(
        self,
        inventory_repo: InventoryRepository,
        menu_repo: MenuRepository,
        order_repo: OrderRepository,
    ) -> None:
        self._inv_repo = inventory_repo
        self._menu_repo = menu_repo
        self._order_repo = order_repo

    def get_all_stock(self) -> list[Ingredient]:
        """Return the full inventory list."""
        return self._inv_repo.get_all()

    def get_recent_alerts(self, limit: int = 20) -> list[AlertRecord]:
        """Return the most recent low-stock alert records."""
        return self._inv_repo.get_recent_alerts(limit)

    def replenish_stock(self, ingredient_id: int, amount: Decimal) -> None:
        """
        Add *amount* to the current stock of *ingredient_id*.
        Validates that amount is positive.
        Raises ValueError on invalid input.
        """
        if amount <= 0:
            raise ValueError("Amount to replenish must be greater than 0.")
        if ingredient_id <= 0:
            raise ValueError("Invalid ingredient ID.")
        self._inv_repo.replenish_stock(ingredient_id, amount)

    def log_eod_wastage(self) -> int:
        """
        Log end-of-day wastage for today's menu items.
        Skips items that have already been logged (idempotent).
        Returns the count of newly logged wastage records.
        """
        today = date.today()
        daily_summary = self._menu_repo.get_daily_summary(today)

        logged_count = 0
        for item in daily_summary:
            wasted = item["QuantityPrepared"] - item["QuantitySold"]
            if wasted > 0 and not self._order_repo.wastage_already_logged(today, item["ItemID"]):
                self._order_repo.log_wastage(today, item["ItemID"], wasted)
                logged_count += 1

        return logged_count
