# Phase 2 Benchmark Report

Machine: Windows 11 laptop, Python 3.14. All times are in milliseconds, the
**median** of 7 runs measured with `time.perf_counter()`. Absolute numbers will
differ on another machine; what matters is the **shape** as n grows.

Reproduce:

```powershell
python benchmarks/benchmark_engine.py
```

The data comes from `benchmarks/generate_data.py`: for n items it creates
n/10 customers, n rentals (n/10 still open, half of those overdue) and a fine
on every 5th returned rental. It is loaded through the normal `load_data()`.

---

## 1. Engine operations (Task 2.1)

### 1.1 Predictions, written before measuring

n = items, R = all rentals (≈ n), F = fines, O = open rentals, k = results.

| Operation | Predicted time | Predicted space | Reasoning |
|---|---|---|---|
| `list_items` | O(n) | O(n) | Copies every item reference into a new list. |
| `search` | O(n · t) | O(k) | Checks every item's name and its t tags; returns only the matches. |
| `rent` | O(1) | O(1) | Customer and item are dict lookups, R8 is a set lookup. |
| `return_item` | O(R) | O(1) | Finds the rental by scanning the rentals list. |
| `overdue_report` | O(R + k log k) | O(k) | Scans every rental, then sorts the k overdue ones. |

### 1.2 Measured, Phase 1 engine (before)

| operation | n=1,000 | n=5,000 | n=10,000 | n=50,000 |
|---|---|---|---|---|
| `list_items` | 0.008 | 0.022 | 0.044 | 0.846 |
| `search` | 0.869 | 2.523 | 5.053 | 26.991 |
| `rent` | 0.255 | 0.444 | 0.827 | 4.832 |
| `return_item` | 0.051 | 0.101 | 0.181 | 1.313 |
| `overdue_report` | 0.160 | 0.532 | 1.253 | 7.115 |

### 1.3 Measured, after adding indexes (see DECISIONS D9)

| operation | n=1,000 | n=5,000 | n=10,000 | n=50,000 |
|---|---|---|---|---|
| `list_items` | 0.008 | 0.080 | 0.049 | 0.513 |
| `search` | 0.893 | 2.483 | 5.962 | 27.979 |
| `rent` | 0.018 | 0.030 | 0.009 | 0.011 |
| `return_item` | 0.010 | 0.015 | 0.004 | 0.004 |
| `overdue_report` | 0.075 | 0.284 | 0.563 | 4.128 |

### 1.4 Predicted vs measured, and the surprises

| Operation | Predicted | Measured before | Measured after |
|---|---|---|---|
| `list_items` | O(n) | O(n) | O(n) |
| `search` | O(n · t) | O(n) | O(n) |
| `rent` | O(1) | **O(R + F)** | O(1) |
| `return_item` | O(R) | O(R) | **O(1)** |
| `overdue_report` | O(R + k log k) | O(R + k log k) | O(O + k log k) |

**Surprise 1: `rent` was linear, not constant.** Every lookup in `rent()` is a
dict or set lookup, but check 4 (R4) calls `unpaid_fines()`, which scanned
*every* rental and *every* fine in the shop to add up one customer's fines. The
cost was hidden one call deeper. Indexing rentals by customer and fines by
rental made it O(k) in that customer's own history, and it now stays flat
at about 0.01 ms.

**Surprise 2: `return_item` became flat after one dict.** Searching the
rentals list was the whole cost: the open rental being returned is near the
end of the list, so the scan was a worst case every time. A dict of open
rentals by ID turns that into one hash lookup, and the time stopped depending
on n.

**Surprise 3: `overdue_report` only got about 1.7× faster, not 10×.** It now
scans only the open rentals (n/10 instead of n), but half of those are overdue,
and for each one it still computes days late and the fee, then sorts them. The
remaining cost is O(k log k) in the overdue rentals themselves, which no index
can remove, because the report has to show every one.

**Surprise 4: tiny timings are noisy.** `list_items` at 5,000 (0.080 ms) was
slower than at 10,000 (0.049 ms) in the second run. Below about 0.1 ms, other
things on the machine (garbage collection, the CPU changing speed) are as large
as the work itself. Only the jump to 50,000 (≈ 10× the time for 5× the
items) is a real signal, and it is still linear: the list copy outgrows the CPU
cache.

**Surprise 5: `search` is now the slowest operation by far.** It is O(n) by
design, because it must look at every name and tag. At 50,000 items it takes
about 28 ms, which a user would notice on every keystroke on the website.
Task 2.3's word-to-SKU index (stretch) is the fix.
