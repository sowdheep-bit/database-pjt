"""
services/order_service.py
--------------------------
ACID-safe order placement for the Canteen System.

This service owns the entire transactional order lifecycle:
  1. Lock and validate DailyMenu availability
  2. Lock, validate, and deduct each ingredient from Inventory
  3. Increment DailyMenu.QuantitySold
  4. Insert the Order record

All four steps execute inside a single db.transaction() block, so any
failure causes a full rollback — no partial state is ever persisted.
"""

from __future__ import annotations

from datetime import date

from canteen_system.config.database import DatabaseManager
from canteen_system.repositories.inventory_repo import InventoryRepository
from canteen_system.repositories.menu_repo import MenuRepository
from canteen_system.repositories.order_repo import OrderRepository


class OrderService:
    def __init__(
        self,
        db: DatabaseManager,
        menu_repo: MenuRepository,
        inventory_repo: InventoryRepository,
        order_repo: OrderRepository,
    ) -> None:
        self._db = db
        self._menu_repo = menu_repo
        self._inventory_repo = inventory_repo
        self._order_repo = order_repo

    def place_order(self, customer_id: int, item_id: int, quantity: int) -> str:
        """
        Atomically place an order for *quantity* units of *item_id*.

        Returns a human-readable result message (success or failure reason).
        The caller (UI layer) is responsible for displaying it.
        """
        if quantity <= 0:
            return "Quantity must be greater than 0."

        today = date.today()

        try:
            with self._db.transaction() as cur:
                # ── Step 1: Lock & validate DailyMenu row ────────────────────
                daily_item = self._menu_repo.get_daily_item_for_update(cur, today, item_id)
                if not daily_item:
                    raise ValueError("Item is not on today's menu.")

                available = daily_item["QuantityPrepared"] - daily_item["QuantitySold"]
                if quantity > available:
                    raise ValueError(
                        f"Only {available} portion(s) available; you requested {quantity}."
                    )

                # ── Step 2: Lock, validate & deduct each ingredient ───────────
                ingredients = self._menu_repo.get_ingredients_for_item_in_tx(cur, item_id)
                for ing in ingredients:
                    required = ing["QuantityRequired"] * quantity
                    inv_row = self._inventory_repo.get_by_id_for_update(cur, ing["IngredientID"])

                    if not inv_row:
                        raise ValueError(
                            f"Ingredient ID {ing['IngredientID']} not found in inventory."
                        )
                    if inv_row["CurrentStockQuantity"] < required:
                        raise ValueError(
                            f"Insufficient stock for '{inv_row['IngredientName']}'. "
                            f"Required: {required}, Available: {inv_row['CurrentStockQuantity']}."
                        )
                    self._inventory_repo.deduct_stock(cur, ing["IngredientID"], required)

                # ── Step 3: Increment quantity sold ───────────────────────────
                self._menu_repo.increment_quantity_sold(cur, today, item_id, quantity)

                # ── Step 4: Record the order ───────────────────────────────────
                self._order_repo.create_order_in_tx(cur, customer_id, item_id, quantity)

            return "Order placed successfully! Ingredients deducted and sales updated."

        except ValueError as exc:
            # Business-rule violation — already rolled back by context manager
            return f"Order rejected: {exc}"
        except Exception as exc:
            # Unexpected DB or system error — already rolled back
            return f"Transaction failed and was rolled back. Error: {exc}"
