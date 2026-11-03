"""Task 2.1: time the five engine operations as the shop grows.

    python benchmarks/benchmark_engine.py

Each operation is timed RUNS times with time.perf_counter() and the MEDIAN is
reported (a single run is noise: other programs, garbage collection, ...).
"""

import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_data import TODAY, load  # noqa: E402

SIZES = [1_000, 5_000, 10_000, 50_000]
RUNS = 7


def median_ms(func, runs=RUNS):
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        func()
        times.append((time.perf_counter() - start) * 1000)
    return statistics.median(times)


def pick_renter_and_item(shop):
    """A customer who may rent (no open rentals, fines <= 500) and a free item."""
    customer = next(c for c in shop.customers.values()
                    if shop.active_count(c.customer_id) == 0
                    and shop.unpaid_fines(c.customer_id) <= 500)
    item = next(i for i in shop.items.values()
                if i.is_rentable() and i.can_extend() and i.available_units > 0)
    return customer.customer_id, item.sku


def measure(n):
    shop = load(n)
    customer_id, sku = pick_renter_and_item(shop)

    rent_times, return_times = [], []
    for _ in range(RUNS):  # rent then return, so every run starts from the same state
        start = time.perf_counter()
        rental = shop.rent(customer_id, sku, TODAY)
        rent_times.append((time.perf_counter() - start) * 1000)

        start = time.perf_counter()
        shop.return_item(rental.rental_id, TODAY)
        return_times.append((time.perf_counter() - start) * 1000)

    return {
        "list_items": median_ms(shop.list_items),
        "search": median_ms(lambda: shop.search("zzz")),  # no match: worst case
        "rent": statistics.median(rent_times),
        "return_item": statistics.median(return_times),
        "overdue_report": median_ms(lambda: shop.overdue_report(TODAY)),
    }


def main():
    results = {n: measure(n) for n in SIZES}
    operations = list(results[SIZES[0]])
    header = "| operation | " + " | ".join(f"n={n:,}" for n in SIZES) + " |"
    print(header)
    print("|" + "---|" * (len(SIZES) + 1))
    for op in operations:
        cells = " | ".join(f"{results[n][op]:.3f}" for n in SIZES)
        print(f"| `{op}` | {cells} |")
    print(f"\nTimes in ms, median of {RUNS} runs.")


if __name__ == "__main__":
    main()
