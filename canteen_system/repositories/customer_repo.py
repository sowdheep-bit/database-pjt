"""
repositories/customer_repo.py
------------------------------
Data Access Layer — Customer table only.

All methods execute raw parameterised SQL via the DatabaseManager.
No business logic lives here.
"""

from __future__ import annotations

from typing import Optional

from canteen_system.config.database import DatabaseManager
from canteen_system.models.customer import Customer


class CustomerRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    def find_by_id(self, customer_id: int) -> Optional[Customer]:
        """Return a Customer by primary key, or None if not found."""
        rows = self._db.execute_query(
            "SELECT * FROM Customers WHERE CustomerID = %s",
            (customer_id,),
        )
        if rows:
            return Customer.from_row(rows[0])
        return None

    def create(self, full_name: str, customer_type: str, contact_number: str) -> Customer:
        """
        Insert a new customer row.
        Returns the newly created Customer (with auto-assigned ID).
        Raises RuntimeError on DB failure.
        """
        new_id = self._db.execute_query(
            "INSERT INTO Customers (FullName, CustomerType, ContactNumber) VALUES (%s, %s, %s)",
            (full_name, customer_type, contact_number),
            commit=True,
        )
        if new_id is None:
            raise RuntimeError("Failed to insert customer — no lastrowid returned.")
        return Customer(
            customer_id=new_id,
            full_name=full_name,
            customer_type=customer_type,
            contact_number=contact_number,
        )
