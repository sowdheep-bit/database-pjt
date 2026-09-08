# Canteen Management System

A modular, production-ready Python CLI application for managing a canteen — featuring customer ordering, inventory control, daily menu management, end-of-day wastage logging, and analytics.

## Architecture

The project follows a **strict 4-layer architecture** with clean dependency flow:

```
Presentation (ui/)  →  Services (services/)  →  Repositories (repositories/)  →  DB (config/)
```

Data models (`models/`) are plain `@dataclass` objects shared across all layers.

```text
canteen_system/
├── config/
│   └── database.py          # DatabaseManager: connection, transaction() & cursor() ctx managers
├── models/
│   ├── customer.py          # Customer dataclass
│   ├── inventory.py         # Ingredient, MenuItem, DailyMenuItem, MenuIngredient, AlertRecord
│   ├── order.py             # Order, WastageRecord, PeakHourRecord, RollingAverageRecord
│   └── user.py              # Manager dataclass
├── repositories/            # Data Access Layer — raw parameterised SQL only
│   ├── customer_repo.py
│   ├── inventory_repo.py
│   ├── menu_repo.py
│   └── order_repo.py
├── services/                # Business Logic Layer — ACID transactions, validation, orchestration
│   ├── auth_service.py
│   ├── order_service.py
│   ├── menu_service.py
│   ├── inventory_service.py
│   └── analytics_service.py
├── ui/                      # Presentation Layer — input(), print(), service calls only
│   ├── customer_cli.py
│   └── management_cli.py
├── schema/
│   └── schema.sql           # Database schema and trigger definitions
└── main.py                  # Entrypoint: dependency wiring, DB bootstrap, menu loop
```

## Prerequisites

- Python 3.10+
- MySQL 8.0+

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the application

```bash
# From the project root (the directory containing canteen_system/)
python canteen_system/main.py
```

The application will:
1. Prompt for MySQL connection credentials
2. Create the `canteen_db` database if it does not exist
3. Run `schema.sql` to create tables (if not already present)
4. Prompt to create the first admin account if none exists
5. Seed two demo menu items (Burger, Fries) with ingredients if the DB is empty

## Usage

### Customer Flow
1. Select **"1. Customer Login"** from the main menu
2. Enter your Customer ID or leave blank to register
3. Select **"1. View Menu & Place Order"** — choose an Item ID and quantity
4. The system atomically validates stock, deducts ingredients, and records the order

### Management Flow
1. Select **"2. Management Login"**
2. Authenticate with your username and password
3. Choose from:
   - **Morning Setup** — set prepared quantities for today's menu items
   - **Inventory Monitoring** — view stock levels, alerts; replenish stock
   - **End-of-Day Wastage Logging** — auto-log unsold quantities
   - **Analytics** — 7-day rolling average or peak-hour demand report

## Key Design Decisions

| Decision | Rationale |
|---|---|
| `db.transaction()` context manager | Replaces manual `try/commit/except rollback` in every ACID block |
| Repository layer with `_in_tx` variants | Transactional operations require an active cursor; non-transactional ones use `execute_query` |
| Services return values / raise exceptions | UI layer decides how to display; services never call `print()` |
| `@dataclass` models with `from_row()` | Zero-cost hydration from DB dicts; no ORM overhead |
| SHA-256 password hashing | Kept for compatibility with existing stored hashes; upgrade path to bcrypt documented in `auth_service.py` |

## Database Schema

See [`schema/schema.sql`](schema/schema.sql) for the full DDL, including:
- 9 tables: `Customers`, `Management`, `MenuItems`, `Inventory`, `MenuIngredients`, `DailyMenu`, `Orders`, `WastageLog`, `Alerts`
- `LowStockAlert` trigger on `Inventory` updates

## Running the Original Monolith

The original `canteen_cli.py` is preserved at the project root and can still be run independently:

```bash
python canteen_cli.py
```
