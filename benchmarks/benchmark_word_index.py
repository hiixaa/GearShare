"""Task 2.3 stretch: linear search vs the word-to-SKU index.

    python benchmarks/benchmark_word_index.py
"""

import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dsa.hashing import WordIndex  # noqa: E402
from generate_data import load  # noqa: E402

SIZES = [1_000, 5_000, 10_000, 50_000]
RUNS = 51
QUERY = "zhiyun drone"   # two words: brand AND product


def median_ms(func, runs=RUNS):
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        func()
        times.append((time.perf_counter() - start) * 1000)
    return statistics.median(times)


def main():
    print("| n | build_index_ms | linear_search_ms | index_search_ms | matches |")
    print("|---|---|---|---|---|")
    for n in SIZES:
        shop = load(n)
        items = shop.list_items()
        build = median_ms(lambda: WordIndex(items), runs=5)
        index = WordIndex(items)
        # The engine's search matches one phrase; for two words, filter twice.
        linear = median_ms(lambda: [i for i in shop.search("zhiyun")
                                    if "drone" in i.name.lower()])
        indexed = median_ms(lambda: index.search(QUERY))
        print(f"| {n:,} | {build:.3f} | {linear:.3f} | {indexed:.4f} | "
              f"{len(index.search(QUERY))} |")
    print(f"\nms, median of {RUNS} runs (build: 5). Query: '{QUERY}'.")


if __name__ == "__main__":
    main()
