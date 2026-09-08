"""
models/inventory.py
-------------------
Data models for Inventory ingredients and alert records.
Pure dataclasses — no business logic, no database access.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class Ingredient:
    ingredient_id: int
    ingredient_name: str
    current_stock: Decimal
    reorder_threshold: Decimal

    @classmethod
    def from_row(cls, row: dict) -> "Ingredient":
        return cls(
            ingredient_id=row["IngredientID"],
            ingredient_name=row["IngredientName"],
            current_stock=row["CurrentStockQuantity"],
            reorder_threshold=row["ReorderThreshold"],
        )

    @property
    def is_low_stock(self) -> bool:
        return self.current_stock <= self.reorder_threshold


@dataclass
class AlertRecord:
    alert_id: int
    alert_timestamp: datetime
    alert_type: str
    ingredient_name: str
    current_stock: Decimal
    reorder_threshold: Decimal

    @classmethod
    def from_row(cls, row: dict) -> "AlertRecord":
        return cls(
            alert_id=row["AlertID"],
            alert_timestamp=row["AlertTimestamp"],
            alert_type=row["AlertType"],
            ingredient_name=row["IngredientName"],
            current_stock=row["CurrentStockQuantity"],
            reorder_threshold=row["ReorderThreshold"],
        )


@dataclass
class MenuItem:
    item_id: int
    name: str
    category: str
    cost_price: Decimal

    @classmethod
    def from_row(cls, row: dict) -> "MenuItem":
        return cls(
            item_id=row["ItemID"],
            name=row["Name"],
            category=row.get("Category", ""),
            cost_price=row["CostPrice"],
        )


@dataclass
class DailyMenuItem:
    """A menu item enriched with today's availability data."""
    item_id: int
    name: str
    category: str
    cost_price: Decimal
    quantity_prepared: int
    quantity_sold: int

    @property
    def available(self) -> int:
        return self.quantity_prepared - self.quantity_sold

    @classmethod
    def from_row(cls, row: dict) -> "DailyMenuItem":
        return cls(
            item_id=row["ItemID"],
            name=row["Name"],
            category=row.get("Category", ""),
            cost_price=row["CostPrice"],
            quantity_prepared=row["QuantityPrepared"],
            quantity_sold=row["QuantitySold"],
        )


@dataclass
class MenuIngredient:
    """The quantity of a specific ingredient required per menu item."""
    ingredient_id: int
    quantity_required: Decimal

    @classmethod
    def from_row(cls, row: dict) -> "MenuIngredient":
        return cls(
            ingredient_id=row["IngredientID"],
            quantity_required=row["QuantityRequired"],
        )
