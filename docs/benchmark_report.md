# Phase 2 Benchmark Report

I measured everything on my Windows 11 laptop with Python 3.14. All times are
in milliseconds, using `time.perf_counter()`, and each number is the **median**
of several runs, because a single run is mostly noise. Your numbers will be
different. What matters is how the times change as n grows.

The test data comes from `benchmarks/generate_data.py`. For n items it makes
n/10 customers and n rentals (n/10 of them still open, and half of those
overdue), with a fine on every 5th returned rental. It's loaded through the
normal `load_data()`, just like the real data.

---

## 1. Engine operations (Task 2.1)

To reproduce: `python benchmarks/benchmark_engine.py`

### My predictions (written before measuring)

n = items, R = all rentals (about n), F = fines, O = open rentals, k = results.

| Operation | Predicted time | Predicted space | My reasoning |
|---|---|---|---|
| `list_items` | O(n) | O(n) | It copies every item into a new list. |
| `search` | O(n · t) | O(k) | It checks every item's name and its t tags, and keeps only the matches. |
| `rent` | O(1) | O(1) | The customer and item are dict lookups, and R8 is a set lookup. |
| `return_item` | O(R) | O(1) | It finds the rental by scanning the rentals list. |
| `overdue_report` | O(R + k log k) | O(k) | It looks at every rental, then sorts the k overdue ones. |

### Measured with the Phase 1 engine

| operation | n=1,000 | n=5,000 | n=10,000 | n=50,000 |
|---|---|---|---|---|
| `list_items` | 0.008 | 0.022 | 0.044 | 0.846 |
| `search` | 0.869 | 2.523 | 5.053 | 26.991 |
| `rent` | 0.255 | 0.444 | 0.827 | 4.832 |
| `return_item` | 0.051 | 0.101 | 0.181 | 1.313 |
| `overdue_report` | 0.160 | 0.532 | 1.253 | 7.115 |

### Measured after adding indexes (DECISIONS D9)

| operation | n=1,000 | n=5,000 | n=10,000 | n=50,000 |
|---|---|---|---|---|
| `list_items` | 0.008 | 0.080 | 0.049 | 0.513 |
| `search` | 0.893 | 2.483 | 5.962 | 27.979 |
| `rent` | 0.018 | 0.030 | 0.009 | 0.011 |
| `return_item` | 0.010 | 0.015 | 0.004 | 0.004 |
| `overdue_report` | 0.075 | 0.284 | 0.563 | 4.128 |

### Prediction vs reality

| Operation | Predicted | Measured before | Measured after |
|---|---|---|---|
| `list_items` | O(n) | O(n) | O(n) |
| `search` | O(n · t) | O(n) | O(n) |
| `rent` | O(1) | **O(R + F)** | O(1) |
| `return_item` | O(R) | O(R) | **O(1)** |
| `overdue_report` | O(R + k log k) | O(R + k log k) | O(O + k log k) |

### What surprised me

**`rent` was linear, not constant.** Every lookup inside `rent()` is a dict or
set lookup, but the R4 check calls `unpaid_fines()`, which went through every
rental and every fine in the shop just to add up one customer's fines. The cost
was hidden one function call deeper. Indexing rentals by customer and fines by
rental made it depend only on that customer's own history, and it now stays at
about 0.01 ms however big the shop gets.

**One dict made `return_item` flat.** Scanning the rentals list was the entire
cost, and the rental being returned is near the end of the list, so every scan
was the worst case. A dict of open rentals by ID turns that into a single lookup,
and the time no longer depends on n.

**`overdue_report` only got about 1.7× faster, not 10×.** It now looks only at
open rentals (n/10 instead of n), but half of those are overdue, and for each
one it still works out the days late and the fee, then sorts them. That
remaining work is about the overdue rentals themselves, and no index can remove
it, because the report has to show every one.

**Tiny timings are noisy.** In the second run, `list_items` took longer at 5,000
items (0.080 ms) than at 10,000 (0.049 ms). Below about 0.1 ms, background
things like garbage collection and the CPU changing speed are as big as the work
being measured. Only the jump at 50,000 (about 10× the time for 5× the items) is
a real signal, and that's still linear: the copied list just stops fitting in
the CPU cache.

**`search` is now by far the slowest operation.** It's O(n) by design, because
it has to look at every name and tag. At 50,000 items it takes about 28 ms, which
you'd notice on every keystroke on a website. The word index in Task 2.3 is the
fix.

---

## 2. Searching and sorting (Task 2.2)

