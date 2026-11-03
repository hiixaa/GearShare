"""Import a gear CSV into a new shop, skipping duplicate SKUs (Task 2.3).

    python import_gear.py gear_with_duplicate.csv

A bare file name is also looked for in the data/ folder.
"""

import sys
from pathlib import Path

from dsa.hashing import DATA_DIR, import_gear
from gearshare import GearShare


def main(argv):
    if len(argv) != 2:
        print("Usage: python import_gear.py <gear.csv>")
        return 1
    path = Path(argv[1])
    if not path.exists() and (DATA_DIR / path).exists():
        path = DATA_DIR / path
    if not path.exists():
        print(f"File not found: {argv[1]}")
        return 1

    rows, added, duplicates = import_gear(path, GearShare())
    for line_no, sku, first_name in duplicates:
        print(f"Line {line_no}: duplicate SKU {sku} "
              f"(already used by '{first_name}'), skipped.")
    skipped = len(duplicates)
    print(f"Imported {rows} rows: {added} added, "
          f"{skipped} duplicate{'' if skipped == 1 else 's'} skipped.")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv))
