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

### D20. Every `ON DELETE`, chosen on purpose

- **Problem:** for each foreign key, what should happen to the child rows when the parent row is deleted? The spec asks in particular: *what should happen to a customer's rentals if the customer is deleted?*
- **Options for customer → rentals:**
  1. `CASCADE`: deleting Rohan deletes RN002, RN009, RN010, and through fines, his unpaid ₹600.
  2. `SET NULL`: keep the rentals but forget who rented them.
  3. `RESTRICT`: refuse to delete a customer who has any rental history.
- **Chosen:** `RESTRICT`.
- **Why:**
  - With `CASCADE`, deleting one customer silently rewrites the shop's history. Q4 "most rented items" and Q7 "fines per tier per month" would change after the fact, and unpaid fines would simply vanish.
  - **The accountant** (revenue and fines reports), **the owner** (which gear is popular) and **anyone settling a dispute** ("who had the drone on 24 October?") would all object.
  - `SET NULL` keeps the numbers but loses accountability, and `customer_id` is `NOT NULL` anyway.
  - If a customer must leave (for example, a privacy request), the right move is to **anonymise** the customer row (name and email replaced), not to delete history.
- **All the other choices:**

| Foreign key | ON DELETE | Why |
|---|---|---|
| customers.tier → membership_tiers | RESTRICT (+ ON UPDATE CASCADE) | A tier with customers can't vanish; renaming a tier updates its customers. |
| rentals.customer_id → customers | **RESTRICT** | History must survive (above). |
| rentals.sku → items | RESTRICT | Same reason: a rented item stays for the records (retire it, don't delete it). |
| fines.rental_id → rentals | RESTRICT | Money owed must never disappear as a side effect. Undo-of-return deletes the fine **explicitly** first. |
| items.category_id → categories | RESTRICT | Move the items before deleting their category. |
| categories.parent_id → categories | RESTRICT | Can't delete Photography while Cameras and Lenses hang under it. |
| item_tags.sku → items | CASCADE | Tag links mean nothing without the item. |
| item_tags.tag_id → tags | CASCADE | Deleting a tag removes it from every item. |
| waiting_list → items / customers | CASCADE | A queue entry is meaningless once its item or customer is gone. |
| audit_log | no foreign keys | The log must still describe rows that were later deleted (e.g. "RN011 rented, then undone"). |

### D21. SQL `CHECK` passes on NULL: date checks use `IS`, not `=`

- **Problem:** the first version of `schema.sql` had `CHECK (date(due_date) = due_date)`. A test showed that `'2026-13-03'` was **accepted**: `date('2026-13-03')` is `NULL`, `NULL = '2026-13-03'` is `NULL`, and SQL treats a `CHECK` that evaluates to `NULL` as **passed** (only `FALSE` fails).
- **Options:** add `AND date(x) IS NOT NULL` to every check, or compare with `IS` (`NULL IS 'text'` is false, not NULL).
- **Chosen:** `CHECK (date(x) IS x)`. It's shorter, and it also rejects impossible dates like `2026-02-30` (which `date()` silently rolls over to `2026-03-02`, so it isn't equal to the input).
- **Lesson:** every `CHECK` was tested with a bad row. The bug was only found because a test inserted an invalid date and expected an error.

### D22. SQL scripts run as modules (`python -m sql.run_sql`)

- **Problem:** on this laptop, `python sql/run_sql.py sql/schema.sql` fails with `PermissionError: [Errno 13] Permission denied` when reading the `.sql` file.
- **What was tested:**
  - The same code started with `python -m sql.run_sql` or `python -c` reads the file fine.
  - A script reading a `.txt` copy of the same file works.
  - A script reading a `.sql` copy **outside OneDrive** (in `%TEMP%`) still fails.
  - So it isn't the code, OneDrive or the file. A security rule on the machine blocks Python processes started as `python <file>.py` from opening `.sql` files.
- **Options:**
  1. Rename the files to `.txt`. That breaks the spec's required names (`schema.sql`, `seed.sql`, ...).
  2. Ask IT for an exception. That's out of our control, and other machines may differ.
  3. Run the scripts as modules: `sql/` becomes a package (`sql/__init__.py`) and every command is `python -m sql.<script>`.
- **Chosen:** Option 3. It works here and on any normal machine, and keeps the spec's file names.
- **Consequence for Part B (3.7):** `python main.py` is started as a script, so it must **not** read `schema.sql` at start-up. The database is created once by a `-m` command (`python -m sql.setup_db`), and the engine only opens it.
- **Consequence for tests:** run them with `python -m pytest` (as the README says). The `pytest.exe` launcher counts as a script, so the database tests fail with the same `PermissionError` when it is used.

### D23. Q11 and the display item: "available" means "on the shelf"

- **Problem:** Q11 "units available right now" shows the Vintage Leica (Showcase) with **1** available, but R1 says it can never be rented. Is 1 a wrong answer?
- **Options:**
  1. Show 1: the unit is physically in the shop (`total_units − open rentals`).
  2. Show 0 for display items (`CASE WHEN item_type = 'Display' THEN 0 ...`).
  3. Leave display items out of Q11 (`WHERE item_type <> 'Display'`).
- **Chosen:** Option 1, matching the spec's expected output.
- **Why:** Q11 answers one question, "how many units are not out on rental?", and that is the same calculation for every item. Whether an item **may** be rented is a different fact, already stored in `item_type` and enforced by `DisplayItem.is_rentable()` (R1). Mixing the two into one number would hide which fact caused a 0: is the Leica out on rental, or not for rent? It's the same split the console already makes: the catalogue prints `not rentable` for the Leica instead of a number, based on the item type, not on the count.
- **When I'd change it:** a page that only asks "what can I rent now?" (like the website's catalogue filter) should use option 3, or add a separate `rentable` column, rather than redefining "available".

