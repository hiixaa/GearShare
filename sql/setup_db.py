"""Create a fresh GearShare database: schema.sql, seed.sql, then indexes.sql.

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


def create_database(db_path, out=print, with_indexes=True):
    """Build the schema, load the starter data and (by default) add the indexes.

    with_indexes=False is for the index report, which must measure the
    database BEFORE indexes.sql and then add them itself.
    """
    names = ["schema.sql", "seed.sql"] + (["indexes.sql"] if with_indexes else [])
    scripts = [(SQL_DIR / name).read_text(encoding="utf-8") for name in names]
    conn = connect(db_path)
    try:
        for script in scripts:
            run(script, conn, out)
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
