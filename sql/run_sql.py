"""Run a .sql file against the GearShare database and print every result.

    python -m sql.run_sql sql/schema.sql
    python -m sql.run_sql sql/queries.sql
    python -m sql.run_sql sql/queries.sql --db path/to/other.db

Statements run one at a time in autocommit mode, so BEGIN / COMMIT / ROLLBACK
written in the file behave exactly as written. A failing statement prints
'ERROR: ...' and the script carries on (like the sqlite3 shell), which the
transaction demo relies on.

For each SELECT, the first '-- ' comment line of the block above it is printed as a title.
"""

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "gearshare.db"


def split_statements(sql):
    """Yield (title, statement) pairs. A statement ends at a ';' that
    sqlite3.complete_statement() agrees is the end (not inside a string)."""
    title, buffer = None, ""
    for line in sql.splitlines(keepends=True):
        stripped = line.strip()
        if not buffer.strip() and stripped.startswith("--"):
            text = stripped.lstrip("-").strip()
            if text and title is None:      # first comment line = the title
                title = text
            continue
        if not buffer.strip() and not stripped:
            title = None                    # a blank line starts a new comment block
            continue
        buffer += line
        if sqlite3.complete_statement(buffer):
            yield title, buffer.strip()
            title, buffer = None, ""
    if buffer.strip():
        yield title, buffer.strip()


def format_rows(columns, rows):
    table = [columns] + [["" if v is None else str(v) for v in row] for row in rows]
    widths = [max(len(r[i]) for r in table) for i in range(len(columns))]
    lines = []
    for row in table:
        cells = [cell.ljust(widths[i]) if i < len(row) - 1 else cell
                 for i, cell in enumerate(row)]
        lines.append(" | ".join(cells))
    return "\n".join(lines)


def run(sql, conn, out=print):
    for title, statement in split_statements(sql):
        try:
            cursor = conn.execute(statement)
        except sqlite3.Error as e:
            out(f"ERROR: {e}")
            continue
        if cursor.description:                      # it returned rows
            columns = [d[0] for d in cursor.description]
            rows = cursor.fetchall()
            if title:
                out(title)
            out(format_rows(columns, rows))
            out("")


def connect(db_path):
    conn = sqlite3.connect(db_path, isolation_level=None)  # autocommit: SQL controls transactions
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sql_file")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    args = parser.parse_args()
    # Read the whole file first: if it can't be read, fail before touching the database.
    sql = Path(args.sql_file).read_text(encoding="utf-8")
    conn = connect(args.db)
    try:
        run(sql, conn)
    finally:
        conn.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
