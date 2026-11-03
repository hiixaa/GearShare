"""Task 3.8: the SQL injection experiment. THROWAWAY DEMO, never imported.

    python -m sql.injection_demo

search_unsafe() is DELIBERATELY WRONG: it pastes the user's text into the SQL
with an f-string. It is the only place in the project that builds SQL by
string formatting, and it exists to show why nothing else does.
"""

import sqlite3
import sys
import tempfile
from pathlib import Path

from sql.setup_db import create_database


def search_unsafe(conn, text):
    """DON'T DO THIS. The text becomes part of the SQL code itself."""
    sql = f"SELECT name FROM items WHERE name LIKE '%{text}%'"
    return sql, conn.execute(sql).fetchall()


def search_safe(conn, text):
    """The fix: a ? placeholder. The text is sent separately, as DATA only."""
    sql = "SELECT name FROM items WHERE name LIKE '%' || ? || '%'"
    return sql, conn.execute(sql, (text,)).fetchall()


def rows(n):
    return f"{n} row" if n == 1 else f"{n} rows"


def main():
    attack = "' OR '1'='1"
    with tempfile.TemporaryDirectory() as folder:
        db = Path(folder) / "demo.db"
        create_database(db, out=lambda *_: None)      # the 7 starter items
        conn = sqlite3.connect(db)
        count = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        print(f"({count} items in the table)\n")

        calls = [("search_unsafe", search_unsafe, "Drone"),
                 ("search_unsafe", search_unsafe, attack),
                 ("search_safe", search_safe, attack),
                 ("search_safe", search_safe, "Drone")]
        width = max(len(f'{name}("{text}")') for name, _, text in calls) + 3
        evidence = []
        for name, func, text in calls:
            sql, found = func(conn, text)
            note = "   (every item leaked)" if len(found) == count else ""
            print(f"{f'{name}({chr(34)}{text}{chr(34)})':<{width}}-> {rows(len(found)):<8}{note}".rstrip())
            evidence.append((name, text, sql, found))

        print("\nWhat the database actually received:")
        for name, text, sql, found in evidence:
            print(f"\n{name}({text!r})")
            print(f"  SQL : {sql}")
            if name == "search_safe":
                print(f"  data: {text!r}   <- sent separately, never parsed as SQL")
            print(f"  rows: {[r[0] for r in found]}")
        conn.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
