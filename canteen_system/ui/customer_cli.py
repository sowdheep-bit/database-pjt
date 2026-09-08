"""
ui/customer_cli.py
-------------------
Presentation layer for the customer-facing CLI experience.

Responsibilities:
  - Prompt for customer ID / registration details
  - Render today's menu as a formatted table
  - Prompt for order item + quantity selection
  - Display order result messages

Zero SQL. Zero business logic. Only input(), print(), and service calls.
"""

from __future__ import annotations

from typing import Optional

from canteen_system.models.customer import Customer
from canteen_system.repositories.customer_repo import CustomerRepository
from canteen_system.services.menu_service import MenuService
from canteen_system.services.order_service import OrderService


class CustomerCLI:
    def __init__(
        self,
        customer_repo: CustomerRepository,
        menu_service: MenuService,
        order_service: OrderService,
    ) -> None:
        self._customer_repo = customer_repo
        self._menu_service = menu_service
        self._order_service = order_service

    # ------------------------------------------------------------------
    # Customer identification
    # ------------------------------------------------------------------

    def get_or_create_customer(self) -> Optional[Customer]:
        """
        Prompt the user to identify themselves by ID or register as new.
        Returns a Customer object, or None if registration fails.
        """
        print("\n" + "-" * 50)
        print("  CUSTOMER LOGIN")
        print("-" * 50)
        customer_id_str = input("Enter your Customer ID (leave blank to register): ").strip()

        if customer_id_str:
            try:
                customer = self._customer_repo.find_by_id(int(customer_id_str))
                if customer:
                    print(f"\n  Welcome back, {customer.full_name}!")
                    return customer
                print("  Customer ID not found. Please register below.")
            except ValueError:
                print("  Invalid ID format.")

        # Registration flow
        print("\n  New Customer Registration")
        name = input("  Full Name        : ").strip()
        if not name:
            print("  Name cannot be empty.")
            return None

        ctype = input("  Type (Student/Staff): ").strip().title()
        if ctype not in ("Student", "Staff"):
            print("  Invalid type. Must be 'Student' or 'Staff'.")
            return None

        contact = input("  Contact Number   : ").strip()

        try:
            customer = self._customer_repo.create(name, ctype, contact)
            print(f"\n  Registered! Your Customer ID is: {customer.customer_id}")
            return customer
        except RuntimeError as exc:
            print(f"  Registration failed: {exc}")
            return None

    # ------------------------------------------------------------------
    # Menu display
    # ------------------------------------------------------------------

    def display_menu(self) -> bool:
        """
        Render today's available menu.
        Returns True if there are available items, False otherwise.
        """
        items = self._menu_service.get_today_menu()

        if not items:
            print("\n  No items available today or everything is sold out.")
            return False

        print("\n" + "-" * 72)
        print(f"  {'TODAY\'S MENU':^68}")
        print("-" * 72)
        print(f"  {'ID':<5}  {'Item':<28}  {'Category':<14}  {'Price':>8}  {'Left':>6}")
        print("  " + "-" * 68)
        for item in items:
            print(
                f"  {item.item_id:<5}  {item.name:<28}  {item.category:<14}"
                f"  ${item.cost_price:>7.2f}  {item.available:>6}"
            )
        print("-" * 72)
        return True

    # ------------------------------------------------------------------
    # Order placement
    # ------------------------------------------------------------------

    def prompt_place_order(self, customer: Customer) -> None:
        """
        Display the menu and prompt the user to place an order.
        Delegates the ACID transaction to OrderService.
        """
        if not self.display_menu():
            return

        try:
            item_id = int(input("\n  Enter Item ID to order : ").strip())
            quantity = int(input("  Enter quantity         : ").strip())
        except ValueError:
            print("  Invalid input — please enter numbers only.")
            return

        result = self._order_service.place_order(customer.customer_id, item_id, quantity)
        print(f"\n  {result}")

    # ------------------------------------------------------------------
    # Customer sub-menu loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Run the full customer session: identify → order loop → exit."""
        customer = self.get_or_create_customer()
        if not customer:
            return

        while True:
            print(f"\n  Welcome, {customer.full_name}!")
            print("  1. View Menu & Place Order")
            print("  2. Back to Main Menu")
            choice = input("  Select option: ").strip()

            if choice == "1":
                self.prompt_place_order(customer)
            elif choice == "2":
                break
            else:
                print("  Invalid option.")
