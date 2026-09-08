"""
services/analytics_service.py
-------------------------------
Analytical queries and predictive insights for the Canteen System.

Responsibilities:
  - 7-day rolling average wastage (window function over DailyMenu history)
  - Peak-hour demand reporting (orders bucketed by hour of day)
"""

from __future__ import annotations

from datetime import date

from canteen_system.models.order import PeakHourRecord, RollingAverageRecord
from canteen_system.repositories.order_repo import OrderRepository


class AnalyticsService:
    def __init__(self, order_repo: OrderRepository) -> None:
        self._order_repo = order_repo

    def get_rolling_7day_wastage_forecast(
        self, for_date: date | None = None
    ) -> list[RollingAverageRecord]:
        """
        Return today's items enriched with their 7-day rolling sales average.
        A high delta between today's sold quantity and the rolling average
        signals potential over-preparation (wastage risk).

        *for_date* defaults to today if not supplied.
        """
        target = for_date or date.today()
        return self._order_repo.get_rolling_7day_avg(target)

    def get_peak_hour_demand(self, for_date: date | None = None) -> list[PeakHourRecord]:
        """
        Return per-hour order statistics for *for_date*, sorted by busiest hour first.
        *for_date* defaults to today if not supplied.
        """
        target = for_date or date.today()
        return self._order_repo.get_peak_hour_demand(target)

    @staticmethod
    def wastage_risk_label(record: RollingAverageRecord) -> str:
        """
        Classify a rolling-average record as 'High' or 'Normal' risk.
        'High' means today's actual sales are more than 20% above the 7-day average,
        suggesting the item was over-prepared relative to historical demand.
        """
        if record.avg_sold > 0 and record.quantity_sold < record.avg_sold * 0.8:
            return "High"
        return "Normal"
