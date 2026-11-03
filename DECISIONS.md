# Decision Log

Each entry: the problem, the options, what was chosen and why.

---

## Phase 1: Python + OOP

### D1. Where does tier knowledge live?

- **Problem:** Basic, Plus and Pro differ in item limit (R3), rental period and late fee (R5). The code needs these numbers in many places.
- **Options:**
  1. One `Customer` class with a `tier` string and `if tier == 'Basic'` checks.
  2. A lookup dict `{"Basic": (2, 3, 50), ...}` inside `GearShare`.
  3. An abstract `Customer` with subclasses `BasicCustomer`, `PlusCustomer`, `ProCustomer`, each overriding `max_items()`, `rental_period()`, `late_fee_per_day()`.
- **Chosen:** Option 3 (polymorphism).
- **Why:** Option 1 scatters `if` chains through the code, and adding a tier means editing every one of them. Option 2 keeps the numbers away from the object they describe. With option 3, the service just calls `customer.max_items()`, and a new tier is one new class. The only place a tier *name* is turned into a class is the loader's mapping dict (`TIER_CLASSES`), which is a lookup, not a branch.

### D2. How do item types differ: a flag or subclasses?

- **Problem:** Display items are never rented (R1), accessories are always 2 days and can't be extended (R2), and equipment follows the tier.
- **Options:**
  1. A single `GearItem` with an `item_type` string and `if` checks in `rent()` / `extend()`.
  2. An abstract `GearItem` with `Equipment`, `Accessory`, `DisplayItem` answering `is_rentable()`, `rental_days(customer)`, `can_extend()`.
- **Chosen:** Option 2.
- **Why:** The rule belongs to the item. `Accessory.rental_days()` returns 2 regardless of customer, and `Equipment.rental_days(customer)` asks the customer. This double dispatch means `GearShare` never needs to know which combination it has.

### D3. Where does the late-fee calculation live?

