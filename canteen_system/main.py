"""
main.py
--------
Application entrypoint for the Canteen Management System.

Responsibilities:
  - Collect DB connection credentials from the user
  - Bootstrap the database (create schema if not present)
  - Wire all dependencies (repos → services → CLI controllers)
  - Seed initial data on first run
  - Run the top-level menu loop
"""

from __future__ import annotations

import getpass
import os
import sys

# -- Ensure the project root is on sys.path so `canteen_system` resolves ------
# __file__ is <project_root>/canteen_system/main.py
# dirname once  → <project_root>/canteen_system/
# dirname twice → <project_root>/            ← this is what we need
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from canteen_system.config.database import DatabaseManager

# Repositories
from canteen_system.repositories.customer_repo import CustomerRepository
from canteen_system.repositories.inventory_repo import InventoryRepository
from canteen_system.repositories.menu_repo import MenuRepository
from canteen_system.repositories.order_repo import OrderRepository

# Services
from canteen_system.services.analytics_service import AnalyticsService
from canteen_system.services.auth_service import AuthService
from canteen_system.services.inventory_service import InventoryService
from canteen_system.services.menu_service import MenuService
from canteen_system.services.order_service import OrderService

# UI Controllers
from canteen_system.ui.customer_cli import CustomerCLI
from canteen_system.ui.management_cli import ManagementCLI


# -- Schema file is relative to this file --------------------------------------
SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "schema", "schema.sql")


def _collect_db_credentials() -> tuple[str, str, str, int]:
    """Prompt the user for MySQL connection details. Returns (host, user, password, port)."""
    print("\n" + "=" * 50)
    print("  CANTEEN MANAGEMENT SYSTEM")
    print("=" * 50)
    print("  Database Connection Setup\n")
    host = input("  MySQL Host   [localhost]: ").strip() or "localhost"
    user = input("  MySQL User   [root]     : ").strip() or "root"
    password = getpass.getpass("  MySQL Password          : ")
    port_str = input("  MySQL Port   [3306]     : ").strip() or "3306"
    try:
        port = int(port_str)
    except ValueError:
        print("  Invalid port — defaulting to 3306.")
        port = 3306
    return host, user, password, port


def _bootstrap_database(db: DatabaseManager) -> None:
    """
    1. Connect without a database selected.
    2. Create `canteen_db` if it doesn't exist.
    3. Reconnect to `canteen_db`.
    4. Run schema.sql if tables are missing.
    """
    print("\n  Connecting to MySQL…")
    db.connect(use_db=False)
    db.ensure_database_exists()
    db.disconnect()

    db.connect(use_db=True)

    if os.path.exists(SCHEMA_FILE):
        db.initialize_schema(SCHEMA_FILE)
    else:
        print(
            f"  Warning: schema file not found at {SCHEMA_FILE}. "
            "Assuming schema already exists."
        )


def _wire_dependencies(db: DatabaseManager) -> tuple[AuthService, CustomerCLI, ManagementCLI]:
    """Construct the full dependency graph and return the top-level controllers."""

    # -- Repositories ----------------------------------------------------------
    customer_repo  = CustomerRepository(db)
    inventory_repo = InventoryRepository(db)
    menu_repo      = MenuRepository(db)
    order_repo     = OrderRepository(db)

    # -- Services --------------------------------------------------------------
    auth_service      = AuthService(db)
    menu_service      = MenuService(menu_repo)
    order_service     = OrderService(db, menu_repo, inventory_repo, order_repo)
    inventory_service = InventoryService(inventory_repo, menu_repo, order_repo)
    analytics_service = AnalyticsService(order_repo)

    # -- UI Controllers --------------------------------------------------------
    customer_cli   = CustomerCLI(customer_repo, menu_service, order_service)
    management_cli = ManagementCLI(menu_service, inventory_service, analytics_service)

    return auth_service, customer_cli, management_cli


def main() -> None:
    host, user, password, port = _collect_db_credentials()

    db = DatabaseManager(host, user, password, port)

    try:
        _bootstrap_database(db)
    except ConnectionError as exc:
        print(f"\n  ✗ Could not connect to MySQL: {exc}")
        print("  Please check your credentials and try again.")
        return

    auth_svc, customer_cli, management_cli = _wire_dependencies(db)

    # First-run seeding
    auth_svc.seed_admin_if_needed()
    auth_svc.seed_initial_data_if_needed()

    # -- Main menu loop --------------------------------------------------------
    try:
        while True:
            print("\n" + "=" * 50)
            print("  MAIN MENU")
            print("=" * 50)
            print("  1. Customer Login")
            print("  2. Management Login")
            print("  3. Exit")
            choice = input("  Select an option: ").strip()

            if choice == "1":
                customer_cli.run()

            elif choice == "2":
                username = input("  Username: ").strip()
                password = getpass.getpass("  Password: ")
                manager = auth_svc.login(username, password)
                if manager:
                    management_cli.run(manager)
                else:
                    print("  Invalid credentials. Please try again.")

            elif choice == "3":
                print("\n  Goodbye!\n")
                break

            else:
                print("  Invalid option. Please select 1, 2, or 3.")

    finally:
        db.disconnect()


if __name__ == "__main__":
    main()
