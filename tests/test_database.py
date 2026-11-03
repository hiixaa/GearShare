"""Phase 3 tests on a fresh temporary database (schema.sql + seed.sql)."""

import sqlite3

import pytest

from sql.setup_db import create_database


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "test.db"
    create_database(path, out=lambda *_: None)   # quiet
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    yield conn
    conn.close()


def count(db, sql):
    return db.execute(sql).fetchone()[0]


# --- 3.4: counts after loading -----------------------------------------------------

@pytest.mark.parametrize("sql, expected", [
    ("SELECT COUNT(*) FROM items", 7),
    ("SELECT COUNT(*) FROM tags", 10),
    ("SELECT COUNT(*) FROM customers", 5),
    ("SELECT COUNT(*) FROM rentals", 10),
    ("SELECT COUNT(*) FROM fines", 4),
    ("SELECT COUNT(*) FROM categories", 8),
    ("SELECT COUNT(*) FROM membership_tiers", 3),
    ("SELECT COUNT(*) FROM item_tags", 11),
])
def test_seed_counts(db, sql, expected):
    # Whole SQL strings, not f"... FROM {table}": no SQL is built by formatting.
    assert count(db, sql) == expected


def test_three_open_rentals(db):
    assert count(db, "SELECT COUNT(*) FROM rentals WHERE return_date IS NULL") == 3


def test_photography_is_parent_of_cameras_and_lenses(db):
    rows = db.execute("""
        SELECT c.name FROM categories AS c
        JOIN categories AS p ON p.category_id = c.parent_id
        WHERE p.name = 'Photography' ORDER BY c.name""").fetchall()
    assert rows == [("Cameras",), ("Lenses",)]


def test_seed_can_be_run_twice(tmp_path):
    path = tmp_path / "twice.db"
    create_database(path, out=lambda *_: None)
    create_database(path, out=lambda *_: None)
    conn = sqlite3.connect(path)
    assert count(conn, "SELECT COUNT(*) FROM rentals") == 10
    conn.close()


# --- 3.3: constraints reject bad data -------------------------------------------------

@pytest.mark.parametrize("bad_sql", [
    "INSERT INTO items VALUES ('123', 'X', 1, 'Equipment', 1, 1, 1)",              # SKU length
    "INSERT INTO items VALUES ('1000000009', 'X', 1, 'Equipment', 1, 1, -1)",      # units < 0
    "INSERT INTO customers VALUES ('C009', 'X', 'ananya@example.com', 'Basic')",   # email UNIQUE
    "INSERT INTO customers VALUES ('C009', 'X', 'x@example.com', 'Gold')",         # unknown tier
    "INSERT INTO rentals VALUES ('RN099', 'C001', '1000000002', '2026-11-03', '2026-11-01', NULL, 0)",
    "INSERT INTO rentals VALUES ('RN099', 'C001', '1000000002', '2026-13-03', '2026-12-31', NULL, 0)",
    "INSERT INTO fines VALUES ('RN004', -1, 0)",                                    # fine < 0
    "DELETE FROM customers WHERE customer_id = 'C004'",                             # RESTRICT
    "DELETE FROM categories WHERE name = 'Photography'",                            # has children
])
def test_constraints_reject_bad_rows(db, bad_sql):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(bad_sql)


def test_deleting_an_item_cascades_to_its_tags_only(db):
    db.execute("INSERT INTO items VALUES ('1000000099', 'Temp', 1, 'Equipment', 1, 1, 1)")
    db.execute("INSERT INTO item_tags VALUES ('1000000099', 1)")
    db.execute("DELETE FROM items WHERE sku = '1000000099'")
    assert count(db, "SELECT COUNT(*) FROM item_tags WHERE sku = '1000000099'") == 0
    assert count(db, "SELECT COUNT(*) FROM tags") == 10
