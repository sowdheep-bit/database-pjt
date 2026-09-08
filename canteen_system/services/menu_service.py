"""
services/menu_service.py
-------------------------
Business logic for menu management in the Canteen System.

Responsibilities:
  - Retrieve today's available menu for display
  - Handle morning setup (upsert prepared quantities into DailyMenu)
"""

from __future__ import annotations

from datetime import date

from canteen_system.models.inventory import DailyMenuItem, MenuItem
from canteen_system.repositories.menu_repo import MenuRepository


class MenuService:
    def __init__(self, menu_repo: MenuRepository) -> None:
        self._menu_repo = menu_repo

    def get_today_menu(self) -> list[DailyMenuItem]:
        """
        Return all DailyMenu items that are available today (prepared > sold).
        Returns an empty list if nothing is on the menu or everything is sold out.
        """
        return self._menu_repo.get_today_available_items(date.today())

    def get_all_menu_items(self) -> list[MenuItem]:
        """Return every configured menu item (used during morning setup)."""
        return self._menu_repo.get_all_items()

    def set_daily_quantity(self, item_id: int, quantity: int) -> None:
        """
        Record or add to the prepared quantity for *item_id* for today.
        Validates that quantity is positive before delegating to the repo.
        Raises ValueError on invalid input.
        """
        if quantity <= 0:
            raise ValueError("Quantity prepared must be greater than 0.")
        if item_id <= 0:
            raise ValueError("Invalid item ID.")
        self._menu_repo.upsert_daily_menu(date.today(), item_id, quantity)
