"""Task 3.5: every query in sql/queries.sql must return the spec's expected values."""

import sqlite3
from pathlib import Path

import pytest

from sql.run_sql import split_statements
from sql.setup_db import create_database

QUERIES_FILE = Path(__file__).parent.parent / "sql" / "queries.sql"

EXPECTED = {
    "Q1": [("Canon EOS 200D", "dslr"), ("Canon EOS 200D", "photo"),
           ("Sony 50mm Lens", "lens"), ("Sony 50mm Lens", "photo")],
    "Q2": [("RN001", "Vikram Shah", "DJI Mini Drone"),
           ("RN002", "Rohan Das", "Canon EOS 200D"),
           ("RN003", "Meera Joshi", "Manfrotto Tripod")],
    "Q3": [("Vikram Shah", "DJI Mini Drone", "2026-10-29", 5),
           ("Rohan Das", "Canon EOS 200D", "2026-10-31", 3)],
    "Q4": [("Canon EOS 200D", 3), ("DJI Mini Drone", 2), ("Rode Wireless Mic", 2)],
    "Q5": [("Vintage Leica (Showcase)",)],
    "Q6": [("Pooja Menon",)],
    "Q7": [("Basic", "2026-07", 600), ("Basic", "2026-08", 600), ("Plus", "2026-06", 300)],
    "Q8": [("Paid", 900), ("Pending", 600)],
    "Q9": [("Vikram Shah", 3)],
    "Q10": [("Accessories", 22.0), ("Audio", 10.0), ("Cameras", 5.5), ("Drones", 5.0)],
    "Q11": [("Canon EOS 200D", 1), ("Sony 50mm Lens", 1), ("DJI Mini Drone", 0),
            ("Manfrotto Tripod", 1), ("Rode Wireless Mic", 1),
            ("Vintage Leica (Showcase)", 1), ("SD Card 128GB", 3)],
    "Q12": [("Canon EOS 200D", "Rode Wireless Mic", 2)],
}


def load_queries():
    """{'Q1': sql, ...} from queries.sql, keyed by the title's first word."""
    text = QUERIES_FILE.read_text(encoding="utf-8")
    return {title.split()[0]: sql for title, sql in split_statements(text)
            if title and title.startswith("Q")}


QUERIES = load_queries()


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    path = tmp_path_factory.mktemp("q") / "queries.db"
    create_database(path, out=lambda *_: None)
    conn = sqlite3.connect(path)
    yield conn
    conn.close()


def test_there_are_exactly_12_queries():
    assert sorted(QUERIES, key=lambda q: int(q[1:])) == [f"Q{n}" for n in range(1, 13)]


@pytest.mark.parametrize("name", list(EXPECTED))
def test_query_matches_expected_output(db, name):
    assert db.execute(QUERIES[name]).fetchall() == EXPECTED[name]
