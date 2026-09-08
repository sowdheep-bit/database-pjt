"""
ui/management_cli.py
---------------------
Presentation layer for the management portal CLI.

Responsibilities:
  - Render all management sub-menus and collect input
  - Display inventory, alerts, analytics tables
  - Delegate all logic to the appropriate service layer

Zero SQL. Zero business logic. Only input(), print(), and service calls.
"""

from __future__ import annotations

from canteen_system.models.user import Manager
from canteen_system.services.analytics_service import AnalyticsService
from canteen_system.services.inventory_service import InventoryService
from canteen_system.services.menu_service import MenuService


class ManagementCLI:
    def __init__(
        self,
        menu_service: MenuService,
        inventory_service: InventoryService,
        analytics_service: AnalyticsService,
    ) -> None:
        self._menu_svc = menu_service
        self._inv_svc = inventory_service
        self._analytics_svc = analytics_service

    # ------------------------------------------------------------------
    # Morning Setup
    # ------------------------------------------------------------------

    def morning_setup(self) -> None:
        """Prompt the manager to set today's prepared quantities for menu items."""
        print("\n" + "-" * 50)
        print("  MORNING SETUP — Today's Menu")
        print("-" * 50)

        items = self._menu_svc.get_all_menu_items()
        if not items:
            print("  No menu items configured in the database.")
            return

        print(f"  {'ID':<5}  {'Item Name':<30}")
        print("  " + "-" * 36)
        for item in items:
            print(f"  {item.item_id:<5}  {item.name:<30}")

        try:
            item_id = int(input("\n  Enter Item ID to prepare (0 to cancel): ").strip())
            if item_id == 0:
                return
            quantity = int(input("  Enter Quantity Prepared: ").strip())
            self._menu_svc.set_daily_quantity(item_id, quantity)
            print("  [OK] Menu updated successfully.")
        except ValueError as exc:
            print(f"  Invalid input: {exc}")

    # ------------------------------------------------------------------
    # Inventory Monitoring
    # ------------------------------------------------------------------

    def inventory_monitoring(self) -> None:
        """Display low-stock alerts and current inventory; offer replenishment."""
        # -- Alerts -------------------------------------------------------
        print("\n" + "-" * 72)
        print(f"  {'LOW STOCK ALERTS':^68}")
        print("-" * 72)
        alerts = self._inv_svc.get_recent_alerts()
        if not alerts:
            print("  No recent alerts.")
        else:
            print(
                f"  {'Time':<20}  {'Ingredient':<20}  {'Current Stock':>13}  {'Threshold':>9}"
            )
            print("  " + "-" * 66)
            for a in alerts:
                print(
                    f"  {a.alert_timestamp.strftime('%Y-%m-%d %H:%M'):<20}"
                    f"  {a.ingredient_name:<20}"
                    f"  {a.current_stock:>13}"
                    f"  {a.reorder_threshold:>9}"
                )

        # -- Inventory ----------------------------------------------------
        print("\n" + "-" * 72)
        print(f"  {'CURRENT INVENTORY':^68}")
        print("-" * 72)
        stock = self._inv_svc.get_all_stock()
        if stock:
            print(f"  {'ID':<5}  {'Ingredient':<22}  {'Current Stock':>13}  {'Threshold':>9}  {'Status':<10}")
            print("  " + "-" * 64)
            for ing in stock:
                status = "[!] LOW" if ing.is_low_stock else "OK"
                print(
                    f"  {ing.ingredient_id:<5}  {ing.ingredient_name:<22}"
                    f"  {ing.current_stock:>13}"
                    f"  {ing.reorder_threshold:>9}"
                    f"  {status:<10}"
                )

        # -- Replenishment -------------------------------------------------
        print()
        add_stock = input("  Add stock? (y/n): ").strip().lower()
        if add_stock == "y":
            try:
                ing_id = int(input("  Ingredient ID    : ").strip())
                qty = float(input("  Quantity to add  : ").strip())
                self._inv_svc.replenish_stock(ing_id, qty)
                print("  [OK] Stock replenished.")
            except ValueError as exc:
                print(f"  Invalid input: {exc}")

    # ------------------------------------------------------------------
    # End-of-Day Wastage Logging
    # ------------------------------------------------------------------

    def eod_wastage_logging(self) -> None:
        """Trigger EOD wastage logging and display the result."""
        print("\n" + "-" * 50)
        print("  END-OF-DAY WASTAGE LOGGING")
        print("-" * 50)
        count = self._inv_svc.log_eod_wastage()
        if count == 0:
            print("  No new wastage to log (all items already logged or fully sold).")
        else:
            print(f"  [OK] Successfully logged {count} wastage record(s).")

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def analytics(self) -> None:
        """Display the analytics sub-menu and render the selected report."""
        print("\n" + "-" * 50)
        print("  ANALYTICS & PREDICTIVE INSIGHTS")
        print("-" * 50)
        print("  1. Wastage Prediction (7-Day Rolling Average)")
        print("  2. Peak-Hour Demand Reporting")
        choice = input("  Select report: ").strip()

        if choice == "1":
            self._show_rolling_avg()
        elif choice == "2":
            self._show_peak_hour()
        else:
            print("  Invalid choice.")

    def _show_rolling_avg(self) -> None:
        print("\n  Calculating 7-day rolling average for today's items…")
        records = self._analytics_svc.get_rolling_7day_wastage_forecast()
        if not records:
            print("  Insufficient data — no items sold today, or no history yet.")
            return

        print("\n" + "-" * 72)
        print(f"  {'7-DAY ROLLING AVERAGE':^68}")
        print("-" * 72)
        print(f"  {'Item':<22}  {'Sold Today':>10}  {'7-Day Avg':>10}  {'Risk':<8}")
        print("  " + "-" * 56)
        for r in records:
            risk = self._analytics_svc.wastage_risk_label(r)
            flag = "[!]" if risk == "High" else " "
            print(
                f"  {r.name:<22}  {r.quantity_sold:>10}  {r.avg_sold:>10.2f}"
                f"  {flag} {risk:<6}"
            )

    def _show_peak_hour(self) -> None:
        print("\n  Peak-hour demand for today:")
        records = self._analytics_svc.get_peak_hour_demand()
        if not records:
            print("  No orders placed today.")
            return

        print("\n" + "-" * 52)
        print(f"  {'PEAK-HOUR DEMAND':^48}")
        print("-" * 52)
        print(f"  {'Hour (24h)':<12}  {'Total Orders':>13}  {'Total Items':>13}")
        print("  " + "-" * 42)
        for r in records:
            print(
                f"  {r.hour_of_day:02d}:00–{r.hour_of_day:02d}:59  "
                f"{r.total_orders:>13}  {r.total_items:>13}"
            )

    # ------------------------------------------------------------------
    # Management portal loop
    # ------------------------------------------------------------------

    def run(self, manager: Manager) -> None:
        """Run the management portal loop for the authenticated *manager*."""
        while True:
            print(f"\n{'=' * 50}")
            print(f"  MANAGEMENT PORTAL  |  Level: {manager.access_level}")
            print(f"  Logged in as: {manager.full_name}")
            print(f"{'=' * 50}")
            print("  1. Morning Setup (Daily Menu)")
            print("  2. Inventory Monitoring & Alerts")
            print("  3. End-of-Day Wastage Logging")
            print("  4. Analytics & Insights")
            print("  5. Back to Main Menu")
            m_choice = input("  Select option: ").strip()

            if m_choice == "1":
                self.morning_setup()
            elif m_choice == "2":
                self.inventory_monitoring()
            elif m_choice == "3":
                self.eod_wastage_logging()
            elif m_choice == "4":
                self.analytics()
            elif m_choice == "5":
                break
            else:
                print("  Invalid option.")
