"""The database connection, the transaction context manager, and Storage."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from errors import StorageError
from storage.customers import CustomerRepository
from storage.items import ItemRepository
from storage.rentals import RentalRepository


class Database:
    """One SQLite connection. All SQL from the repositories runs through here."""

    def __init__(self, path):
        if not Path(path).exists():
            raise StorageError(f"No database at {path}. Create it with: python -m sql.setup_db")
        # isolation_level=None: no hidden auto-BEGIN. Transactions start and end
        # exactly where transaction() says, nowhere else.
        self.conn = sqlite3.connect(path, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._depth = 0

    def execute(self, sql, params=()):
        """Run ONE parameterised statement. Values go in `params`, never in `sql`."""
        try:
            return self.conn.execute(sql, params)
        except sqlite3.Error as e:
            raise StorageError(f"Database error: {e}") from e

    def query(self, sql, params=()):
        return self.execute(sql, params).fetchall()

    @contextmanager
    def transaction(self):
        """Everything inside commits together, or rolls back together.

        Nested use joins the outer transaction (only the outermost one
        commits), so an operation and its audit row share one transaction.
        BEGIN IMMEDIATE takes the write lock BEFORE any reads, so two rent
        requests can't both see the last unit as free (DECISIONS D19).
        """
        if self._depth == 0:
            self.execute("BEGIN IMMEDIATE")
        self._depth += 1
        try:
            yield
        except BaseException:
            self._depth -= 1
            if self._depth == 0:
                self.conn.execute("ROLLBACK")
            raise
        else:
            self._depth -= 1
            if self._depth == 0:
                self.execute("COMMIT")

    def close(self):
        self.conn.close()


class Storage:
    """The storage layer GearShare talks to: one repository per table group."""

    def __init__(self, path):
        self.db = Database(path)
        self.items = ItemRepository(self.db)
        self.customers = CustomerRepository(self.db)
        self.rentals = RentalRepository(self.db)

    def transaction(self):
        return self.db.transaction()

    def close(self):
        self.db.close()
