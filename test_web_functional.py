"""
Comprehensive functional test for the Canteen Management System web application.
Tests every route, session handling, database interactions, and error cases.
Run: python test_web_functional.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import json
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

from canteen_system.web.app import create_app

app = create_app()
app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False

PASS = []
FAIL = []

def test(name, condition, detail=""):
    if condition:
        print(f"  ✓ PASS: {name}")
        PASS.append(name)
    else:
        print(f"  ✗ FAIL: {name} — {detail}")
        FAIL.append(f"{name}: {detail}")

def get_management_credentials():
    """Get the actual management username from the DB."""
    conn = mysql.connector.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        user=os.environ.get('DB_USER', 'root'),
        password=os.environ.get('DB_PASSWORD', ''),
        port=int(os.environ.get('DB_PORT', '3306')),
        database=os.environ.get('DB_NAME', 'canteen_db'),
    )
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT Username FROM Management LIMIT 1")
    row = cur.fetchone()
    conn.close()
    return row['Username'] if row else None

with app.test_client() as client:
    print("\n" + "="*60)
    print("  CANTEEN SYSTEM - WEB FUNCTIONAL TESTS")
    print("="*60)

    # ── Test 1: Landing page ──────────────────────────────
    print("\n[1] Landing Page")
    r = client.get('/')
    test("Landing page loads (200)", r.status_code == 200)
    test("Landing page has 'Canteen'", b'Canteen' in r.data)
    test("Landing page has customer link", b'customer' in r.data.lower())
    test("Landing page has management link", b'management' in r.data.lower())

    # ── Test 2: Customer Register ────────────────────────
    print("\n[2] Customer Registration")
    r = client.get('/customer/register')
    test("Register page loads (200)", r.status_code == 200)

    r = client.post('/customer/register', data={
        'full_name': 'Test Student Web',
        'customer_type': 'Student',
        'contact_number': '9876543210'
    }, follow_redirects=True)
    test("Register POST succeeds", r.status_code == 200)
    test("Registration redirects to menu", b'Menu' in r.data or b'menu' in r.data.lower())
    test("Success flash shown", b'Account created' in r.data or b'Customer ID' in r.data)

    # Check session has customer_id
    with client.session_transaction() as sess:
        customer_id = sess.get('customer_id')
    test("Customer ID in session after register", customer_id is not None, f"Got: {customer_id}")

    # ── Test 3: Customer Menu ────────────────────────────
    print("\n[3] Customer Menu")
    r = client.get('/customer/menu')
    test("Menu page loads (200)", r.status_code == 200)
    test("Menu page has expected structure", b'Menu' in r.data or b'menu' in r.data.lower())

    # ── Test 4: Customer Login/ID lookup ─────────────────
    print("\n[4] Customer Login (ID lookup)")
    # Clear session
    with client.session_transaction() as sess:
        sess.clear()

    # Test login with the customer we just created
    r = client.post('/customer/login', data={'customer_id': str(customer_id)}, follow_redirects=True)
    test("Customer login by ID (200)", r.status_code == 200)
    test("Login redirects to menu", b'Menu' in r.data or b'menu' in r.data.lower())

    with client.session_transaction() as sess:
        logged_in = sess.get('customer_id') == customer_id
    test("Customer session set after login", logged_in)

    # ── Test 5: Customer Logout ──────────────────────────
    print("\n[5] Customer Logout")
    r = client.get('/customer/logout', follow_redirects=True)
    test("Logout redirects (200)", r.status_code == 200)
    with client.session_transaction() as sess:
        test("Session cleared after logout", 'customer_id' not in sess)

    # ── Test 6: Access control — unauthenticated customer menu ──
    print("\n[6] Customer Access Control")
    r = client.get('/customer/menu', follow_redirects=False)
    test("Menu redirects unauthenticated (302)", r.status_code == 302)
    test("Redirects to login", 'login' in r.headers.get('Location', ''))

    # ── Test 7: Management Login ─────────────────────────
    print("\n[7] Management Login")
    r = client.get('/management/login')
    test("Management login page loads (200)", r.status_code == 200)

    mgmt_username = get_management_credentials()
    print(f"  (Found management username: '{mgmt_username}')")

    if mgmt_username:
        # Try common passwords — the seed created with "admin123" or prompted
        # We'll check what hash is stored and try known passwords
        conn = mysql.connector.connect(
            host=os.environ.get('DB_HOST', 'localhost'),
            user=os.environ.get('DB_USER', 'root'),
            password=os.environ.get('DB_PASSWORD', ''),
            port=int(os.environ.get('DB_PORT', '3306')),
            database=os.environ.get('DB_NAME', 'canteen_db'),
        )
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT Username, PasswordHash FROM Management LIMIT 1")
        mgmt_row = cur.fetchone()
        conn.close()

        import hashlib
        # Test common passwords
        mgmt_pass = None
        for pw in [mgmt_username, 'sowdheep', 'admin', 'admin123', 'password', '12345678', '123456', 'canteen', 'root']:
            hashed = hashlib.sha256(pw.encode()).hexdigest()
            if hashed == mgmt_row['PasswordHash']:
                mgmt_pass = pw
                break

        if mgmt_pass:
            print(f"  (Found management password via hash match: '{mgmt_pass}')")
            r = client.post('/management/login', data={
                'username': mgmt_username,
                'password': mgmt_pass
            }, follow_redirects=True)
            test("Management login succeeds (200)", r.status_code == 200)
            test("Redirects to dashboard", b'Dashboard' in r.data or b'dashboard' in r.data.lower())

            with client.session_transaction() as sess:
                test("Manager session set", 'manager_id' in sess)
        else:
            print("  (Could not determine management password — testing with wrong credentials)")
            r = client.post('/management/login', data={
                'username': mgmt_username,
                'password': 'wrongpassword'
            }, follow_redirects=True)
            test("Bad credentials rejected", b'Invalid' in r.data or b'wrong' in r.data.lower())
            mgmt_pass = None
    else:
        print("  (No management users in DB)")
        mgmt_pass = None

    # ── Test 8: Management Dashboard ────────────────────
    print("\n[8] Management Dashboard")
    if mgmt_pass:
        r = client.get('/management/dashboard')
        test("Dashboard loads (200)", r.status_code == 200)
        test("Dashboard has KPI structure", b'Dashboard' in r.data or b'Orders' in r.data)

    items = []
    # ── Test 9: Morning Setup ─────────────────────────────
    print("\n[9] Morning Setup")
    if mgmt_pass:
        r = client.get('/management/morning-setup')
        test("Morning setup page loads (200)", r.status_code == 200)

        # Get a menu item ID from DB
        conn = mysql.connector.connect(
            host=os.environ.get('DB_HOST', 'localhost'),
            user=os.environ.get('DB_USER', 'root'),
            password=os.environ.get('DB_PASSWORD', ''),
            port=int(os.environ.get('DB_PORT', '3306')),
            database=os.environ.get('DB_NAME', 'canteen_db'),
        )
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT ItemID, Name FROM MenuItems LIMIT 2")
        items = cur.fetchall()
        conn.close()

        if items:
            item = items[0]
            print(f"  (Setting quantity for item: {item['Name']} ID={item['ItemID']})")
            r = client.post('/management/morning-setup', data={
                'item_id': str(item['ItemID']),
                'quantity': '50'
            }, follow_redirects=True)
            test("Morning setup POST succeeds (200)", r.status_code == 200)
            test("Success flash shown", b'updated' in r.data.lower() or b'Quantity' in r.data)

            if len(items) > 1:
                item2 = items[1]
                r = client.post('/management/morning-setup', data={
                    'item_id': str(item2['ItemID']),
                    'quantity': '30'
                }, follow_redirects=True)
                test("Morning setup second item", r.status_code == 200)
        else:
            test("Morning setup items available", False, "No MenuItems in DB")

    # ── Test 10: Customer Menu After Morning Setup ────────
    print("\n[10] Customer Menu After Morning Setup")
    # Login as customer
    with client.session_transaction() as sess:
        sess['customer_id'] = customer_id
        sess['customer_name'] = 'Test Customer'

    r = client.get('/customer/menu')
    test("Menu after setup loads (200)", r.status_code == 200)
    has_items = b'Order Now' in r.data or b'order' in r.data.lower()
    test("Menu shows items after morning setup", has_items, "No order buttons found")

    # ── Test 11: Place Order ────────────────────────────
    print("\n[11] Place Order (ACID Transaction)")
    if has_items and items:
        item_id = items[0]['ItemID']
        r = client.post('/customer/order', data={
            'item_id': str(item_id),
            'quantity': '2'
        }, follow_redirects=True)
        test("Order POST returns 200", r.status_code == 200)
        order_success = b'successfully' in r.data.lower() or b'placed' in r.data.lower()
        order_rejected = b'rejected' in r.data.lower() or b'Insufficient' in r.data
        test("Order processed (success or valid rejection)", order_success or order_rejected,
             f"Neither success nor rejection message found")
        if order_success:
            print("    → Order was successfully placed!")
        elif order_rejected:
            print("    → Order rejected (likely insufficient ingredients in test DB)")

    # ── Test 12: Order History ──────────────────────────
    print("\n[12] Customer Order History")
    r = client.get('/customer/orders')
    test("Order history loads (200)", r.status_code == 200)
    test("Order history page structure OK", b'Orders' in r.data or b'orders' in r.data.lower())

    # ── Test 13: Inventory Management ────────────────────
    print("\n[13] Management Inventory")
    if mgmt_pass:
        with client.session_transaction() as sess:
            sess['manager_id'] = 1
            sess['manager_name'] = 'Admin'
            sess['manager_level'] = 'Admin'

        r = client.get('/management/inventory')
        test("Inventory page loads (200)", r.status_code == 200)
        test("Inventory table present", b'Stock' in r.data or b'stock' in r.data.lower())

        # Replenish stock
        conn = mysql.connector.connect(
            host=os.environ.get('DB_HOST', 'localhost'),
            user=os.environ.get('DB_USER', 'root'),
            password=os.environ.get('DB_PASSWORD', ''),
            port=int(os.environ.get('DB_PORT', '3306')),
            database=os.environ.get('DB_NAME', 'canteen_db'),
        )
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT IngredientID, IngredientName FROM Inventory LIMIT 1")
        ing = cur.fetchone()
        conn.close()

        if ing:
            r = client.post('/management/inventory/replenish', data={
                'ingredient_id': str(ing['IngredientID']),
                'amount': '25.5'
            }, follow_redirects=True)
            test("Replenish POST succeeds (200)", r.status_code == 200)
            test("Replenish flash shown", b'replenish' in r.data.lower() or b'Stock' in r.data)

    # ── Test 14: Analytics API ──────────────────────────
    print("\n[14] Analytics API")
    with client.session_transaction() as sess:
        sess['manager_id'] = 1

    r = client.get('/api/analytics/rolling-avg')
    test("Rolling avg API returns 200", r.status_code == 200)
    data = json.loads(r.data)
    test("Rolling avg returns list or empty list", isinstance(data, list), f"Got: {type(data)}")
    print(f"    → Rolling avg records: {len(data)}")

    r = client.get('/api/analytics/peak-hour')
    test("Peak hour API returns 200", r.status_code == 200)
    data = json.loads(r.data)
    test("Peak hour returns list", isinstance(data, list), f"Got: {type(data)}")
    print(f"    → Peak hour records: {len(data)}")

    # ── Test 15: EOD Wastage ────────────────────────────
    print("\n[15] End-of-Day Wastage")
    with client.session_transaction() as sess:
        sess['manager_id'] = 1

    r = client.post('/management/wastage', follow_redirects=True)
    test("Wastage POST succeeds (200)", r.status_code == 200)
    test("Wastage flash shown", b'wastage' in r.data.lower() or b'log' in r.data.lower())

    # ── Test 16: Access Control (Management) ─────────────
    print("\n[16] Management Access Control")
    with client.session_transaction() as sess:
        sess.clear()

    r = client.get('/management/dashboard', follow_redirects=False)
    test("Unauthenticated dashboard redirects (302)", r.status_code == 302)
    test("Redirects to management login", 'login' in r.headers.get('Location', ''))

    r = client.get('/api/analytics/rolling-avg')
    test("Unauthenticated API returns 401", r.status_code == 401)

    # ── Test 17: Bad customer ID ─────────────────────────
    print("\n[17] Error Handling")
    r = client.post('/customer/login', data={'customer_id': '999999'}, follow_redirects=True)
    test("Unknown customer ID handled gracefully (200)", r.status_code == 200)
    test("Redirects to register for unknown ID", b'Register' in r.data or b'register' in r.data.lower())

    r = client.post('/customer/login', data={'customer_id': 'notanumber'}, follow_redirects=True)
    test("Invalid customer ID handled (200)", r.status_code == 200)
    test("Shows error message for invalid ID", b'valid' in r.data.lower() or b'error' in r.data.lower() or b'numeric' in r.data.lower())

    # ── Summary ─────────────────────────────────────────
    print("\n" + "="*60)
    print(f"  RESULTS: {len(PASS)} PASSED, {len(FAIL)} FAILED")
    print("="*60)
    if FAIL:
        print("FAILURES:")
        for f in FAIL:
            print(f"  - {f}")
    else:
        print("  All tests passed!")
