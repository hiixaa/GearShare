"""Task 2.2: time the hand-written searches and sorts on item names / SKUs.

    python benchmarks/benchmark_sorts.py

Takes about 1-2 minutes: bubble sort on 10,000 names is slow on purpose.
Medians of several runs, as in 2.1.
"""

import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dsa.search import binary_search, linear_search  # noqa: E402
from dsa.sorting import bubble_sort, insertion_sort, selection_sort  # noqa: E402
from generate_data import load  # noqa: E402

SIZES = [1_000, 5_000, 10_000]
SEARCH_RUNS = 101   # searches take microseconds, so many runs are cheap
SORT_RUNS = 3       # hand sorts take seconds at 10k


def median_ms(func, runs):
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        func()
        times.append((time.perf_counter() - start) * 1000)
    return statistics.median(times)


def measure(n):
    items = load(n).list_items()
    names = [item.name for item in items]          # file order: not sorted
    skus = sorted(item.sku for item in items)
    last_name, last_sku = names[-1], skus[-1]      # worst case for linear search
    return {
        "linear_ms": median_ms(lambda: linear_search(names, last_name), SEARCH_RUNS),
        "binary_ms": median_ms(lambda: binary_search(skus, last_sku), SEARCH_RUNS),
        "sorted_key_ms": median_ms(lambda: sorted(names, key=str.lower), SORT_RUNS),
        "insertion_ms": median_ms(lambda: insertion_sort(names), SORT_RUNS),
        "selection_ms": median_ms(lambda: selection_sort(names), SORT_RUNS),
        "bubble_ms": median_ms(lambda: bubble_sort(names), SORT_RUNS),
    }


def main():
    results = {}
    for n in SIZES:
        print(f"measuring n={n:,} ...", file=sys.stderr)
        results[n] = measure(n)
    columns = list(results[SIZES[0]])
    print("| n | " + " | ".join(columns) + " |")
    print("|" + "---|" * (len(columns) + 1))
    for n in SIZES:
        cells = " | ".join(f"{results[n][c]:,.3f}" for c in columns)
        print(f"| {n:,} | {cells} |")
    print(f"\nms; searches: median of {SEARCH_RUNS} runs, sorts: median of {SORT_RUNS}.")


if __name__ == "__main__":
    main()
