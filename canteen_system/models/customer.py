"""
models/customer.py
------------------
Data model for a Canteen customer.
Pure dataclass — no business logic, no database access.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Customer:
    customer_id: int
    full_name: str
    customer_type: str          # 'Student' | 'Staff'
    contact_number: Optional[str] = None

    @classmethod
    def from_row(cls, row: dict) -> "Customer":
        """Hydrate a Customer from a DB result-set dictionary."""
        return cls(
            customer_id=row["CustomerID"],
            full_name=row["FullName"],
            customer_type=row["CustomerType"],
            contact_number=row.get("ContactNumber"),
        )
