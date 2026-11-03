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

---

## 2. Searching and sorting (Task 2.2)

Reproduce: `python benchmarks/benchmark_sorts.py` (about 1 minute).
Searches use the worst case (the target is the last element) and are the
median of 101 runs. Sorts sort the item names in file order and are the median of 3 runs.

| n | linear_ms | binary_ms | sorted_key_ms | insertion_ms | selection_ms | bubble_ms |
|---|---|---|---|---|---|---|
| 1,000 | 0.039 | 0.001 | 0.159 | 33.568 | 41.035 | 60.632 |
| 5,000 | 0.234 | 0.002 | 1.325 | 762.705 | 1,035.296 | 1,696.167 |
| 10,000 | 0.377 | 0.002 | 1.926 | 3,065.617 | 4,224.761 | 6,855.747 |

### 2.1 The shape: which column does what when n doubles (5k → 10k)

| Column | 5k → 10k | Big-O | Why |
|---|---|---|---|
| `binary_ms` | 0.002 → 0.002 (barely moves) | O(log n) | Doubling n adds just **one** more halving step (≈ 13 → 14 comparisons). |
| `linear_ms` | 0.23 → 0.38 (≈ 2×) | O(n) | Twice as many elements to look at in the worst case. |
| `sorted_key_ms` | 1.3 → 1.9 (≈ 2×) | O(n log n) | Python's Timsort, written in C, plus one `key()` call per element. |
| `insertion_ms` | 763 → 3,066 (**4.0×**) | O(n²) | Each new element is shifted past about half of those before it: n²/4 moves. |
| `selection_ms` | 1,035 → 4,225 (**4.1×**) | O(n²) | Always n²/2 comparisons, whatever the input. |
| `bubble_ms` | 1,696 → 6,856 (**4.0×**) | O(n²) | n²/2 comparisons *and* a swap for each out-of-order pair. |

**Surprise 1: all three hand sorts are O(n²), but bubble is about 2× slower than insertion.**
Big-O hides the constant. Bubble does a full three-step swap for every
out-of-order neighbour, while insertion does a single shift and stops early
once the element is in place. The ranking (insertion < selection < bubble) held
at every size.

**Surprise 2: `sorted()` is about 1,600× faster than insertion sort at 10k.**
Part of that is O(n log n) vs O(n²) (≈ 13 vs 10,000 steps per element at 10k),
and part is that Timsort runs in C, while our loops run in the Python
interpreter. The algorithm explains why the gap *grows*; C explains why it was
already large at n = 1,000.

### 2.2 Is sorting first worth it for binary search? (think-about question 1)

At 10k: sorting once costs ≈ 1.9 ms. Each binary search saves
0.377 − 0.002 ≈ 0.375 ms compared with a linear search. Break-even:
1.9 / 0.375 ≈ **5 searches**. For a single search, linear wins. From about
the 6th search on the same (unchanged) list, sorting first pays off, and the
shop's catalogue is searched thousands of times between changes.

### 2.3 Catalogue sort

Top-level category A-Z, then weight heaviest first, then name A-Z, in one
`sorted()` call with the key `(top_category, -weight_g, name)`. Negating the
weight turns "descending" into "ascending", so one key does all three parts.
See DECISIONS D10.

---

## 3. Hashing (Task 2.3)

### 3.1 Big-O of each hashing task

| Task | With hashing | Without hashing | Structure |
|---|---|---|---|
| Duplicate SKUs on import | O(n) | O(n²): compare each row with every earlier row | `set` of SKUs seen |
| Group by tag | O(total tags) | O(tags × n): one scan per tag | `dict` tag → list |
| Most rented | O(R + m log m), m = distinct items | O(R × m): count each item separately | `dict` SKU → count |
| Packing challenge (two-sum) | O(n), one pass | O(n²): try every pair | `dict` weight → item |
| Word search (stretch) | O(q + matches) per query, after an O(words) build | O(n) per query | `dict` word → `set` of SKUs |

### 3.2 Stretch: word-to-SKU index vs linear search

Reproduce: `python benchmarks/benchmark_word_index.py`. Query `"zhiyun drone"` (both words must match).

| n | build_index_ms | linear_search_ms | index_search_ms | matches |
|---|---|---|---|---|
| 1,000 | 2.585 | 0.524 | 0.0075 | 11 |
| 5,000 | 16.825 | 2.514 | 0.0058 | 38 |
| 10,000 | 37.170 | 5.064 | 0.0107 | 80 |
| 50,000 | 184.369 | 28.212 | 0.0990 | 394 |

**Surprise: the index search still grows a little (0.006 → 0.099 ms).**
The two dict lookups are O(1), but intersecting the two SKU sets and sorting
the result are O(matches), and there are 394 matches at 50k against 11 at 1k.
The cost now follows the size of the **answer**, not the size of the **shop**,
which is exactly what an index is for.

**The trade-off:** building the index costs about 184 ms at 50k (≈ 7 linear
searches), plus memory for one set entry per word per item. It pays off for a
catalogue that is searched far more often than it changes. Every `add_item`
would also have to update the index. See DECISIONS D12.

---

## 4. Stacks, queues and linked lists (Task 2.4)

### 4.1 `list.pop(0)` vs `deque.popleft()`

Reproduce: `python benchmarks/benchmark_queue.py`. Time to empty a queue of n
customer IDs from the front (the way the waiting list serves people), median of 5 runs.

| n | list.pop(0) ms | deque.popleft() ms | ratio |
|---|---|---|---|
| 10,000 | 4.83 | 0.35 | 14x |
| 50,000 | 164.81 | 1.46 | 113x |
| 100,000 | 557.06 | 3.59 | 155x |