### D24. Join choices in the query pack

- **Problem:** each of the 12 queries needs a join type, and the wrong one silently drops or adds rows.
- **Rule used:** `INNER JOIN` when every row we want **has** a match (a rental always has a customer and an item). `LEFT JOIN` when the rows we want are exactly the ones **without** a match (Q5: never rented; Q6: no recent rental; Q11: items with no open rental still need a row).
- **Two traps avoided:**
  - **Q6, filter in `ON`, not `WHERE`:** `LEFT JOIN rentals ... WHERE r.issue_date >= '2026-08-05'` would discard the NULL rows and quietly behave like an INNER JOIN, losing Pooja (who has never rented). The date filter belongs in the `ON` clause.
  - **Q11, `COUNT(r.rental_id)`, not `COUNT(*)`:** after a LEFT JOIN, an item with no open rentals still produces one row (of NULLs). `COUNT(*)` counts that row as 1, which would make the SD card show 2 instead of 3. `COUNT(column)` skips NULLs.
- **Q12** uses a **self-join** (a table joined to itself on the same customer), with `a.name < b.name` so each pair appears once and an item never pairs with itself.

### D25. One covering index on rentals, chosen by measurement

- **Problem:** with 100,000 rentals, the two slowest queries were Q12 (5.5 s) and Q5 (181 ms). SQLite doesn't index foreign keys, so `rentals.sku` had no index.
- **Options tried, all measured (docs/index_report.md):**
  1. Simple indexes on the foreign keys (`rentals(sku)`, `rentals(customer_id, ...)`).
  2. One index per query, each with that query's columns.
  3. **One covering index** for every query that starts from "rentals of this item": `rentals(sku, return_date, issue_date, customer_id, rental_id)`.
- **Chosen:** Option 3.
- **Why:**
  - Option 1 made Q5, Q6 and Q10 **slower**. The index held only `sku`, so for each of ~100,000 rows SQLite jumped back into the table for the other columns, which is slower than one sequential scan.
  - Option 2 fixed Q5 (24.7×) but made **Q9 3× slower**, for the same reason: its index lacked `customer_id`.
  - Option 3 is covering for Q4, Q5, Q9, Q10 and Q11. `sku` comes first because every query looks up by item, and `return_date` second so that "open rentals of this item" (the `rent()` availability check from D19) is one contiguous range. Result: Q5 17×, Q10 3.9×, Q2 3.3×, Q11 2.3×, and nothing measurably slower.
- **Q12 gets no index.** Its cost is producing about 5 million item pairs, which no index can remove. At scale it should be a precomputed summary.
- **Not created: `fines(paid)`.** It has 2 distinct values, and Q8 reads every fine anyway, so it would add write cost and save nothing.
- **Cost of the chosen index:** it repeats 5 of the 7 rental columns, so it roughly doubles the storage for rentals, and every rental insert/return now updates it too. That's acceptable because the shop reads availability far more often than it writes rentals.

### D26. The engine on the database: load once, write through, one transaction per operation

- **Problem:** `GearShare` must read and write through the `storage/` classes instead of lists and CSV files, keep every message identical, and pass every Phase 1 and 2 test.
- **Options:**
  1. **Query the database for everything**: every `rent()` runs `SELECT`s for the customer, the item, the fines and availability. There are no in-memory collections at all.
  2. **Load once, write through**: on start-up, load the shop from the database into objects. Every change is written to the database first, in a transaction, and then applied in memory.
- **Chosen:** Option 2.
- **Why:**
  - The rules need **objects**: `customer.max_items()` and `item.rental_days(customer)` are the polymorphism from Phase 1, so rows would have to become objects on every call anyway.
  - The Phase 2 indexes (`held_skus`, `open_rentals`, the `deque` waiting lists) keep every rule check O(1) without a round-trip to the database.
  - All Phase 1 and 2 tests run unchanged, now on a real database.
  - **The database is the source of truth.** Memory is only a copy made at start-up, and it is rebuilt from the database whenever they could disagree.
- **How "one unit" is guaranteed:**
  - `rent`, `return_item` and `extend` run inside the `@audit` decorator, which opens **one** transaction around the operation's writes **and** its audit row. `undo`, `join_waiting_list` and `add_item` open their own.
  - `Database.transaction()` is a context manager. `BEGIN IMMEDIATE` on entry, `COMMIT` on success, `ROLLBACK` on any exception. Nested use joins the outer transaction.
  - If the database refuses a write (`StorageError`), the transaction rolls back **and** `GearShare` reloads itself from the database, so memory can never keep a change the database rejected. Tested by forcing the audit insert to fail: the rental row is rolled back too, and memory agrees.
  - Rule violations (R1–R10) are raised before anything is written, so they never open a write at all.
- **Layers (the spec's hint):** `gearshare.py` contains neither `sqlite3` nor `SELECT`, and a test checks this. All SQL lives in `storage/`, always with `?` parameters, and a test checks that no `execute()` / `query()` there receives an f-string.
- **`NullStorage`:** the Phase 2 benchmarks and demos still run in memory from generated CSV files (`load_data(folder)`). Instead of `if storage is None` checks in every method, they get a `NullStorage` with the same interface that saves nothing (the Null Object pattern).
- **Trade-off:** with option 2, two programs writing to the same database at once would not see each other's changes until a reload. Fine for one console or one API process. A multi-process deployment would move availability checks into SQL (as in `tx_demo.sql`).
- **Optional path not taken:** SQLAlchemy ORM. Plain DB-API keeps the SQL visible and is what the spec requires; an ORM would hide exactly the SQL this phase is about.
