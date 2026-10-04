"""
canteen_system/web/db_setup.py
-------------------------------
Database initialisation for the Flask web application.

Key design decisions:
  - Reads credentials from environment variables (no interactive prompts).
  - Creates a WebDatabaseManager per-request wrapper that borrows a pooled
    connection, so all existing repositories and services work unchanged.
  - The global `_pool_db` holds the pool configuration; Flask's
    before_request / teardown_request lifecycle checks it out per request.

DO NOT call input() or getpass() here — this must be safe on a web server.
"""

from __future__ import annotations

import os
from contextlib import contextmanager

from canteen_system.config.database import DatabaseManager


# ---------------------------------------------------------------------------
# Module-level pool holder — initialised once at app startup
# ---------------------------------------------------------------------------

_pool_db: DatabaseManager | None = None


def init_db_pool() -> DatabaseManager:
    """
    Read DB credentials from environment variables and create a
    MySQLConnectionPool.  Call this exactly once from the Flask factory.

    Required environment variables:
        DB_HOST     — default: localhost
        DB_USER     — default: root
        DB_PASSWORD — required (no default)
        DB_PORT     — default: 3306
        DB_NAME     — default: canteen_db
        DB_POOL_SIZE — default: 5
    """
    global _pool_db

    host = os.environ.get("DB_HOST", "localhost")
    user = os.environ.get("DB_USER", "root")
    password = os.environ.get("DB_PASSWORD", "")
    port = int(os.environ.get("DB_PORT", "3306"))
    database = os.environ.get("DB_NAME", "canteen_db")
    pool_size = int(os.environ.get("DB_POOL_SIZE", "5"))

    db = DatabaseManager(host, user, password, port, database)
    db.connect_pool(pool_size=pool_size)

    _pool_db = db
    return db


def get_pool_db() -> DatabaseManager:
    """Return the global pool DatabaseManager.  Raises if not initialised."""
    if _pool_db is None:
        raise RuntimeError(
            "Database pool not initialised. Did you call init_db_pool()?"
        )
    return _pool_db


# ---------------------------------------------------------------------------
# Per-request WebDatabaseManager wrapper
# ---------------------------------------------------------------------------

class WebDatabaseManager(DatabaseManager):
    """
    A DatabaseManager that borrows a single connection from the pool for the
    duration of one HTTP request, then returns it.

    All existing repositories and services use self._db.execute_query() and
    self._db.transaction(), both of which access self._db.connection.
    This wrapper sets self.connection to the borrowed pooled connection, so
    zero changes are needed in any repository or service.
    """

    def __init__(self, pool_db: DatabaseManager, connection) -> None:
        # Copy the config so initialize_schema etc. still work if called
        super().__init__(
            host=pool_db.host,
            user=pool_db.user,
            password=pool_db.password,
            port=pool_db.port,
            database=pool_db.database,
        )
        # Override the connection with the pooled one
        self.connection = connection
        # Share the pool reference too (not strictly needed for requests)
        self._pool = pool_db._pool

    def disconnect(self) -> None:
        """Return the connection to the pool instead of closing it."""
        if self.connection:
            self.connection.close()  # returns to pool
            self.connection = None


@contextmanager
def request_db():
    """
    Context manager that checks out one connection from the pool,
    wraps it in a WebDatabaseManager, yields it, then returns it.

    Usage inside a Flask route::

        with request_db() as db:
            repo = CustomerRepository(db)
            customer = repo.find_by_id(1)
    """
    pool_db = get_pool_db()
    with pool_db.get_pool_connection() as conn:
        web_db = WebDatabaseManager(pool_db, conn)
        try:
            yield web_db
        finally:
            pass  # conn returned to pool by the outer context manager
