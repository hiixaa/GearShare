"""Task 2.4: list.pop(0) vs deque.popleft() on 100,000 entries.

    python benchmarks/benchmark_queue.py

Empties a queue of N customer IDs from the front, the way the waiting
list serves people (R7). Median of 5 runs.
"""

import statistics
import time
from collections import deque

N = 100_000
RUNS = 5


def drain_list(n):
    queue = [f"C{i:06d}" for i in range(n)]
    start = time.perf_counter()
    while queue:
        queue.pop(0)          # every remaining element shifts one step left
    return (time.perf_counter() - start) * 1000


def drain_deque(n):
    queue = deque(f"C{i:06d}" for i in range(n))
    start = time.perf_counter()
    while queue:
        queue.popleft()       # just moves the left index
    return (time.perf_counter() - start) * 1000


def main():
    print("| n | list.pop(0) ms | deque.popleft() ms | ratio |")
    print("|---|---|---|---|")
    for n in (10_000, 50_000, N):
        lst = statistics.median(drain_list(n) for _ in range(RUNS))
        dq = statistics.median(drain_deque(n) for _ in range(RUNS))
        print(f"| {n:,} | {lst:,.2f} | {dq:,.2f} | {lst / dq:,.0f}x |")
    print(f"\nTime to remove ALL n entries from the front, median of {RUNS} runs.")


if __name__ == "__main__":
    main()
