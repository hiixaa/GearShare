"""Create a fresh GearShare database: schema.sql, then seed.sql.

    python -m sql.setup_db                      # -> data/gearshare.db
    python -m sql.setup_db --db other.db

Run as a module (-m): on this laptop a script started as `python file.py`
may not read .sql files (DECISIONS D22).
"""

import argparse
import sys
from pathlib import Path

from sql.run_sql import DEFAULT_DB, connect, run

SQL_DIR = Path(__file__).resolve().parent


def create_database(db_path, out=print):
    """Build the schema and load the starter data into db_path."""
    schema = (SQL_DIR / "schema.sql").read_text(encoding="utf-8")
    seed = (SQL_DIR / "seed.sql").read_text(encoding="utf-8")
    conn = connect(db_path)
    try:
        run(schema, conn, out)
        run(seed, conn, out)
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Create and seed the GearShare database.")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    args = parser.parse_args()
    create_database(args.db)
    print(f"Database ready: {args.db}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