- **Problem:** R5 needs days late (from the rental's dates), the daily rate (from the customer's tier) and the cap (from the item's price).
- **Options:**
  1. `GearShare`: it already sees everything.
  2. `Customer`: it owns the rate.
  3. `Rental`: it owns the dates and holds references to both the customer and the item.
- **Chosen:** Option 3, `Rental.late_fee(returned_on)`.
- **Why:** The rental is the only object that naturally has all three inputs, and the calculation can be tested on a single `Rental` with no service, no files and no setup. *Against it:* if fees ever depended on shop-wide policy (for example, holidays), the rental would need to be told about that policy, and the service would be the better home.
- **Consequence (tier upgrade question):** because `Rental` holds a reference to the `Customer` object, a customer upgraded from Basic to Pro gets the **new** rate and limit applied to existing rentals at return time. If the shop wanted the rate fixed at issue time, `Rental` would store `fee_per_day` when created. That is a one-line change, because the calculation lives in one place.

### D4. Class attribute vs instance attribute for the rental number

- **Problem:** new rentals need the next ID (`RN011`), and IDs must be unique across the whole shop.
- **Options:**
  1. An instance attribute on each `Rental` (each object would have its own counter, so they would all start at 1).
  2. A class attribute `Rental._next_number`, shared by every `Rental`.
  3. A counter on the `GearShare` service.
- **Chosen:** Option 2, with `Rental.reset_counter(ids)` called by `load_data()`.
- **Why:** the counter describes *all* rentals, not one rental, so it belongs to the class. The dates and extension count describe *one* rental, so they are instance attributes. `MAX_EXTENSIONS = 2` is also a class attribute, because R6 is the same for every rental.
- **Trade-off:** a class attribute is shared by every `GearShare` in the same process (for example, across tests). That is why `load_data()` always resets it from the loaded IDs. If several shops ever ran in one process, option 3 would be safer.

### D5. Validation errors and one extra exception

- **Problem:** the setters must stop invalid objects being created, and returning or extending an unknown rental ID must not crash.
- **Options:** raise `ValueError` everywhere; create a custom error for every field; or reuse the spec's hierarchy where one fits.
- **Chosen:** a bad SKU raises `InvalidSKUError` (R9 is a business rule with a fixed message in the spec). Blank names, a missing `@`, and negative units/prices/fines raise `ValueError`, which is Python's standard "bad value" error. I added **`RentalNotFoundError`** (a child of `GearShareError`) because the spec's list has no error for an unknown rental ID, and the menu must still print a clean `ERROR [RentalNotFoundError]: ...` instead of crashing.
- **Why:** each error carries a `code` (the rule number or the class name), so the console's `ERROR [R3]: ...` and the Phase 4 API's `{"error": "R3"}` come from the same place.
- **Later addition (Task 1.3):** `WaitingListError` (code `R7`) for joining a waiting list when a unit is actually free, or joining it twice.

### D6. Which collection holds which data

- **Problem:** `GearShare` looks things up on every rent, return and report, so the container decides the speed and the simplicity.
- **Options considered:** lists for everything (simple, but every lookup is a scan) vs a container per access pattern.
- **Chosen:**

| Data | Collection | Why |
|---|---|---|
| `items` | `dict` SKU → `GearItem` | Every operation starts with "find the item for this SKU": O(1). Keys are unique, which matches R9. Insertion order keeps the catalogue in file order. |
| `customers` | `dict` ID → `Customer` | Same: O(1) lookup by ID, with IDs unique. |
| `rentals`, `fines` | `list` | Only appended, and read in order (RN001, RN002, ...). Nothing is looked up by position. |
| `held_skus` | `dict` ID → `set` of SKUs | R8 becomes `sku in held` (O(1)), and because R8 allows only one unit per SKU, `len(held)` is exactly the R3 count. |
| `waiting_lists` | `dict` SKU → `list` of IDs | Order matters (first come, first served, R7). Phase 2 replaces the list with a `deque`, because `list.pop(0)` is O(n). |
| `audit_log` | `list` | Append-only history. |

- **Known weakness:** finding a rental by ID scans the list (O(n)). That is acceptable for 10 rentals, and it is measured and improved in Phase 2.

### D7. What "the first person in the list is served first" (R7) means

- **Problem:** when a drone comes back and Meera is #1 on the waiting list, what stops Pooja (who is not first) from renting the free unit straight away?
- **Options:**
  1. Only print "Next on waiting list: Meera Joshi" and let anyone rent the unit.
  2. Automatically create a rental for Meera.
  3. Move Meera from the waiting list to a **reservation**: the unit is held for her, and only she can rent it.
- **Chosen:** Option 3.
- **Why:** option 1 breaks R7 (whoever rents first wins, not whoever waited first). Option 2 rents to Meera without asking her, and she might now break R3 or R4. With option 3, Meera still goes through all the rent checks, and nobody can jump the queue. A pending reservation also counts as "another customer is waiting" for R6, so the item can't be extended in the meantime.

### D8. The audit log: a decorator, using the real clock

- **Problem:** every successful rent, return and extend must be recorded, and a failed one must not be.
- **Options:**
  1. Call `self.audit_log.append(...)` at the end of each of the three methods.
  2. A decorator `@audit` wrapped around them.
- **Chosen:** Option 2.
- **Why:** the logging code is written once, and the business methods stay about business rules. "Only on success" comes for free: if the method raises, the line after the call is never reached.
- **Time stamp:** the audit entry uses `datetime.now()`, not the `today` parameter. `today` is the *business* date that the rules are calculated from (and can be faked with `TODAY=`), while the audit log answers "when did a staff member actually do this?". Keeping the two separate means a test run with `TODAY=2026-11-03` still records when it really happened.

---

## Phase 2: DSA

### D9. Indexes for the hot paths, measured before and after

- **Problem:** the 2.1 benchmark showed that `rent` and `return_item` slow down linearly as the shop grows (`rent`: 0.26 ms at 1k → 4.8 ms at 50k), even though they should only touch one customer and one item.
- **Cause:** `unpaid_fines()` (R4 check) scanned every rental and fine; `get_open_rental()` scanned the rentals list; `iter_overdue()` scanned returned rentals that can never be overdue.
- **Options:**
  1. Leave it: 5 ms is still fast.
  2. Replace the `rentals` list with a dict.
  3. Keep the list as the history, and add **indexes**: `open_rentals` (ID → rental), `rentals_by_customer` (ID → list), `fines_by_rental` (rental ID → list).
- **Chosen:** Option 3.
- **Why:** option 1 hides a cost that grows with every rental ever made, so the shop gets slower every day, forever. Option 2 fixes lookup by ID but not "all rentals of one customer". The indexes are dicts pointing at the *same* objects (no copies), so the extra memory is one reference per rental. Every rental and fine is added through `_add_rental()` / `_add_fine()`, so the list and the indexes cannot disagree.
- **Result:** `rent` 4.8 ms → 0.01 ms and `return_item` 1.3 ms → 0.004 ms at 50k, both now flat. All Phase 1 tests are unchanged and still pass. Full numbers are in `docs/benchmark_report.md`.
- **Cost:** three more structures to keep in sync. Phase 3 moves this job to database indexes.

### D10. Catalogue sort with mixed directions

- **Problem:** the website's catalogue order is category **ascending**, weight **descending**, name **ascending**. A single `reverse=True` can't flip just one part.
- **Options:**
  1. Two (or three) passes: sort by name, then weight descending, then category, relying on Python's sort being **stable** (equal keys keep their earlier order).
  2. One pass with a tuple key, negating the number that sorts descending: `(top_category, -weight_g, name)`.
  3. `functools.cmp_to_key` with a hand-written compare function.
- **Chosen:** Option 2.
- **Why:** it is a single O(n log n) sort, and the key reads exactly like the requirement. Option 1 is the right tool when the descending part is **text** (you can't negate a string). Option 3 calls a Python function for every comparison (≈ n log n calls instead of n key calls), which makes it the slowest and the hardest to read.
- **Detail:** "category" means the **top-level** category (`GearItem.top_category`: `parent_category` if there is one, otherwise `category`), so Cameras and Lenses both sort as Photography, as in the spec's sample.

### D11. Hand sorts never change the caller's list

- **Problem:** should `bubble_sort(names)` sort `names` in place (like `list.sort()`) or return a new list (like `sorted()`)?
- **Chosen:** each hand sort copies the input and returns the sorted copy.
- **Why:** the benchmark sorts the *same* unsorted list several times. If the first run sorted it in place, every later run would sort already-sorted data, which is insertion and bubble sort's best case (O(n)). The median would then be a lie. The copy costs O(n), which is negligible next to O(n²).

### D12. The word index stays a stretch tool, not the engine's search

- **Problem:** `WordIndex` makes multi-word search about 285× faster at 50k items. Should `GearShare.search()` use it?
- **Options:**
  1. Replace `GearShare.search()` with the index.
  2. Keep the substring search in the engine, and keep `WordIndex` as a separate, measured tool.
- **Chosen:** Option 2, for now.
- **Why:** the two return **different answers**. The engine matches substrings (`"dron"` finds "DJI Mini Drone"), while the index matches whole words only. Phase 1's behaviour and samples are the spec, so swapping silently would change results. The index would also need updating on every `add_item`. If the website's search ever becomes slow, the index is the measured fix, but it should be a deliberate feature change ("search by words"), not a hidden one.

### D13. Packing challenge: what the dict stores

- **Problem:** two-sum needs "have I already seen an item with weight X?" in O(1).
- **Options:** a `set` of weights (answers yes/no only), or a `dict` weight → item.
- **Chosen:** `dict` weight → **first** item seen with that weight (`setdefault`).
- **Why:** the answer must name both items, so a set isn't enough. Checking `needed in seen` **before** adding the current item means an item can never pair with itself ("two different items"). Display items are skipped before anything is stored (R1). The result is O(n) time and O(n) space, instead of O(n²) time for trying every pair.

### D14. What an undo entry stores

- **Problem:** option 9 must truly reverse the latest rent or return. Pushing the `Rental` object isn't enough. A return also **created a fine** and may have **moved someone off the waiting list**, and by the time undo runs, the rental might have changed (returned, unit rented again).
- **Options:**
  1. Push the `Rental` object and reverse whatever it looks like now.
  2. Push a snapshot (deep copy) of the whole shop.
  3. Push a small `UndoEntry` with the action and IDs, plus the exact side effects: `used_reservation` (rent), the `Fine` created and `served_customer_id` (return).
- **Chosen:** Option 3.
- **Why:** option 1 can't undo the side effects, and it acts on an object that may no longer be in the state it was pushed in. Option 2 is O(whole shop) memory per action. With option 3, undo looks everything up again by ID, **checks first** (is the unit still free? did the served customer already rent it? would the customer break R3/R8?) and only then changes state. If a check fails, it raises `UndoNotPossibleError` instead of corrupting data. A served customer goes back to the **front** of the queue (`appendleft`), not the end, so undo never costs anyone their place.
- **Details:**
  - The stack is a `deque(maxlen=20)`, used only with `append`/`pop` (LIFO), so it can't grow forever in a long session.
  - Undoing the latest rent hands its ID out again (`Rental.release_id`), so undo + rent gives RN011 both times, without a gap.
  - Undo is recorded in the audit log as `undo_rent` / `undo_return`.

### D15. Waiting list as a `deque`

- **Problem:** the waiting list removes from the front (serve the first person, R7) and adds at the back.
- **Options:** `list` with `pop(0)`, `queue.Queue`, or `collections.deque`.
- **Chosen:** `collections.deque`.
- **Why:** measured at 100,000 entries, draining with `deque.popleft()` took 3.6 ms vs 557 ms with `list.pop(0)` (155×). `queue.Queue` is built for passing work between threads (with locks), which we don't need. A deque also gives O(1) `appendleft`, which undo needs.

### D16. Phase 1 menu sample changes with option 9

- **Problem:** the spec says the menu "gains option 9 (undo)", but the Phase 1 start-up sample shows the menu ending at 8, with "Please enter a number from 0 to 8."
- **Chosen:** the menu now lists `9. Undo`, and the error says "0 to 9". The highest number is computed from the options dict, not hard-coded. The start-up transcript test was updated for exactly these two lines. Every other Phase 1 sample is unchanged and still passes.
- **Why:** the Phase 2 spec explicitly extends the menu, and a prompt saying "0 to 8" while 9 works would be a bug.

### D17. Recursive tree functions, with iterative versions kept alongside

- **Problem:** the category tree (Gear Hub → Photography → Cameras) needs print, count and path. Recursion is the natural fit, but it has a depth limit.
- **Options:**
  1. Recursive only.
  2. Iterative only (explicit stack).
  3. Recursive as the main version (readable), plus iterative versions, tested to give identical results.
- **Chosen:** Option 3.
- **Why:** the shop's real tree is 3 levels deep, where recursion is the clearest code and the depth limit is irrelevant. The iterative versions prove the same results can be produced without the call stack, and a test shows they survive a 10,000-level tree where the recursive one raises `RecursionError`.
- **Rejected:** "just raise `sys.setrecursionlimit`". Measured on Python 3.14: it let plain-Python `path_to` reach depth 200,000, but `total_items` (which recurses through C's `sum()`) still overflowed the real C stack at depth 10,000 with the limit at 20,000. The limit is a safety counter, not more stack.
- **Tree order:** children are kept sorted by name, so `print_tree` output is the same however the items were loaded.

---

## Phase 3: SQL

### D18. SQLite, not PostgreSQL

- **Problem:** the spec allows SQLite or PostgreSQL, but the choice must be the same for Part A (SQL files) and Part B (Python engine).
- **Options:**
  1. **PostgreSQL:** a real server, richer types (`DATE`, `SERIAL`), and what most production shops use.
  2. **SQLite:** a single file, built into Python (`sqlite3`), with nothing to install.
- **Chosen:** SQLite.
- **Why:**
  - Anyone can run the project from a clean copy with no server and no `pip install`. Earlier, pip couldn't even reach pypi.org on this network.
  - Every test can get a fresh, throw-away database (`:memory:` or a temp file) in milliseconds, which the spec asks for in 3.7.
  - It supports everything Phase 3 needs: foreign keys, `CHECK` constraints, transactions, indexes and `EXPLAIN QUERY PLAN`.
- **Costs, and how they are handled:**
  - SQLite has no real `DATE` type, so dates are stored as ISO text `YYYY-MM-DD`. ISO text sorts and compares in date order, and `julianday()` does date arithmetic.
  - Foreign keys are **off by default** in SQLite, so every connection runs `PRAGMA foreign_keys = ON`.
- **When I would choose differently:** several app servers writing at the same time (the Phase 4 API under real load), or many concurrent users. SQLite allows only one writer at a time. Moving would mean changing the connection code and a few types, but the SQL in `queries.sql` is standard.

### D19. Available units: calculated, not stored

- **Problem:** "how many units of the Canon are free?" can be **stored** in an `items.available_units` column, or **calculated** as `total_units − (open rentals of that SKU)`.
- **For storing it:**
  - Reading is one column with no join, which is fastest for the catalogue page, which shows availability for every item on every visit.
  - Renting can claim a unit atomically: `UPDATE items SET available_units = available_units - 1 WHERE sku = ? AND available_units > 0`. The database itself refuses to go below zero, even when two rent requests arrive together.
- **For calculating it:**
  - It is derived data: the open rentals already say how many units are out. A stored copy is a **second source of truth** that can disagree with the first. That is exactly the update anomaly normalisation removes. Every rent, return, undo and manual fix would have to update both, or the shop shows "1 available" when nothing is on the shelf.
  - Phase 1 already works this way: availability is **rebuilt** from rentals with no return date.
  - The spec's Q11 is literally "units available right now", computed from rentals.
- **Chosen:** calculate it (`total_units − COUNT(open rentals)`), with an index on rentals so the count stays fast (Task 3.6).
- **Two rent requests at the same moment:** with a calculated value, "check availability, then insert the rental" must be one transaction that **locks before reading**. In SQLite that is `BEGIN IMMEDIATE`, which takes the write lock first, so the second request waits, then sees the first rental and gets "No units available". Without the lock, both could read "1 free" and both insert.
- **When I would denormalise (store it):** when reading availability is measured to be too slow, e.g. 10 million rentals and a catalogue page showing thousands of items. Then I'd store `available_units`, update it **in the same transaction** as every rental insert/return, add `CHECK (available_units BETWEEN 0 AND total_units)`, and keep a scheduled job that recalculates it from rentals and reports any difference.
