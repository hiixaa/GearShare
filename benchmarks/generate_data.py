"""Generate a fake shop of any size as CSV files, then load it into GearShare.

    python benchmarks/generate_data.py 10000

Writes benchmarks/generated/n10000/{gear,customers,rentals,fines}.csv.
The data is random but seeded, so every run with the same n is identical.

Shape of the data for n items:
- n items with valid 10-digit SKUs (2000000000 + i), 1-3 units each
- n // 10 customers, tiers cycling Basic / Plus / Pro
- n rentals: n // 10 still open (half of them overdue), the rest returned
- a fine on every 5th returned rental, most of them paid
"""

import csv
import random
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from gearshare import GearShare  # noqa: E402  (import after sys.path setup)

GENERATED_DIR = Path(__file__).resolve().parent / "generated"
TODAY = date(2026, 11, 3)

BRANDS = ["Canon", "Sony", "Nikon", "DJI", "Rode", "Manfrotto", "Fujifilm",
          "Panasonic", "GoPro", "Sennheiser", "Godox", "Zhiyun"]
# (category, parent, item_type, product words, tags)
KINDS = [
    ("Cameras", "Photography", "Equipment", ["EOS", "Alpha", "Z", "X-T"], ["photo", "dslr"]),
    ("Lenses", "Photography", "Equipment", ["50mm Lens", "85mm Lens", "Zoom Lens"], ["photo", "lens"]),
    ("Drones", "", "Equipment", ["Mini Drone", "Air Drone"], ["video", "aerial"]),
    ("Tripods", "", "Equipment", ["Tripod", "Monopod"], ["support"]),
    ("Audio", "", "Equipment", ["Wireless Mic", "Shotgun Mic"], ["audio", "interview"]),
    ("Accessories", "", "Accessory", ["SD Card", "Battery"], ["storage", "power"]),
    ("Showcase", "", "Display", ["Vintage Camera (Showcase)"], ["display"]),
]
KIND_WEIGHTS = [25, 20, 10, 15, 15, 13, 2]  # roughly how a real shop's stock looks
TIERS = ["Basic", "Plus", "Pro"]


def generate(n, folder=None, seed=42):
    """Write the four CSV files for a shop with n items. Returns the folder."""
    rng = random.Random(seed)
    folder = Path(folder or GENERATED_DIR / f"n{n}")
    folder.mkdir(parents=True, exist_ok=True)

    # --- items ----------------------------------------------------------------
    items = []
    for i in range(n):
        category, parent, item_type, words, tags = rng.choices(KINDS, KIND_WEIGHTS)[0]
        items.append({
            "sku": str(2_000_000_000 + i),
            "name": f"{rng.choice(BRANDS)} {rng.choice(words)} {i:05d}",
            "tags": ";".join(rng.sample(tags, k=len(tags))),
            "category": category,
            "parent_category": parent,
            "item_type": item_type,
            "weight_g": rng.randint(2, 3000),
            "price": rng.randint(5, 2000) * 100,
            "total_units": rng.randint(1, 3),
        })
    rentable = [it for it in items if it["item_type"] != "Display"]

    # --- customers ------------------------------------------------------------
    n_customers = max(10, n // 10)
    customers = [{
        "customer_id": f"C{i:05d}",
        "name": f"Customer {i:05d}",
        "email": f"customer{i:05d}@example.com",
        "membership_type": TIERS[i % 3],
    } for i in range(1, n_customers + 1)]

    # --- rentals ----------------------------------------------------------------
    rentals = []
    # Open rentals: each on a different item (so units never go below 0),
    # at most 2 per customer (the Basic limit), so the data obeys R3 and R8.
    n_open = n // 10
    for k, item in enumerate(rng.sample(rentable, k=min(n_open, len(rentable)))):
        overdue = k % 2 == 0
        issue = TODAY - timedelta(days=rng.randint(10, 40) if overdue else rng.randint(0, 1))
        due = issue + timedelta(days=2 if item["item_type"] == "Accessory" else 3)
        rentals.append([customers[k // 2 % n_customers]["customer_id"], item["sku"],
                        issue, due, None])
    # Returned rentals: history from the past year.
    while len(rentals) < n:
        item = rng.choice(rentable)
        issue = TODAY - timedelta(days=rng.randint(30, 365))
        due = issue + timedelta(days=3)
        returned = due + timedelta(days=rng.choice([0, 0, 0, 1, 2, 5]))
        rentals.append([rng.choice(customers)["customer_id"], item["sku"],
                        issue, due, returned])

    rental_rows = [{
        "rental_id": f"RN{i:03d}",
        "customer_id": cid, "sku": sku,
        "issue_date": issue, "due_date": due,
        "return_date": returned or "",
    } for i, (cid, sku, issue, due, returned) in enumerate(rentals, start=1)]

    # --- fines: every 5th returned rental, 1 in 4 of them unpaid --------------------
    returned_ids = [r["rental_id"] for r in rental_rows if r["return_date"]]
    fines = [{
        "rental_id": rid,
        "amount": rng.choice([50, 100, 150, 300]),
        "paid": "no" if k % 4 == 0 else "yes",
    } for k, rid in enumerate(returned_ids[::5])]

    _write(folder / "gear.csv", items)
    _write(folder / "customers.csv", customers)
    _write(folder / "rentals.csv", rental_rows)
    _write(folder / "fines.csv", fines)
    return folder


def _write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def load(n, seed=42):
    """Generate (if needed) and load a shop with n items."""
    shop = GearShare()
    shop.load_data(generate(n, seed=seed))
    return shop


if __name__ == "__main__":
    size = int(sys.argv[1]) if len(sys.argv) > 1 else 10_000
    shop = GearShare()
    counts = shop.load_data(generate(size))
    print(f"Loaded {counts['items']} items, {counts['customers']} customers, "
          f"{counts['rentals']} rentals, {counts['fines']} fines.")
