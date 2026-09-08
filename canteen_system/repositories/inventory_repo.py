"""
repositories/inventory_repo.py
--------------------------------
Data Access Layer — Inventory and Alerts tables.

All methods execute raw parameterised SQL via the DatabaseManager.
No business logic lives here.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from canteen_system.config.database import DatabaseManager
from canteen_system.models.inventory import AlertRecord, Ingredient


class InventoryRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_all(self) -> list[Ingredient]:
        """Return all inventory rows."""
        rows = self._db.execute_query(
            "SELECT IngredientID, IngredientName, CurrentStockQuantity, ReorderThreshold FROM Inventory"
        )
        return [Ingredient.from_row(r) for r in (rows or [])]

    def get_recent_alerts(self, limit: int = 20) -> list[AlertRecord]:
        """Return the most recent low-stock alert records."""
        rows = self._db.execute_query(
            """
            SELECT a.AlertID, a.AlertTimestamp, a.AlertType,
                   i.IngredientName, i.CurrentStockQuantity, i.ReorderThreshold
            FROM Alerts a
            JOIN Inventory i ON a.IngredientID = i.IngredientID
            ORDER BY a.AlertTimestamp DESC
            LIMIT %s
            """,
            (limit,),
        )
        return [AlertRecord.from_row(r) for r in (rows or [])]

    def get_by_id_for_update(self, cursor, ingredient_id: int) -> Optional[dict]:
        """
        Lock and return the ingredient row for transactional update.
        Must be called within an active db.transaction() cursor.
        Returns the raw row dict (used inside transaction blocks).
        """
        cursor.execute(
            "SELECT CurrentStockQuantity, IngredientName FROM Inventory WHERE IngredientID = %s FOR UPDATE",
            (ingredient_id,),
        )
        return cursor.fetchone()

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def deduct_stock(self, cursor, ingredient_id: int, amount: Decimal) -> None:
        """
        Deduct *amount* from an ingredient's current stock.
        Must be called within an active db.transaction() cursor.
        """
        cursor.execute(
            "UPDATE Inventory SET CurrentStockQuantity = CurrentStockQuantity - %s WHERE IngredientID = %s",
            (amount, ingredient_id),
        )

    def replenish_stock(self, ingredient_id: int, amount: Decimal) -> None:
        """Add *amount* to an ingredient's current stock (non-transactional)."""
        self._db.execute_query(
            "UPDATE Inventory SET CurrentStockQuantity = CurrentStockQuantity + %s WHERE IngredientID = %s",
            (amount, ingredient_id),
            commit=True,
        )
