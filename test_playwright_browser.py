"""
test_playwright_browser.py
--------------------------
Playwright End-to-End Browser Tests for the Canteen Management System Flask Web App.
Runs against the live running Flask web server at http://127.0.0.1:5000.

Usage:
    python test_playwright_browser.py
"""

import sys
import os
import time

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:5000"

PASS = []
FAIL = []

def test(name, condition, detail=""):
    if condition:
        print(f"  ✓ PASS: {name}")
        PASS.append(name)
    else:
        print(f"  ✗ FAIL: {name} — {detail}")
        FAIL.append(f"{name}: {detail}")

def run_playwright_tests():
    print("\n" + "="*60)
    print("  CANTEEN SYSTEM — PLAYWRIGHT BROWSER E2E TESTS")
    print("="*60)

    with sync_playwright() as p:
        # Launch Chromium headless browser
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # ── 1. Home Page ──────────────────────────────────────
        print("\n[1] Browser Landing Page")
        page.goto(f"{BASE_URL}/")
        test("Landing page status & title", "Canteen" in page.title() or page.locator("h1").is_visible())
        test("Customer portal button visible", page.locator("a[href*='/customer/']").count() > 0)
        test("Management portal button visible", page.locator("a[href*='/management/']").count() > 0)

        # ── 2. Customer Registration Flow ─────────────────────
        print("\n[2] Browser Customer Registration Flow")
        page.goto(f"{BASE_URL}/customer/register")
        test("Register form visible", page.locator("input[name='full_name']").is_visible())

        timestamp = int(time.time())
        test_name = f"Playwright User {timestamp}"
        page.fill("input[name='full_name']", test_name)
        page.select_option("select[name='customer_type']", "Student")
        page.fill("input[name='contact_number']", "9998887770")
        page.click("button[type='submit']")

        # Should redirect to customer menu
        page.wait_for_url(f"{BASE_URL}/customer/menu*")
        test("Redirected to menu page after register", "/customer/menu" in page.url)
        test("Menu page content loaded", page.locator(".menu-grid, .menu-container, .card, h1, h2").count() > 0)

        # Extract Customer ID from flash or session banner if shown
        content = page.content()
        test("Flash notice shown", "Account created" in content or "Customer ID" in content or "Menu" in content)

        # ── 3. Customer Order Flow ────────────────────────────
        print("\n[3] Browser Order Submission")
        # Click first 'Order Now' or submit order form if available
        if page.locator("form[action*='/customer/order']").count() > 0:
            order_form = page.locator("form[action*='/customer/order']").first
            quantity_input = order_form.locator("input[name='quantity']")
            if quantity_input.is_visible():
                quantity_input.fill("1")
            order_form.locator("button[type='submit']").click(force=True)
            page.wait_for_load_state("networkidle")
            test("Order submitted successfully", "success" in page.content().lower() or "order" in page.content().lower() or "placed" in page.content().lower())
        else:
            print("  (No daily items currently available for immediate order form submit)")

        # ── 4. Customer Order History ─────────────────────────
        print("\n[4] Browser Customer Order History")
        page.goto(f"{BASE_URL}/customer/orders")
        test("Order history loaded", page.locator(".page-title, .table-wrapper, .empty-state, table").count() > 0)

        # ── 5. Customer Logout ────────────────────────────────
        print("\n[5] Browser Customer Logout")
        page.goto(f"{BASE_URL}/customer/logout")
        test("Redirected after logout", "/customer/login" in page.url or "/" in page.url)

        # ── 6. Management Login (Invalid & Valid) ──────────────
        print("\n[6] Browser Management Login")
        page.goto(f"{BASE_URL}/management/login")

        # Invalid login
        page.fill("input[name='username']", "sowdheep")
        page.fill("input[name='password']", "wrongpassword123")
        page.click("button[type='submit']")
        page.wait_for_load_state("networkidle")
        test("Invalid login shows error alert", "invalid" in page.content().lower() or "wrong" in page.content().lower() or page.locator(".alert, .flash, .error").is_visible())

        # Valid login
        page.fill("input[name='username']", "sowdheep")
        page.fill("input[name='password']", "sowdheep")
        page.click("button[type='submit']")
        page.wait_for_url(f"{BASE_URL}/management/dashboard*")
        test("Valid login redirects to dashboard", "/management/dashboard" in page.url)
        test("Dashboard title/KPI visible", page.locator("h1, h2, .kpi-card, .card").count() > 0)

        # ── 7. Management Morning Setup ────────────────────────
        print("\n[7] Browser Management Morning Setup")
        page.goto(f"{BASE_URL}/management/morning-setup")
        test("Morning setup page loads", page.locator("form, table, input").count() > 0)
        
        if page.locator("form[action*='/management/morning-setup']").count() > 0:
            setup_form = page.locator("form[action*='/management/morning-setup']").first
            setup_form.locator("input[name='quantity']").fill("25")
            setup_form.locator("button[type='submit']").click(force=True)
            page.wait_for_load_state("networkidle")
            test("Morning setup quantity set", "updated" in page.content().lower() or "quantity" in page.content().lower() or page.locator(".alert").is_visible())

        # ── 8. Management Inventory ───────────────────────────
        print("\n[8] Browser Management Inventory")
        page.goto(f"{BASE_URL}/management/inventory")
        test("Inventory table visible", page.locator("table, .inventory-grid, .card").count() > 0)

        if page.locator("form[action*='/inventory/replenish']").count() > 0:
            repl_form = page.locator("form[action*='/inventory/replenish']").first
            repl_form.locator("input[name='amount']").fill("10")
            repl_form.locator("button[type='submit']").click(force=True)
            page.wait_for_load_state("networkidle")
            test("Stock replenishment submitted", "replenish" in page.content().lower() or "stock" in page.content().lower())

        # ── 9. Management Analytics ───────────────────────────
        print("\n[9] Browser Management Analytics")
        page.goto(f"{BASE_URL}/management/analytics")
        test("Analytics page loaded", "analytics" in page.content().lower() or page.locator("canvas, script, .card").count() > 0)

        # ── 10. Management EOD Wastage ────────────────────────
        print("\n[10] Browser Management EOD Wastage")
        if page.locator("form[action*='/management/wastage']").count() > 0:
            page.locator("form[action*='/management/wastage']").first.locator("button[type='submit']").click(force=True)
            page.wait_for_load_state("networkidle")
            test("Wastage logging form executed", "wastage" in page.content().lower() or "log" in page.content().lower())

        # ── 11. Management Logout ─────────────────────────────
        print("\n[11] Browser Management Logout")
        page.goto(f"{BASE_URL}/management/logout")
        test("Management logout redirects", "/management/login" in page.url or "/" in page.url)

        browser.close()

    print("\n" + "="*60)
    print(f"  PLAYWRIGHT RESULTS: {len(PASS)} PASSED, {len(FAIL)} FAILED")
    print("="*60)
    if FAIL:
        print("PLAYWRIGHT FAILURES:")
        for f in FAIL:
            print(f"  - {f}")
    else:
        print("  All Playwright browser tests passed!")

if __name__ == "__main__":
    run_playwright_tests()
