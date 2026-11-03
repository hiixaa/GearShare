"""Task 3.1: join the four starter CSVs into ONE flat file, one row per rental.

    python -m sql.build_flat

Writes data/gearshare_flat.csv. This is the deliberately un-normalised
"paper register" that the normalisation write-up (docs/normalisation.md)
starts from.
"""

import csv
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

COLUMNS = ["rental_id", "customer_name", "email", "tier", "item_name", "tags",
           "sku", "category", "parent_category", "weight_g", "price",
           "issue_date", "due_date", "return_date", "fine", "fine_paid"]


def read(name, key):
    with open(DATA / name, newline="", encoding="utf-8") as f:
        return {row[key]: row for row in csv.DictReader(f)}


def main():
    gear = read("gear.csv", "sku")
    customers = read("customers.csv", "customer_id")
    fines = read("fines.csv", "rental_id")

    rows = []
    with open(DATA / "rentals.csv", newline="", encoding="utf-8") as f:
        for rental in csv.DictReader(f):
            customer = customers[rental["customer_id"]]
            item = gear[rental["sku"]]
            fine = fines.get(rental["rental_id"], {})
            rows.append({
                "rental_id": rental["rental_id"],
                "customer_name": customer["name"],
                "email": customer["email"],
                "tier": customer["membership_type"],
                "item_name": item["name"],
                "tags": item["tags"],                 # 'photo;dslr' in ONE cell
                "sku": item["sku"],
                "category": item["category"],
                "parent_category": item["parent_category"],
                "weight_g": item["weight_g"],
                "price": item["price"],
                "issue_date": rental["issue_date"],
                "due_date": rental["due_date"],
                "return_date": rental["return_date"],
                "fine": fine.get("amount", ""),
                "fine_paid": fine.get("paid", ""),
            })

    with open(DATA / "gearshare_flat.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to data/gearshare_flat.csv")


if __name__ == "__main__":
    main()
