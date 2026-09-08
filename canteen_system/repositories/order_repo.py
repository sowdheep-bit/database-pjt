"""
repositories/order_repo.py
---------------------------
Data Access Layer — Orders and WastageLog tables.

All methods execute raw parameterised SQL via the DatabaseManager.
No business logic lives here.
"""

from __future__ import annotations

from datetime import date

from canteen_system.config.database import DatabaseManager
from canteen_system.models.order import PeakHourRecord, RollingAverageRecord


class OrderRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def create_order_in_tx(
        self,
        cursor,
        customer_id: int,
        item_id: int,
        quantity: int,
    ) -> None:
        """
        Insert an order row inside an active transaction.
        Must be called within an active db.transaction() cursor.
        """
        cursor.execute(
            "INSERT INTO Orders (CustomerID, ItemID, QuantityOrdered) VALUES (%s, %s, %s)",
            (customer_id, item_id, quantity),
        )

    def get_peak_hour_demand(self, for_date: date) -> list[PeakHourRecord]:
        """Return per-hour order counts for a given date, sorted by busiest hour."""
        rows = self._db.execute_query(
            """
            SELECT
                HOUR(OrderTimestamp)  AS HourOfDay,
                COUNT(OrderID)        AS TotalOrders,
                SUM(QuantityOrdered)  AS TotalItems
            FROM Orders
            WHERE DATE(OrderTimestamp) = %s
            GROUP BY HOUR(OrderTimestamp)
            ORDER BY TotalOrders DESC
            """,
            (for_date,),
        )
        return [PeakHourRecord.from_row(r) for r in (rows or [])]

    # ------------------------------------------------------------------
    # Analytics — rolling average
    # ------------------------------------------------------------------

    def get_rolling_7day_avg(self, for_date: date) -> list[RollingAverageRecord]:
        """
        Return today's items enriched with their 7-day rolling sales average,
        using a window function over the DailyMenu history.
        """
        rows = self._db.execute_query(
            """
            WITH DailySales AS (
                SELECT ItemID, MenuDate, QuantitySold
                FROM DailyMenu
            ),
            RollingAverage AS (
                SELECT
                    ItemID,
                    MenuDate,
                    QuantitySold,
                    AVG(QuantitySold) OVER (
                        PARTITION BY ItemID
                        ORDER BY MenuDate
                        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                    ) AS Rolling7DayAvg
                FROM DailySales
            )
            SELECT r.ItemID, m.Name, r.MenuDate, r.QuantitySold,
                   ROUND(r.Rolling7DayAvg, 2) AS AvgSold
            FROM RollingAverage r
            JOIN MenuItems m ON r.ItemID = m.ItemID
            WHERE r.MenuDate = %s
            """,
            (for_date,),
        )
        return [RollingAverageRecord.from_row(r) for r in (rows or [])]

    # ------------------------------------------------------------------
    # WastageLog
    # ------------------------------------------------------------------

    def wastage_already_logged(self, log_date: date, item_id: int) -> bool:
        """Return True if a wastage entry already exists for this date + item."""
        rows = self._db.execute_query(
            "SELECT LogID FROM WastageLog WHERE LogDate = %s AND ItemID = %s",
            (log_date, item_id),
        )
        return bool(rows)

    def log_wastage(self, log_date: date, item_id: int, quantity_wasted: int) -> None:
        """Insert a wastage record."""
        self._db.execute_query(
            "INSERT INTO WastageLog (LogDate, ItemID, QuantityWasted) VALUES (%s, %s, %s)",
            (log_date, item_id, quantity_wasted),
            commit=True,
        )
