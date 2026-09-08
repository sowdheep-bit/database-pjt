"""
models/user.py
--------------
Data model for Management staff / admin users.
Pure dataclass — no business logic, no database access.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Manager:
    manager_id: int
    full_name: str
    access_level: str   # 'Manager' | 'Admin'

    @classmethod
    def from_row(cls, row: dict) -> "Manager":
        return cls(
            manager_id=row["ManagerID"],
            full_name=row["FullName"],
            access_level=row["AccessLevel"],
        )