To reproduce: `python benchmarks/benchmark_sorts.py` (it takes about a minute).
Searches use the worst case (the item I'm looking for is the last one), median
of 101 runs. Sorts sort the item names in file order, median of 3 runs.

| n | linear_ms | binary_ms | sorted_key_ms | insertion_ms | selection_ms | bubble_ms |
|---|---|---|---|---|---|---|
| 1,000 | 0.039 | 0.001 | 0.159 | 33.568 | 41.035 | 60.632 |
| 5,000 | 0.234 | 0.002 | 1.325 | 762.705 | 1,035.296 | 1,696.167 |
| 10,000 | 0.377 | 0.002 | 1.926 | 3,065.617 | 4,224.761 | 6,855.747 |

### What happens when n doubles (5k → 10k)

| Column | 5k → 10k | Big-O | Why |
|---|---|---|---|
| `binary_ms` | 0.002 → 0.002 (barely moves) | O(log n) | Doubling n only adds one more halving step (about 13 → 14 comparisons). |
| `linear_ms` | 0.23 → 0.38 (about 2×) | O(n) | Twice as many items to check in the worst case. |
| `sorted_key_ms` | 1.3 → 1.9 (about 2×) | O(n log n) | Python's built-in Timsort, written in C. |
| `insertion_ms` | 763 → 3,066 (4.0×) | O(n²) | Each new name gets shifted past about half of the ones before it. |
| `selection_ms` | 1,035 → 4,225 (4.1×) | O(n²) | Always n²/2 comparisons, whatever the input. |
| `bubble_ms` | 1,696 → 6,856 (4.0×) | O(n²) | n²/2 comparisons, plus a swap for every out-of-order pair. |

So one column barely moves (binary search), one roughly doubles (linear search),
and the hand-written sorts roughly quadruple.

**All three of my sorts are O(n²), but bubble sort is about 2× slower than
insertion sort.** Big-O hides constants. Bubble sort does a full swap for every
out-of-order pair of neighbours, while insertion sort does one shift per step and
stops as soon as the item is in place. The order (insertion fastest, then
selection, then bubble) held at every size.

**`sorted()` is about 1,600× faster than my insertion sort at 10k.** Part of
that is O(n log n) vs O(n²), and part is that Timsort runs in C while my loops
run in the Python interpreter. The algorithm explains why the gap keeps
growing; C explains why it's already big at 1,000 items.

### Is it worth sorting first so you can use binary search?

At 10k items, sorting once costs about 1.9 ms, and each binary search saves about
0.375 ms compared to a linear search (0.377 − 0.002). So it pays off after
1.9 / 0.375, about **5 searches**. For a single search, linear search wins. But
the shop's catalogue gets searched thousands of times between changes, so
sorting first is clearly worth it there.

### The catalogue sort

Top-level category A-Z, then heaviest first, then name A-Z, in one `sorted()`
call with the key `(top_category, -weight_g, name)`. Negating the weight turns
"descending" into "ascending", so a single key handles all three parts (D10).

---

## 3. Hashing (Task 2.3)

### Big-O with and without hashing

| Task | With hashing | Without | What I used |
|---|---|---|---|
| Duplicate SKUs on import | O(n) | O(n²), comparing each row with every earlier row | a set of SKUs already seen |
| Group by tag | O(total tags) | O(tags × n), one pass per tag | a dict, tag → names |
| Most rented | O(R + m log m), m = distinct items | O(R × m), counting each item separately | a dict, SKU → count |
| Packing challenge (two-sum) | O(n), one pass | O(n²), trying every pair | a dict, weight → item |
| Word search (stretch) | O(words + matches) per search, after building it once | O(n) per search | a dict, word → set of SKUs |

### Stretch task: the word index vs linear search

To reproduce: `python benchmarks/benchmark_word_index.py`. The query is
"zhiyun drone", and both words have to match.

| n | build_index_ms | linear_search_ms | index_search_ms | matches |
|---|---|---|---|---|
| 1,000 | 2.585 | 0.524 | 0.0075 | 11 |
| 5,000 | 16.825 | 2.514 | 0.0058 | 38 |
| 10,000 | 37.170 | 5.064 | 0.0107 | 80 |
| 50,000 | 184.369 | 28.212 | 0.0990 | 394 |

**The index search still grows a little (0.006 → 0.099 ms).** The two dict
lookups are O(1), but combining the two sets of SKUs and sorting the result
depends on how many matches there are: 394 at 50k against 11 at 1k. So the cost
now follows the size of the answer instead of the size of the shop, which is
exactly what an index is for.

**The trade-off.** Building the index takes about 184 ms at 50k (about 7 linear
searches' worth), plus memory for every word of every item. It's worth it for a
catalogue that's searched much more often than it changes, but every new item
would also have to be added to the index (D12).

---

## 4. Stacks, queues and linked lists (Task 2.4)

### `list.pop(0)` vs `deque.popleft()`

To reproduce: `python benchmarks/benchmark_queue.py`. This is the time to empty
a queue of n customer IDs from the front, the way the waiting list serves
people. Median of 5 runs.

| n | list.pop(0) ms | deque.popleft() ms | ratio |
|---|---|---|---|
| 10,000 | 4.83 | 0.35 | 14x |
| 50,000 | 164.81 | 1.46 | 113x |
| 100,000 | 557.06 | 3.59 | 155x |

**Why `pop(0)` is slow:** a Python list is one block of memory. `pop(0)` removes
the first item and then shifts every other item one place to the left, so each
pop is O(n) and emptying the whole queue is O(n²). Going from 50k to 100k
multiplied the time by about 3.4, heading towards 4×.

A deque is built from a chain of fixed-size blocks, with a pointer to each end.
`popleft()` just moves the front pointer, so each pop is O(1) and emptying the
queue is O(n). Doubling n roughly doubled its time (1.46 → 3.59 ms).

### Big-O of the new structures

| Operation | Structure | Time | Space |
|---|---|---|---|
| Push or pop an undo entry | `deque(maxlen=20)` used as a stack | O(1) | 20 entries at most |
| Undo a rent | plus `list.remove` from the rentals history | O(R) | O(1) |
| Undo a return | a lookup in that customer's own rentals | O(k) | O(1) |
| Join the waiting list / serve the next person | `deque.append` / `popleft` | O(1) | O(w) |
| Put a served customer back at the front | `deque.appendleft` | O(1) | none |
| Rental history: insert at the head | linked list | O(1) | one node |
| Rental history: walk / delete / reverse / 2nd from the end | linked list | O(n) | O(1) |

**Undoing a rent turned out to be O(R), not O(1).** Everything else in undo is a
dict or set operation, but removing the rental from the full history list is a
scan. It's still quick in practice, because the rental being undone is near the
end, but `list.remove` searches from the front. In Phase 3 the database's primary
key removes it directly.

---

## 5. Recursion (Task 2.5)

To see the sample output: `python -m dsa.categories`

### Recursive vs iterative

| Function | Recursive Big-O | How deep it goes | Iterative version |
|---|---|---|---|
| `factorial(n)` | O(n) time | n | a loop, O(1) space |
| `fibonacci(n)` | **O(2ⁿ)** time | n | `fibonacci_iterative`: O(n) time, O(1) space |
| `sum_of_digits(n)` | O(digits) | one level per digit (about 10 for any normal number) | a loop |
| `tree_lines` / `total_items` / `path_to` | O(nodes) | the tree's height | an explicit stack: `tree_lines_iterative`, `total_items_iterative`, `path_to_iterative` |

Naive Fibonacci on my laptop: n = 20 took 3.5 ms, 25 took 23 ms, and 30 took
225 ms. That's about 10× for every +5, since 1.6⁵ ≈ 11. The loop version stayed
under 0.1 ms.

### Depth 10,000: what `sys.setrecursionlimit` does and doesn't change

I built a chain of 10,000 categories, each one the only child of the one before:

| Function | Limit | Depth | Result |
|---|---|---|---|
| `path_to` (plain Python calls) | 1,000 (the default) | 10,000 | `RecursionError: maximum recursion depth exceeded` |
| `path_to` | 20,000 | 10,000 | works |
| `path_to` | 1,000,000 | 200,000 | works, but slowly (it copies the path at every level, so O(depth²)) |
| `total_items` (recurses through C's `sum()`) | 20,000 | 10,000 | `RecursionError: Stack overflow (used 2914 kB)` |
| all the `*_iterative` versions | 1,000 (the default) | 10,000 | work |

**What the limit changes:** only Python's own safety counter, i.e. how many
Python calls it allows before raising `RecursionError`.

**What it doesn't fix:**
1. The process's real C stack, which the operating system gives a fixed size
   (a few MB). Python 3.14 runs plain Python-to-Python calls without using the C
   stack, which is why `path_to` survived once I raised the counter. But
   `total_items` calls itself through `sum()` and a generator, which are C code,
   so every level also uses C stack. It ran out at depth 10,000 even with the
   limit at 20,000. On older Python versions this can crash the whole program.
2. Speed and memory. Every call still costs memory, and a deep recursion that
   copies data (like `path_to`'s list) gets slower at every level.

**Which is clearer?** The recursive versions. `path_to` reads just like its
definition: "the path to X is my name plus my child's path to X". The iterative
version has to carry the path around on its own stack.

**Which would I use at depth 10,000?** The iterative one. Its only limit is memory.

### Where recursion is the wrong choice

- **`fibonacci`** is the worst. Each call makes two more, so the same values get
  recalculated again and again: `fibonacci(30)` makes about 2.7 million calls to
  produce one number. A loop, or remembering earlier answers, fixes it.
- **`factorial`** works, but it goes n levels deep, so `factorial(5000)` fails
  at the default limit where a loop never would. Recursion gains nothing here.
- **`sum_of_digits`** and the **category tree** are good fits. They never go
  deep (a handful of digits, a tree about 3 levels high), and a tree really is
  recursive: every category is a smaller tree.

---

## 6. What I took away from Phase 2

1. **Measure before optimising.** The biggest slowdown (`rent`) was in a method
   that looked O(1). Only the numbers showed it.
2. **Hashing turned most O(n) and O(n²) work into O(1) lookups:** indexes for
   renting and returning, a set for duplicates, a dict for two-sum, and the word
   index for search.
3. **Picking the right container matters more than clever code:**
   `deque.popleft()` vs `list.pop(0)` was 155× faster at 100k, with the same
   one-line call.
4. **Big-O hides constants.** All three hand sorts are O(n²), but bubble sort
   was 2× slower than insertion sort, and Python's `sorted()` was about 1,600×
   faster at 10k.
5. **Recursion suits problems that are naturally recursive and shallow.** For
   deep or repetitive ones, I'd use a loop or an explicit stack.
