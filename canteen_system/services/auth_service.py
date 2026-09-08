"""
services/auth_service.py
-------------------------
Authentication & user seeding for the Canteen System.

Responsibilities:
  - Password hashing (SHA-256; see note below about upgrading to bcrypt)
  - Manager login validation
  - First-run admin account seeding
  - Basic initial data seeding (menu items + ingredients)

NOTE: SHA-256 is used here to maintain compatibility with existing stored
PasswordHash values in the database (as in the original monolith).
For new deployments, consider upgrading to bcrypt:
    pip install bcrypt
and replace the `hash_password` implementation with bcrypt.hashpw().
"""

from __future__ import annotations

import getpass
import hashlib
from typing import Optional

from canteen_system.config.database import DatabaseManager
from canteen_system.models.user import Manager


class AuthService:
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Password hashing
    # ------------------------------------------------------------------

    @staticmethod
    def hash_password(password: str) -> str:
        """Return the SHA-256 hex digest of *password*."""
        return hashlib.sha256(password.encode()).hexdigest()

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    def login(self, username: str, password: str) -> Optional[Manager]:
        """
        Validate management credentials.
        Returns a Manager dataclass on success, None on failure.
        """
        hashed = self.hash_password(password)
        rows = self._db.execute_query(
            "SELECT ManagerID, FullName, AccessLevel "
            "FROM Management WHERE Username = %s AND PasswordHash = %s",
            (username, hashed),
        )
        if rows:
            return Manager.from_row(rows[0])
        return None

    # ------------------------------------------------------------------
    # First-run seeding
    # ------------------------------------------------------------------

    def seed_admin_if_needed(self) -> None:
        """
        If no management users exist, interactively prompt for the first
        admin account and create it.
        """
        rows = self._db.execute_query("SELECT COUNT(*) AS cnt FROM Management")
        if rows and rows[0]["cnt"] == 0:
            print("\nNo management users found. Let's create the initial Admin account.")
            username = input("Enter admin username: ").strip()
            password = getpass.getpass("Enter admin password: ")
            hashed = self.hash_password(password)
            self._db.execute_query(
                "INSERT INTO Management (FullName, AccessLevel, Username, PasswordHash) "
                "VALUES (%s, %s, %s, %s)",
                ("System Admin", "Admin", username, hashed),
                commit=True,
            )
            print("Admin account created successfully.")

    def seed_initial_data_if_needed(self) -> None:
        """
        If MenuItems is empty, seed basic demo items and inventory so the
        system is usable out-of-the-box.
        """
        rows = self._db.execute_query("SELECT COUNT(*) AS cnt FROM MenuItems")
        if rows and rows[0]["cnt"] == 0:
            print("Seeding initial menu items and inventory…")
            self._db.execute_query(
                "INSERT INTO MenuItems (Name, Category, CostPrice) "
                "VALUES ('Burger', 'Main', 5.00), ('Fries', 'Side', 2.00)",
                commit=True,
            )
            self._db.execute_query(
                "INSERT INTO Inventory (IngredientName, CurrentStockQuantity, ReorderThreshold) "
                "VALUES ('Bun', 100, 20), ('Patty', 100, 20), ('Potato', 500, 50)",
                commit=True,
            )
            self._db.execute_query(
                "INSERT INTO MenuIngredients (ItemID, IngredientID, QuantityRequired) "
                "VALUES (1, 1, 1), (1, 2, 1), (2, 3, 2)",
                commit=True,
            )
            print("Initial data seeded.")
