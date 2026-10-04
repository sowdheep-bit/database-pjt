"""
config/database.py
------------------
Database connection management for the Canteen System.

Responsibilities:
  - Establish / close MySQL connections
  - Provide a managed cursor context manager (auto-close)
  - Provide a transaction context manager (auto commit/rollback)
  - Execute raw parameterised queries (SELECT returns rows, DML returns lastrowid)
  - Bootstrap the schema on first run
"""

from __future__ import annotations

import os
import subprocess
from contextlib import contextmanager
from typing import Any, Generator, Optional

import mysql.connector
from mysql.connector import Error, MySQLConnection
from mysql.connector.pooling import MySQLConnectionPool


class DatabaseManager:
    """Manages a single persistent MySQL connection for the application lifetime."""

    def __init__(
        self,
        host: str,
        user: str,
        password: str,
        port: int = 3306,
        database: str = "canteen_db",
    ) -> None:
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self.database = database
        self.connection: Optional[MySQLConnection] = None
        self._pool: Optional[MySQLConnectionPool] = None

    # ------------------------------------------------------------------
    # Web connection pool (additive — does not affect CLI connect/disconnect)
    # ------------------------------------------------------------------

    def connect_pool(self, pool_size: int = 5) -> None:
        """
        Initialise a MySQLConnectionPool for concurrent web requests.
        Call this during Flask app startup instead of connect().
        The CLI continues to use connect() / disconnect() — unchanged.
        """
        self._pool = MySQLConnectionPool(
            pool_name="canteen_pool",
            pool_size=pool_size,
            host=self.host,
            user=self.user,
            password=self.password,
            port=self.port,
            database=self.database,
        )

    @contextmanager
    def get_pool_connection(self):
        """
        Yield a connection from the pool.  The connection is returned to the
        pool automatically when the context exits (even on error).

        Usage::

            with db.get_pool_connection() as conn:
                with conn.cursor(dictionary=True) as cur:
                    cur.execute(...)
        """
        if self._pool is None:
            raise RuntimeError("Connection pool is not initialised. Call connect_pool() first.")
        conn = self._pool.get_connection()
        try:
            yield conn
        finally:
            conn.close()  # returns connection back to pool

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def connect(self, use_db: bool = True) -> bool:
        """Open a connection.  Returns True on success, False on failure."""
        try:
            db_arg = self.database if use_db else None
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                port=self.port,
                database=db_arg,
            )
            return self.connection.is_connected()
        except Error as exc:
            raise ConnectionError(f"Cannot connect to MySQL: {exc}") from exc

    def disconnect(self) -> None:
        """Close the connection if open."""
        if self.connection and self.connection.is_connected():
            self.connection.close()

    # ------------------------------------------------------------------
    # Context managers
    # ------------------------------------------------------------------

    @contextmanager
    def cursor(self) -> Generator[Any, None, None]:
        """Yield a dictionary cursor, always closing it on exit."""
        cur = self.connection.cursor(dictionary=True)
        try:
            yield cur
        finally:
            cur.close()

    @contextmanager
    def transaction(self) -> Generator[Any, None, None]:
        """
        Managed ACID transaction block.

        Usage::

            with db.transaction() as cur:
                cur.execute("UPDATE ...")
                cur.execute("INSERT ...")
            # auto-committed on exit; rolled back on any exception
        """
        # Flush any implicit autocommit state first
        self.connection.commit()
        self.connection.start_transaction()
        cur = self.connection.cursor(dictionary=True)
        try:
            yield cur
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cur.close()

    # ------------------------------------------------------------------
    # Generic query helper (used by repositories for non-transactional ops)
    # ------------------------------------------------------------------

    def execute_query(
        self,
        query: str,
        params: Optional[tuple] = None,
        commit: bool = False,
    ) -> Any:
        """
        Execute *query* with optional *params*.

        - SELECT / SHOW  → returns list[dict]
        - INSERT with commit=True → returns lastrowid (int)
        - UPDATE / DELETE with commit=True → returns None (commits silently)
        - Raises RuntimeError on execution failure.
        """
        with self.cursor() as cur:
            try:
                cur.execute(query, params or ())
                if commit:
                    self.connection.commit()
                    return cur.lastrowid
                upper = query.strip().upper()
                if upper.startswith(("SELECT", "SHOW", "WITH")):
                    return cur.fetchall()
                return None
            except Error as exc:
                if commit:
                    self.connection.rollback()
                raise RuntimeError(f"Query failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Schema bootstrap
    # ------------------------------------------------------------------

    def ensure_database_exists(self) -> None:
        """Create the `canteen_db` schema if it doesn't exist."""
        cur = self.connection.cursor()
        try:
            cur.execute("CREATE DATABASE IF NOT EXISTS canteen_db")
            # consume any result so the connection stays clean
            cur.fetchall()
            self.connection.commit()
        finally:
            cur.close()

    def initialize_schema(self, schema_file: str) -> bool:
        """
        Execute the SQL schema file via the mysql CLI (best-effort).
        Falls back gracefully if the CLI is not available.
        Returns True if the schema tables are present afterwards.
        """
        with self.cursor() as cur:
            cur.execute("SHOW TABLES")
            tables = cur.fetchall()
            if tables:
                return True  # Already initialised

        print("Initialising database schema…")
        try:
            env = os.environ.copy()
            if self.password:
                env["MYSQL_PWD"] = self.password
            cmd = ["mysql", "-h", self.host, "-u", self.user, "-P", str(self.port)]
            with open(schema_file, "r") as fh:
                result = subprocess.run(
                    cmd, stdin=fh, env=env, capture_output=True, text=True
                )
            if result.returncode == 0:
                print("Schema initialised successfully.")
            else:
                print(f"mysql CLI error (schema may already exist): {result.stderr.strip()}")
        except Exception as exc:
            print(f"Could not run mysql CLI: {exc}. Assuming schema exists.")

        # Reconnect so the new tables are visible
        self.disconnect()
        return self.connect()
