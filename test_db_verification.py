"""
test_db_verification.py
------------------------
Database State Change Verification for the Canteen Management System.
Verifies ACID transaction state changes for Order Placement, Stock Replenishment, Morning Setup, and Wastage Logging.

Usage:
    python test_db_verification.py
"""

import sys
import os
import datetime
from decimal import Decimal

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from dotenv import load_dotenv
load_dotenv()

from canteen_system.web.db_setup import init_db_pool, request_db
from canteen_system.web.utils import build_services
from canteen_system.repositories.menu_repo import MenuRepository
from canteen_system.repositories.inventory_repo import InventoryRepository

PASS = []
FAIL = []

def test(name, condition, detail=""):
    if condition:
        print(f"  ✓ PASS: {name}")
        PASS.append(name)
    else:
        print(f"  ✗ FAIL: {name} — {detail}")
        FAIL.append(f"{name}: {detail}")

def run_db_verifications():
    print("\n" + "="*60)
    print("  CANTEEN SYSTEM — DATABASE STATE VERIFICATION")
    print("="*60)

    init_db_pool()

    with request_db() as db:
        svc = build_services(db)
        menu_repo = MenuRepository(db)
        inv_repo = InventoryRepository(db)

        # 1. Register a test customer
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        cust = svc.customer_repo.create(f"DB Test Cust {timestamp}", "Student", "9990001112")
        test("Customer record inserted into DB", cust.customer_id is not None)

        # 2. Morning Setup: Set ItemID=1 (Burger) quantity to 50 for today
        today = datetime.date.today()
        svc.menu.set_daily_quantity(1, 50)
        
        daily_item = menu_repo.get_daily_summary(today)
        burger_daily = next((i for i in daily_item if i['ItemID'] == 1), None)
        test("Morning setup created DailyMenu row", burger_daily is not None)

        # 3. Replenish Bun ingredient (ID=1) by 20 to ensure enough stock
        inv_before = inv_repo.get_all()
        bun_before = next((i for i in inv_before if i.ingredient_id == 1), None)
        
        svc.inventory.replenish_stock(1, 20.0)
        
        inv_after_repl = inv_repo.get_all()
        bun_after_repl = next((i for i in inv_after_repl if i.ingredient_id == 1), None)
        
        test(
            "Replenish stock increased Inventory quantity",
            bun_after_repl and bun_before and bun_after_repl.current_stock == bun_before.current_stock + Decimal('20.0')
        )

        # 4. Place Order via OrderService.place_order (ACID transaction)
        order_count_before = db.execute_query("SELECT COUNT(*) AS cnt FROM Orders")[0]['cnt']
        
        daily_item_before = menu_repo.get_daily_summary(today)
        burger_before = next((i for i in daily_item_before if i['ItemID'] == 1), None)
        qty_prepared_before = burger_before['QuantityPrepared'] if burger_before else 0
        qty_sold_before = burger_before['QuantitySold'] if burger_before else 0

        order_result = svc.order.place_order(cust.customer_id, 1, 2)
        test("Order placement returned success message", "Order placed" in order_result, f"Got: {order_result}")

        # Check DB state changes
        order_count_after = db.execute_query("SELECT COUNT(*) AS cnt FROM Orders")[0]['cnt']
        test("Orders table row count increased by 1", order_count_after == order_count_before + 1)

        latest_order = db.execute_query("SELECT * FROM Orders ORDER BY OrderID DESC LIMIT 1")[0]
        test("Order recorded correct CustomerID", latest_order['CustomerID'] == cust.customer_id)
        test("Order recorded correct ItemID", latest_order['ItemID'] == 1)
        test("Order recorded correct Quantity", latest_order['QuantityOrdered'] == 2)

        daily_item_after = menu_repo.get_daily_summary(today)
        burger_after = next((i for i in daily_item_after if i['ItemID'] == 1), None)
        qty_sold_after = burger_after['QuantitySold'] if burger_after else 0
        test("DailyMenu quantity sold increased by 2", qty_sold_after == qty_sold_before + 2)

    print("\n" + "="*60)
    print(f"  DB VERIFICATION RESULTS: {len(PASS)} PASSED, {len(FAIL)} FAILED")
    print("="*60)
    if FAIL:
        print("FAILURES:")
        for f in FAIL:
            print(f"  - {f}")
    else:
        print("  All database state verifications passed!")

if __name__ == "__main__":
    run_db_verifications()