**Why (think-about question 3):** a Python `list` is one contiguous array.
`pop(0)` removes the first slot, then **shifts every remaining element one
step left**, which is O(n) per pop, so draining the whole queue is O(n²). Doubling
n from 50k to 100k multiplied the time by about 3.4, heading towards 4×. A
`deque` is a doubly linked list of fixed-size blocks, with an index for each
end. `popleft()` just moves the left index (and occasionally frees an empty
block), which is O(1) per pop and O(n) to drain. Doubling n doubled its time
(1.46 → 3.59 ms, roughly 2×).

### 4.2 Big-O of the new structures

| Operation | Structure | Time | Space |
|---|---|---|---|
| Push / pop undo entry | `deque(maxlen=20)` used as a stack | O(1) | O(20) at most |
| Undo a rent | + `list.remove` from the rentals history | O(R) | O(1) |
| Undo a return | lookup in the customer's own rentals | O(k) | O(1) |
| Join waiting list / serve next | `deque.append` / `popleft` | O(1) | O(w) |
| Put a served customer back at the front | `deque.appendleft` | O(1) | — |
| History: insert at head | linked list | O(1) | O(1) per node |
| History: traverse / delete / reverse / 2nd from end | linked list | O(n) | O(1) |

**Surprise: undoing a rent is O(R), not O(1).** Everything else in undo is a
dict or set operation, but removing the rental from the full `rentals` history
list is a scan. It is still fast in practice, because the rental being undone
is near the end of the list, but `list.remove` searches from the front. A
dict-based history (as in Phase 3's database, with a primary key) removes it in O(1).

---

## 5. Recursion (Task 2.5)

Reproduce the sample: `python -m dsa.categories`.

### 5.1 Recursive vs iterative

| Function | Recursive Big-O | Recursion depth | Iterative version |
|---|---|---|---|
| `factorial(n)` | O(n) time | n | a loop, O(1) space |
| `fibonacci(n)` | **O(2ⁿ)** time | n | `fibonacci_iterative`: O(n) time, O(1) space |
| `sum_of_digits(n)` | O(digits) | digits (≈ 10 for any int you'd use) | a loop |
| `tree_lines` / `total_items` / `path_to` | O(nodes) | tree height | explicit stack: `tree_lines_iterative`, `total_items_iterative`, `path_to_iterative` |

Naive Fibonacci measured on this machine: n = 20 → 3.5 ms, 25 → 23 ms,
30 → 225 ms (about ×10 for every +5, since 1.6⁵ ≈ 11). The iterative version stayed under 0.1 ms.

### 5.2 Depth 10,000: what `sys.setrecursionlimit` changes and doesn't (measured)

A chain of 10,000 categories, each the only child of the previous one:

| Function | Limit | Depth | Result |
|---|---|---|---|
| `path_to` (plain Python calls) | 1,000 (default) | 10,000 | `RecursionError: maximum recursion depth exceeded` |
| `path_to` | 20,000 | 10,000 | works |
| `path_to` | 1,000,000 | 200,000 | works, but slowly (it copies the path at every level: O(depth²)) |
| `total_items` (recursion **through** C's `sum()`) | 20,000 | 10,000 | `RecursionError: Stack overflow (used 2914 kB)` |
| any `*_iterative` | 1,000 (default) | 10,000 | works |

**What `setrecursionlimit` changes:** only Python's own safety counter, the
number of Python frames it allows before raising `RecursionError`.

**What it does not fix:**
1. The real **C stack** of the process (about 1-8 MB, set by the operating
   system). Python 3.14 runs plain Python-to-Python calls without using the
   C stack, so `path_to` survived once the counter was raised. But
   `total_items` calls itself *through* `sum()` and a generator, which are C
   code, so every level also takes C stack. It overflowed at depth 10,000
   even with the limit at 20,000. On older Pythons, or in other code paths,
   this is a hard crash.
2. Speed and memory: every frame still costs memory, and a deep recursion
   that copies data (like `path_to`'s list) gets slower with each level.

**Which is clearer?** The recursive versions. `path_to` reads like its
definition: "the path to X is my name plus my child's path to X". The
iterative version has to carry the path on its own stack.
**Which at depth 10,000?** The iterative one. Its only limit is memory.

### 5.3 Where recursion is the wrong choice (think-about question 4)

- **`fibonacci`**: the worst choice. Two calls per call means the same values
  are recomputed exponentially often (`fibonacci(30)` makes about 1.6 million
  calls to produce one number). Use the loop, or memoisation.
- **`factorial`**: works, but the depth equals n, so `factorial(5000)` fails
  at the default limit, while a loop never would. Nothing is gained by recursion.
- **`sum_of_digits`** and the **category tree**: good fits. The depth is tiny
  (number of digits, tree height ≈ 3), and the tree is recursive by nature,
  since every category is a smaller tree.

---

## 6. Conclusions

1. **Measure before optimising.** The biggest slowdown (`rent`, 2.1) was in
   a method that *looked* O(1). Only the numbers showed it.
2. **Hashing turned most O(n) and O(n²) work into O(1) lookups:** indexes for
   rent/return, sets for duplicates, a dict for two-sum, and the word index for search.
3. **The right container matters more than clever code:** `deque.popleft()`
   vs `list.pop(0)` was 155× at 100k, with the same one-line call.
4. **Big-O hides constants:** all three hand sorts are O(n²), but bubble was
   2× slower than insertion, and Python's C-coded `sorted()` was about 1,600× faster at 10k.
5. **Recursion is for problems that are naturally recursive and shallow.**
   For deep or repetitive ones, use a loop or an explicit stack.
