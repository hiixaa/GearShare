"""Task 3.6: time the 12 queries on 100,000 rentals, before and after indexes.

    python -m sql.index_report             # build data/gearshare_big.db, measure, index, measure
    python -m sql.index_report --no-index  # only the 'before' measurements

Prints the timings of all 12 queries and EXPLAIN QUERY PLAN for the slowest
ones, before and after running sql/indexes.sql. Medians of several runs.
"""

import argparse
import random
import sqlite3
import statistics
import sys
import time
from datetime import date, timedelta
from pathlib import Path

from sql.run_sql import ROOT, split_statements
from sql.setup_db import SQL_DIR, create_database

BIG_DB = ROOT / "data" / "gearshare_big.db"
TODAY = date(2026, 11, 3)
N_CUSTOMERS, N_ITEMS, N_RENTALS = 1_000, 1_000, 100_000
RUNS = 5


def build_big_db(path, seed=7):
    """Starter data + 1,000 customers + 1,000 items + 100,000 rentals (~1% open)."""
    if path.exists():
        path.unlink()
    create_database(path, out=lambda *_: None)
    rng = random.Random(seed)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    tiers = ["Basic", "Plus", "Pro"]
    category_ids = [r[0] for r in conn.execute(
        "SELECT category_id FROM categories WHERE name <> 'Photography'")]
    with conn:   # one transaction for the bulk load: ~100x faster than autocommit
        conn.executemany(
            "INSERT INTO customers VALUES (?, ?, ?, ?)",
            [(f"C{i:05d}", f"Customer {i}", f"c{i}@example.com", tiers[i % 3])
             for i in range(100, 100 + N_CUSTOMERS)])
        conn.executemany(
            "INSERT INTO items VALUES (?, ?, ?, 'Equipment', ?, ?, ?)",
            [(str(3_000_000_000 + i), f"Item {i:04d}", rng.choice(category_ids),
              rng.randint(2, 3000), rng.randint(5, 2000) * 100, 50)
             for i in range(N_ITEMS)])
        customers = [r[0] for r in conn.execute("SELECT customer_id FROM customers")]
        skus = [r[0] for r in conn.execute("SELECT sku FROM items WHERE item_type <> 'Display'")]
        rows, fines = [], []
        for n in range(N_RENTALS):
            issue = TODAY - timedelta(days=rng.randint(0, 365))
            due = issue + timedelta(days=5)
            is_open = rng.random() < 0.01
            returned = None if is_open else min(TODAY, due + timedelta(days=rng.choice([0, 0, 0, 1, 3])))
            rental_id = f"RN{100_000 + n}"
            rows.append((rental_id, rng.choice(customers), rng.choice(skus),
                         issue.isoformat(), due.isoformat(),
                         returned.isoformat() if returned else None))
            if returned and returned > due:
                fines.append((rental_id, (returned - due).days * 50, rng.random() < 0.7))
        conn.executemany("INSERT INTO rentals (rental_id, customer_id, sku, issue_date,"
                         " due_date, return_date) VALUES (?, ?, ?, ?, ?, ?)", rows)
        conn.executemany("INSERT INTO fines VALUES (?, ?, ?)", fines)
    conn.execute("ANALYZE")   # give the query planner real statistics
    conn.close()


def load_queries():
    text = (SQL_DIR / "queries.sql").read_text(encoding="utf-8")
    return {title.split()[0]: sql for title, sql in split_statements(text)
            if title and title.startswith("Q")}


def median_ms(conn, sql):
    times = []
    for _ in range(RUNS):
        start = time.perf_counter()
        conn.execute(sql).fetchall()
        times.append((time.perf_counter() - start) * 1000)
    return statistics.median(times)


def plan(conn, sql):
    rows = conn.execute("EXPLAIN QUERY PLAN " + sql).fetchall()
    return "\n".join(f"{'  ' * _depth(rows, r)}{r[3]}" for r in rows)


def _depth(rows, row):
    parents = {r[0]: r[1] for r in rows}
    depth, parent = 0, row[1]
    while parent:
        depth += 1
        parent = parents.get(parent, 0)
    return depth


def measure(conn, queries, label):
    print(f"\n## {label}\n\n| query | median ms |\n|---|---|")
    times = {name: median_ms(conn, sql) for name, sql in queries.items()}
    for name, ms in times.items():
        print(f"| {name} | {ms:,.2f} |")
    return times


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-index", action="store_true")
    parser.add_argument("--explain", nargs="*", default=None,
                        help="queries to EXPLAIN (default: the 2 slowest)")
    args = parser.parse_args()

    print(f"Building {BIG_DB.name}: {N_RENTALS:,} rentals ...", file=sys.stderr)
    build_big_db(BIG_DB)
    queries = load_queries()
    conn = sqlite3.connect(BIG_DB)
    print(f"rentals: {conn.execute('SELECT COUNT(*) FROM rentals').fetchone()[0]:,}, "
          f"open: {conn.execute('SELECT COUNT(*) FROM rentals WHERE return_date IS NULL').fetchone()[0]:,}")

    before = measure(conn, queries, "Before indexes")
    targets = args.explain or sorted(before, key=before.get, reverse=True)[:2]
    for name in targets:
        print(f"\n### EXPLAIN QUERY PLAN {name} (before)\n```\n{plan(conn, queries[name])}\n```")
    if args.no_index:
        return

    conn.executescript((SQL_DIR / "indexes.sql").read_text(encoding="utf-8"))
    conn.execute("ANALYZE")
    after = measure(conn, queries, "After indexes (sql/indexes.sql)")
    for name in targets:
        print(f"\n### EXPLAIN QUERY PLAN {name} (after)\n```\n{plan(conn, queries[name])}\n```")
    print("\n| query | before ms | after ms | speed-up |\n|---|---|---|---|")
    for name in queries:
        print(f"| {name} | {before[name]:,.2f} | {after[name]:,.2f} | "
              f"{before[name] / after[name]:,.1f}x |")
    conn.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
