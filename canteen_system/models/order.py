"""
models/order.py
---------------
Data models for Orders and Wastage.
Pure dataclasses — no business logic, no database access.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Order:
    order_id: int
    customer_id: int
    item_id: int
    quantity_ordered: int
    order_timestamp: datetime

    @classmethod
    def from_row(cls, row: dict) -> "Order":
        return cls(
            order_id=row["OrderID"],
            customer_id=row["CustomerID"],
            item_id=row["ItemID"],
            quantity_ordered=row["QuantityOrdered"],
            order_timestamp=row["OrderTimestamp"],
        )


@dataclass
class WastageRecord:
    log_id: int
    log_date: datetime
    item_id: int
    quantity_wasted: int

    @classmethod
    def from_row(cls, row: dict) -> "WastageRecord":
        return cls(
            log_id=row["LogID"],
            log_date=row["LogDate"],
            item_id=row["ItemID"],
            quantity_wasted=row["QuantityWasted"],
        )


@dataclass
class PeakHourRecord:
    hour_of_day: int
    total_orders: int
    total_items: int

    @classmethod
    def from_row(cls, row: dict) -> "PeakHourRecord":
        return cls(
            hour_of_day=int(row["HourOfDay"]),
            total_orders=int(row["TotalOrders"] or 0),
            total_items=int(row["TotalItems"] or 0),
        )


@dataclass
class RollingAverageRecord:
    item_id: int
    name: str
    menu_date: datetime
    quantity_sold: int
    avg_sold: float

    @classmethod
    def from_row(cls, row: dict) -> "RollingAverageRecord":
        return cls(
            item_id=row["ItemID"],
            name=row["Name"],
            menu_date=row["MenuDate"],
            quantity_sold=int(row["QuantitySold"] or 0),
            avg_sold=float(row["AvgSold"] or 0.0),
        )
