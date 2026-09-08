"""
repositories/menu_repo.py
--------------------------
Data Access Layer — MenuItems, DailyMenu, and MenuIngredients tables.

All methods execute raw parameterised SQL via the DatabaseManager.
No business logic lives here.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from canteen_system.config.database import DatabaseManager
from canteen_system.models.inventory import (
    DailyMenuItem,
    MenuItem,
    MenuIngredient,
)


class MenuRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # MenuItems
    # ------------------------------------------------------------------

    def get_all_items(self) -> list[MenuItem]:
        """Return all configured menu items."""
        rows = self._db.execute_query("SELECT ItemID, Name, Category, CostPrice FROM MenuItems")
        return [MenuItem.from_row(r) for r in (rows or [])]

    # ------------------------------------------------------------------
    # DailyMenu
    # ------------------------------------------------------------------

    def get_today_available_items(self, menu_date: date) -> list[DailyMenuItem]:
        """
        Return menu items that are prepared and still have stock for *menu_date*.
        """
        rows = self._db.execute_query(
            """
            SELECT m.ItemID, m.Name, m.Category, m.CostPrice,
                   dm.QuantityPrepared, dm.QuantitySold
            FROM MenuItems m
            JOIN DailyMenu dm ON m.ItemID = dm.ItemID
            WHERE dm.MenuDate = %s AND dm.QuantityPrepared > dm.QuantitySold
            """,
            (menu_date,),
        )
        return [DailyMenuItem.from_row(r) for r in (rows or [])]

    def get_daily_summary(self, menu_date: date) -> list[dict]:
        """Return raw rows from DailyMenu for a given date (used for EOD wastage)."""
        return self._db.execute_query(
            "SELECT ItemID, QuantityPrepared, QuantitySold FROM DailyMenu WHERE MenuDate = %s",
            (menu_date,),
        ) or []

    def get_daily_item_for_update(self, cursor, menu_date: date, item_id: int) -> Optional[dict]:
        """
        Lock the DailyMenu row for transactional update.
        Must be called within an active db.transaction() cursor.
        """
        cursor.execute(
            "SELECT QuantityPrepared, QuantitySold FROM DailyMenu "
            "WHERE MenuDate = %s AND ItemID = %s FOR UPDATE",
            (menu_date, item_id),
        )
        return cursor.fetchone()

    def upsert_daily_menu(self, menu_date: date, item_id: int, quantity: int) -> None:
        """
        Insert or increment today's DailyMenu quantity for an item.
        Uses ON DUPLICATE KEY UPDATE to handle re-entries.
        """
        self._db.execute_query(
            """
            INSERT INTO DailyMenu (MenuDate, ItemID, QuantityPrepared)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE QuantityPrepared = QuantityPrepared + %s
            """,
            (menu_date, item_id, quantity, quantity),
            commit=True,
        )

    def increment_quantity_sold(self, cursor, menu_date: date, item_id: int, quantity: int) -> None:
        """
        Increment the QuantitySold counter atomically.
        Must be called within an active db.transaction() cursor.
        """
        cursor.execute(
            "UPDATE DailyMenu SET QuantitySold = QuantitySold + %s "
            "WHERE MenuDate = %s AND ItemID = %s",
            (quantity, menu_date, item_id),
        )

    # ------------------------------------------------------------------
    # MenuIngredients
    # ------------------------------------------------------------------

    def get_ingredients_for_item(self, item_id: int) -> list[MenuIngredient]:
        """Return all ingredient requirements for a given menu item."""
        rows = self._db.execute_query(
            "SELECT IngredientID, QuantityRequired FROM MenuIngredients WHERE ItemID = %s",
            (item_id,),
        )
        return [MenuIngredient.from_row(r) for r in (rows or [])]

    def get_ingredients_for_item_in_tx(self, cursor, item_id: int) -> list[dict]:
        """
        Fetch ingredient requirements inside an active transaction cursor.
        Returns raw row dicts for use in the order transaction block.
        """
        cursor.execute(
            "SELECT IngredientID, QuantityRequired FROM MenuIngredients WHERE ItemID = %s",
            (item_id,),
        )
        return cursor.fetchall()
