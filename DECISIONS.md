# Decision Log

This is where I wrote down the design decisions I made along the way. For each
one: what the problem was, which options I considered, what I picked, and why.
They're numbered D1 to D33 in the order I made them, and the code comments
refer to them by number.

---

## Phase 1: Python + OOP

### D1. Where the tier rules live

**Problem.** Basic, Plus and Pro customers have different item limits (R3),
rental periods and late fees (R5), and these numbers are needed in a lot of
places.

**Options.**
1. One `Customer` class with a `tier` string, and `if tier == 'Basic'` checks wherever a number is needed.
2. A lookup dict inside `GearShare`, like `{"Basic": (2, 3, 50), ...}`.
3. An abstract `Customer` with `BasicCustomer`, `PlusCustomer` and `ProCustomer` subclasses, each overriding `max_items()`, `rental_period()` and `late_fee_per_day()`.

**Decision: option 3 (polymorphism).** With option 1, the `if` chains end up
everywhere, and adding a tier means hunting all of them down. Option 2 keeps the
numbers away from the thing they describe. With subclasses, the service just
asks `customer.max_items()`, and a new tier is one new class. The only place a
tier name becomes a class is the `TIER_CLASSES` dict in the loader, and that's
a lookup, not a branch.

### D2. Item types: a flag or subclasses?

**Problem.** Display items can never be rented (R1). Accessories are always 2
days and can't be extended (R2). Equipment follows the customer's tier.

**Options.** One `GearItem` with an `item_type` string and `if` checks inside
`rent()` and `extend()`, or an abstract `GearItem` with `Equipment`, `Accessory`
and `DisplayItem` subclasses that each answer `is_rentable()`,
`rental_days(customer)` and `can_extend()`.

**Decision: subclasses.** The rule belongs to the item.
`Accessory.rental_days()` returns 2 whoever the customer is, while
`Equipment.rental_days(customer)` asks the customer. Because each side answers
its own question, `GearShare` never has to work out which combination it's
dealing with.

### D3. Where the late fee is calculated

**Problem.** R5 needs three things: how many days late (from the rental's
dates), the daily rate (from the customer's tier) and the cap (the item's price).

**Options.** `GearShare`, because it can see everything; `Customer`, because it
owns the rate; or `Rental`, because it owns the dates and points at both the
customer and the item.

**Decision: `Rental.late_fee(returned_on)`.** The rental is the only object that
naturally has all three inputs, and I can test the fee on a single `Rental`
without setting up a whole shop. The argument against it: if fees ever depended
on shop-wide policy (holidays, say), the rental would have to be told about that
policy, and the service would be a better home.

**About tier upgrades** (one of the spec's questions): because a `Rental` keeps
a reference to the `Customer`, a customer upgraded from Basic to Pro gets the
new rate on their existing rentals when they return them. If the shop wanted the
rate fixed when the item was rented, the rental would store `fee_per_day` when
it's created. That's a one-line change, since the calculation lives in one place.

### D4. The rental number: class attribute or instance attribute?

**Problem.** New rentals need the next ID (RN011, RN012, ...), and IDs must be
unique across the whole shop.

**Options.** An instance attribute on each rental (useless, since every object
would start counting at 1), a class attribute `Rental._next_number` shared by
all rentals, or a counter on the `GearShare` service.

**Decision: a class attribute**, reset by `load_data()` through
`Rental.reset_counter(ids)`. The counter describes all rentals, not one, so it
belongs to the class. A rental's dates and extension count describe that one
rental, so they're instance attributes. `MAX_EXTENSIONS = 2` is a class attribute
too, because R6 is the same for every rental.

The catch is that a class attribute is shared by every `GearShare` in the same
process, which matters in tests. That's why `load_data()` always resets it from
the IDs it loads. If several shops ever ran in one process, a counter on the
service would be safer.

### D5. Validation errors, plus one extra exception

**Problem.** The property setters have to stop invalid objects from being
created, and returning or extending an unknown rental ID mustn't crash the menu.

**Options.** `ValueError` for everything, a custom error for every field, or the
spec's exception hierarchy wherever it fits.

**Decision.** A bad SKU raises `InvalidSKUError`, because R9 is a business rule
with its own message in the spec. A blank name, an email without `@`, or negative
units, prices or fines raise Python's ordinary `ValueError`. I also added
`RentalNotFoundError` (a child of `GearShareError`), because the spec's list has
nothing for an unknown rental ID, and the menu should still print a clean
`ERROR [RentalNotFoundError]: ...`.

Every error carries a `code`: the rule number (`R3`) or the class name. So the
console's `ERROR [R3]: ...` and, later, the API's `{"error": "R3"}` both come from
the same place. In Task 1.3 I added `WaitingListError` (code `R7`) for joining a
waiting list when a unit is actually free, or joining it twice.

### D6. Which collection holds what

**Problem.** `GearShare` looks things up on every rent, return and report, so
the choice of container decides both speed and simplicity.

**Options.** Plain lists for everything (simple, but every lookup is a scan),
or a container chosen for how each piece of data is used.

**Decision: one container per access pattern.**

| Data | Collection | Why |
|---|---|---|
| `items` | dict, SKU → item | Almost everything starts with "find the item for this SKU", which is O(1). Keys are unique, like SKUs (R9), and insertion order keeps the catalogue in file order. |
| `customers` | dict, ID → customer | Same reasoning: O(1) lookup by ID. |
| `rentals`, `fines` | list | Only ever appended to and read in order. |
| `held_skus` | dict, customer ID → set of SKUs | R8 becomes `sku in held` (O(1)). Since R8 allows one unit per SKU, `len(held)` is also exactly the R3 count. |
| `waiting_lists` | dict, SKU → list of IDs | Order matters (first come, first served). Phase 2 swapped the list for a deque (D15). |
| `audit_log` | list | Append-only history. |

The weak spot was that finding a rental by ID scanned the whole list. That's
fine for 10 rentals; I measured it and fixed it in Phase 2 (D9).

### D7. What "the first person in the list is served first" means

**Problem.** When the drone comes back and Meera is #1 on the waiting list, what
stops Pooja (who isn't first) from renting it straight away?

**Options.**
1. Just print "Next on waiting list: Meera Joshi" and let anyone rent the unit.
2. Create a rental for Meera automatically.
3. Move Meera from the waiting list to a reservation: the unit is held for her, and only she can rent it.

**Decision: option 3.** Option 1 breaks R7, because whoever is quickest wins,
not whoever waited longest. Option 2 rents to Meera without asking her, and she
might break R3 or R4 by then. With a reservation, Meera still goes through all
the normal rent checks, and nobody can jump the queue. A pending reservation
also counts as "another customer is waiting" for R6, so the item can't be
extended in the meantime.

### D8. The audit log: a decorator with real timestamps

**Problem.** Every successful rent, return and extend must be logged, and failed
ones must not.

**Options.** An `audit_log.append(...)` call at the end of each of the three
methods, or one `@audit` decorator wrapped around them.

**Decision: the decorator.** The logging code exists once, and the business
methods only contain business rules. "Only log on success" comes for free: if
the method raises, the logging line after it never runs.

The timestamp uses `datetime.now()`, not the `today` parameter. `today` is the
business date the rules are calculated from (and can be faked with `TODAY=`).
The audit log answers a different question: when did someone actually do this?
Keeping them separate means a test run with `TODAY=2026-11-03` still records when
it really happened.

---

## Phase 2: DSA

### D9. Indexes for the slow paths, measured before and after

**Problem.** The benchmark in 2.1 showed `rent` and `return_item` getting
slower as the shop grew (`rent` went from 0.26 ms at 1k items to 4.8 ms at 50k),
even though each one only deals with one customer and one item.

**Cause.** `unpaid_fines()` (the R4 check) scanned every rental and every fine,
`get_open_rental()` scanned the whole rentals list, and `iter_overdue()` looked
at returned rentals that can never be overdue.

**Options.** Leave it (5 ms is still fast); turn the rentals list into a dict;
or keep the list as the history and add indexes next to it: `open_rentals`
(ID → rental), `rentals_by_customer` (ID → list) and `fines_by_rental`
(rental ID → list).

**Decision: add the indexes.** Leaving it means a cost that grows with every
rental the shop ever makes. A dict alone fixes lookup by ID, but not "all of
this customer's rentals". The indexes point at the same objects (nothing is
copied), so they cost one reference per rental. Everything goes through
`_add_rental()` and `_add_fine()`, so the list and the indexes can't drift apart.

**Result.** At 50k items, `rent` dropped from 4.8 ms to 0.01 ms and `return_item`
from 1.3 ms to 0.004 ms, and both now stay flat as the shop grows. All the
Phase 1 tests still pass unchanged. The price is three more structures to keep in
sync; in Phase 3 the database took over that job. The full numbers are in
`docs/benchmark_report.md`.

### D10. Sorting the catalogue in mixed directions

**Problem.** The website's catalogue order is category A-Z, then weight
heaviest first, then name A-Z. A single `reverse=True` can't flip just one part.

**Options.** Sort several times (name, then weight descending, then category),
relying on Python's sort being stable; sort once with a tuple key that negates
the weight, `(top_category, -weight_g, name)`; or write a compare function and
use `functools.cmp_to_key`.

**Decision: the tuple key.** It's one O(n log n) sort, and the key reads exactly
like the requirement. Sorting several times is the right trick when the
descending part is text, because you can't negate a string. A compare function
calls Python code for every comparison, so it's both the slowest and the hardest
to read.

"Category" here means the top-level category (`GearItem.top_category`), so
Cameras and Lenses both sort as Photography, as in the spec's sample.

### D11. My hand-written sorts never change the caller's list

**Problem.** Should `bubble_sort(names)` sort `names` in place, like
`list.sort()`, or return a new list, like `sorted()`?

**Decision: return a sorted copy.** The benchmark sorts the same unsorted list
several times. If the first run sorted it in place, every later run would be
sorting already-sorted data, which is the best case for bubble and insertion
sort, and the median would be meaningless. Copying is O(n), which is nothing
next to O(n²).

### D12. The word index stays separate from the engine's search

**Problem.** The `WordIndex` makes multi-word search about 285× faster at 50k
items. Should `GearShare.search()` use it?

**Options.** Replace the engine's search with the index, or keep the
substring search and leave `WordIndex` as a separate, measured tool.

**Decision: keep them separate, for now.** They give different answers. The
engine matches substrings ("dron" finds "DJI Mini Drone"), while the index only
matches whole words. Phase 1's samples define the search behaviour, so swapping
quietly would change results. The index would also need updating whenever an
item is added. If search ever gets slow, the index is the measured fix, but it
should be a deliberate change ("search by words"), not a hidden one.

### D13. What the packing challenge's dict stores

**Problem.** Two-sum needs to answer "have I already seen an item with weight
X?" in O(1).

**Options.** A set of weights (which only says yes or no), or a dict from
weight to item.

**Decision: a dict from weight to the first item seen with it.** The answer has
to name both items, so a set isn't enough. I check `needed in seen` before
adding the current item, which means an item can never pair with itself. Display
items are skipped before anything is stored (R1). The whole thing is O(n) time
and space, instead of O(n²) for trying every pair.

### D14. What an undo entry stores

**Problem.** Option 9 has to genuinely reverse the last rent or return. Pushing
the `Rental` object isn't enough: a return may also have created a fine and
moved someone off the waiting list. And by the time undo runs, things may have
changed (the item returned, or the unit rented again).

**Options.**
1. Push the `Rental` and reverse whatever state it's in now.
2. Push a deep copy of the whole shop.
3. Push a small `UndoEntry`: the action, the IDs, and the exact side effects (whether a rent used a reservation; the fine and the served customer for a return).

**Decision: option 3.** Option 1 can't undo the side effects, and it acts on an
object that may have changed since it was pushed. Option 2 copies the whole shop
on every action. With option 3, undo looks everything up again by ID and checks
first (is the unit still free? has the served customer already rented it? would
the customer break R3 or R8?). Only then does it change anything. If a check
fails, it raises `UndoNotPossibleError` instead of leaving the data in a mess.
A customer who was served goes back to the front of the queue (`appendleft`),
not the end, so undo never costs anyone their place.

A few details:
- The stack is a `deque(maxlen=20)`, used only with `append` and `pop`, so it can't grow forever.
- Undoing the latest rent gives its ID back (`Rental.release_id`), so undo and rent again both produce RN011, with no gap.
- Undos are logged as `undo_rent` and `undo_return`.

### D15. The waiting list is a deque

**Problem.** The waiting list takes people off the front (serve the first in
line) and adds them at the back.

**Options.** A list with `pop(0)`, `queue.Queue`, or `collections.deque`.

**Decision: `collections.deque`.** I measured it: emptying 100,000 entries took
3.6 ms with `deque.popleft()` and 557 ms with `list.pop(0)`, about 155× slower.
`queue.Queue` is meant for passing work between threads and comes with locks we
don't need. A deque also has O(1) `appendleft`, which undo uses.

### D16. Option 9 changes one Phase 1 sample

**Problem.** Phase 2 adds "9. Undo" to the menu, but the Phase 1 start-up sample
shows the menu ending at 8, with "Please enter a number from 0 to 8."

**Decision.** The menu now shows `9. Undo`, and the error says "0 to 9". The
highest number comes from the options dict, not a hard-coded 8. I updated exactly
those two lines in the start-up test, and every other Phase 1 sample is
unchanged. The Phase 2 spec explicitly adds the option, and a prompt saying
"0 to 8" while 9 works would be a bug.

### D17. Recursive tree functions, with iterative versions alongside

**Problem.** The category tree (Gear Hub → Photography → Cameras) needs print,
count and path-finding. Recursion fits naturally, but it has a depth limit.

**Options.** Recursive only, iterative only (with an explicit stack), or
recursive as the main version with iterative versions tested to give the same
results.

**Decision: both, with recursion as the main version.** The real tree is three
levels deep, where recursion is the clearest code and the limit doesn't matter.
The iterative versions show the same results without the call stack, and a test
proves they handle a 10,000-level tree where the recursive version raises
`RecursionError`.

I tried just raising `sys.setrecursionlimit`, and it isn't a real fix. On Python
3.14 it let the plain-Python `path_to` go 200,000 levels deep, but `total_items`
(which recurses through C's `sum()`) still overflowed the real C stack at depth
10,000 with the limit at 20,000. The limit is a safety counter, not extra stack.

The children are kept sorted by name, so `print_tree` gives the same output
however the items were loaded.

---

## Phase 3: SQL

### D18. SQLite rather than PostgreSQL

**Problem.** The spec allows either, but whichever I pick has to be used for
both the SQL files (Part A) and the Python engine (Part B).

**Options.** PostgreSQL, a real server with richer types and what most
production systems use, or SQLite, a single file built into Python.

**Decision: SQLite.** Anyone can run the project from a fresh clone without
installing a server. That mattered here, because at the start pip couldn't even
reach pypi.org on this network. Every test can get its own throwaway database in
milliseconds, which Task 3.7 asks for. And SQLite has everything Phase 3 needs:
foreign keys, CHECK constraints, transactions, indexes and `EXPLAIN QUERY PLAN`.

There are two catches:
- SQLite has no real DATE type. I store dates as ISO text (`YYYY-MM-DD`), which sorts in date order, and use `julianday()` for date arithmetic.
- Foreign keys are off by default, so every connection runs `PRAGMA foreign_keys = ON`.

I'd switch to PostgreSQL if several servers had to write at the same time.
SQLite only allows one writer at a time. The SQL in `queries.sql` is standard, so
moving would mostly mean changing the connection code.

### D19. Available units are calculated, not stored

**Problem.** "How many Canons are free?" could be a stored column,
`items.available_units`, or calculated as total units minus the item's open
rentals.

**The case for storing it.** Reading is one column with no join, which is fast
for the catalogue page. Renting can also claim a unit atomically with
`UPDATE items SET available_units = available_units - 1 WHERE sku = ? AND available_units > 0`,
so the database itself refuses to go below zero.

**The case for calculating it.** The number is derived: the open rentals already
say how many units are out. A stored copy is a second source of truth that can
disagree with the first, which is exactly the update anomaly normalisation is
meant to remove. Every rent, return, undo and manual fix would have to update
both, or the shop would show "1 available" with nothing on the shelf. Phase 1
already works this way, and the spec's Q11 is literally "units available right
now", calculated from rentals.

**Decision: calculate it**, with an index on rentals so the count stays fast
(see D25).

What if two people rent at the same moment? Then "check availability, then
insert the rental" has to be one transaction that takes the lock before
reading. In SQLite that's `BEGIN IMMEDIATE`: the second request waits, then
sees the first rental and gets "No units available". Without the lock, both
could read "1 free" and both insert.

I'd store it instead if reading availability ever proved too slow, say 10
million rentals and a catalogue page with thousands of items. Then I'd update
it in the same transaction as every rental, add
`CHECK (available_units BETWEEN 0 AND total_units)`, and run a regular job that
recalculates it and reports any difference.

### D20. Every ON DELETE, chosen on purpose

**Problem.** For each foreign key, what should happen to the child rows when
the parent is deleted? The spec specifically asks what should happen to a
customer's rentals if the customer is deleted.

**Options for customer → rentals.** CASCADE (deleting Rohan also deletes
RN002, RN009, RN010 and, through fines, his unpaid ₹600), SET NULL (keep the
rentals but forget who rented them), or RESTRICT (refuse to delete a customer
who has any history).

**Decision: RESTRICT.** CASCADE would quietly rewrite the shop's history: "most
rented items" (Q4) and "fines per tier per month" (Q7) would change after the
fact, and unpaid fines would vanish. The accountant, the owner, and anyone
sorting out a dispute ("who had the drone on 24 October?") would all object.
SET NULL keeps the numbers but loses accountability, and `customer_id` is
NOT NULL anyway. If a customer really has to go (a privacy request, say), the
right move is to anonymise their row, not to delete their history.

The rest:

| Foreign key | ON DELETE | Why |
|---|---|---|
| customers.tier → membership_tiers | RESTRICT, with ON UPDATE CASCADE | A tier that still has customers can't disappear; renaming a tier renames it for its customers. |
| rentals.customer_id → customers | RESTRICT | History must survive (above). |
| rentals.sku → items | RESTRICT | Same idea: an item that was ever rented stays in the records. Retire it, don't delete it. |
| fines.rental_id → rentals | RESTRICT | Money owed should never disappear as a side effect. Undoing a return deletes its fine explicitly first. |
| items.category_id → categories | RESTRICT | Move the items before deleting their category. |
| categories.parent_id → categories | RESTRICT | Photography can't be deleted while Cameras and Lenses sit under it. |
| item_tags → items, tags | CASCADE | A tag link means nothing without its item or tag. |
| waiting_list → items, customers | CASCADE | A queue entry is meaningless once the item or customer is gone. |
| audit_log | no foreign keys | The log has to keep describing rows that were later deleted (e.g. "RN011 rented, then undone"). |

### D21. CHECK passes on NULL, so the date checks use IS

**Problem.** My first `schema.sql` had `CHECK (date(due_date) = due_date)`. A
test showed it accepted `'2026-13-03'`. `date('2026-13-03')` is NULL,
`NULL = '2026-13-03'` is also NULL, and SQL counts a CHECK that comes out NULL
as passed. Only FALSE fails.

**Options.** Add `AND date(x) IS NOT NULL` to every check, or compare with `IS`,
because `NULL IS 'text'` is false rather than NULL.

**Decision: `CHECK (date(x) IS x)`.** It's shorter, and it also rejects
impossible dates like `2026-02-30`, which `date()` quietly rolls over to
`2026-03-02`. I only found this bug because I tested every CHECK with a bad row.

### D22. The SQL scripts run as modules (`python -m sql.run_sql`)

**Problem.** On this laptop, `python sql/run_sql.py sql/schema.sql` fails with
`PermissionError: [Errno 13] Permission denied` when it opens the `.sql` file.

**What I tested.** The same code started with `python -m sql.run_sql` or
`python -c` reads the file fine. A script reading a `.txt` copy works. A script
reading a `.sql` copy outside OneDrive (in `%TEMP%`) still fails. So it isn't
the code, OneDrive or the file: a security rule on the machine stops Python
processes started as `python something.py` from opening `.sql` files.

**Options.** Rename the files to `.txt`, which breaks the file names the spec
requires; ask IT for an exception, which is out of my hands and wouldn't help on
other machines; or make `sql/` a package and run everything with
`python -m sql.<script>`.

**Decision: run them as modules.** It works here and on any normal machine, and
the spec's file names stay the same. It has two knock-on effects:
- `python main.py` is started as a script, so it must never read `schema.sql`. The database is created once with `python -m sql.setup_db`, and the engine only opens it.
- Tests must be run with `python -m pytest`. The `pytest.exe` launcher counts as a script, so the database tests fail with the same error.

### D23. Q11 and the display item: "available" means "on the shelf"

**Problem.** Q11 ("units available right now") shows the Vintage Leica with 1
available, even though R1 says it can never be rented. Is that wrong?

**Options.** Show 1, since the unit is physically in the shop; show 0 for
display items with a CASE; or leave display items out of Q11 altogether.

**Decision: show 1, as in the spec's expected output.** Q11 answers "how many
units aren't out on rental?", and that's the same calculation for every item.
Whether an item may be rented is a different fact, stored in `item_type` and
enforced by `DisplayItem.is_rentable()`. Squashing both into one number would
hide which one caused a 0. The console already splits them the same way: the
catalogue prints "not rentable" for the Leica based on its type, not its count.

A page that only cares about "what can I rent right now?" should filter out
display items, or add a separate `rentable` column, rather than redefine
"available".

### D24. Choosing the join for each query

**Problem.** Each of the 12 queries needs a join type, and the wrong one quietly
drops or adds rows.

**The rule I used.** INNER JOIN when every row I want has a match (a rental
always has a customer and an item). LEFT JOIN when the rows I want are exactly
the ones without a match: Q5 (never rented), Q6 (no recent rental), and Q11
(items with no open rental still need a row).

**Two traps I avoided.**
- Q6 keeps the date filter in the ON clause, not in WHERE. Putting `WHERE r.issue_date >= '2026-08-05'` after a LEFT JOIN throws away the NULL rows and turns it back into an INNER JOIN, and Pooja (who has never rented) disappears.
- Q11 uses `COUNT(r.rental_id)`, not `COUNT(*)`. After a LEFT JOIN, an item with no open rentals still produces one row of NULLs. `COUNT(*)` would count it, and the SD card would show 2 instead of 3. Counting a column skips NULLs.

Q12 uses a self-join: who-rented-what joined to itself on the same customer,
with `a.name < b.name` so each pair appears once and an item never pairs with itself.

### D25. One covering index on rentals, chosen by measuring

**Problem.** With 100,000 rentals, the two slowest queries were Q12 (5.5 s) and
Q5 (181 ms). SQLite doesn't index foreign keys automatically, so `rentals.sku`
had no index at all.

**What I tried, all measured (`docs/index_report.md`).**
1. Simple indexes on the foreign keys, like `rentals(sku)`.
2. A separate index for each slow query.
3. One covering index for every query that starts from "the rentals of this item": `rentals(sku, return_date, issue_date, customer_id, rental_id)`.

**Decision: option 3.** The first attempt made Q5, Q6 and Q10 slower. The index
only held `sku`, so for each of about 100,000 rows SQLite had to jump back into
the table for the other columns, which is slower than just reading the table
once. The second fixed Q5 (24.7× faster) but made Q9 3× slower, for the same
reason: its index didn't include `customer_id`. The single covering index holds
every column Q4, Q5, Q9, Q10 and Q11 read. `sku` comes first because every one of
them looks up by item, and `return_date` second so that "the open rentals of this
item" (the availability check from D19) is one continuous range. The results:
Q5 17× faster, Q10 3.9×, Q2 3.3×, Q11 2.3×, and nothing measurably slower.

Q12 gets no index. Its cost is producing about 5 million item pairs, and no
index can remove that work. At real scale it should be a precomputed summary.

I also chose not to index `fines(paid)`. It only has two values, and Q8 reads
every fine anyway, so it would add work on every write and save nothing.

The cost of the index I kept: it repeats 5 of the 7 rental columns, so it
roughly doubles the space rentals take, and every insert or return updates it.
That's fine for a shop that checks availability far more often than it rents.

### D26. The engine on the database: load once, write through

**Problem.** `GearShare` has to read and write through the `storage/` classes
instead of lists and CSV files, keep every message the same, and still pass every
Phase 1 and Phase 2 test.

**Options.** Query the database for everything (every `rent()` runs SELECTs for
the customer, the item, the fines and availability, with nothing kept in
memory), or load the shop into objects once at start-up and write every change
through to the database.

**Decision: load once, write through.** The rules need objects:
`customer.max_items()` and `item.rental_days(customer)` are the Phase 1
polymorphism, so rows would have to become objects on every call anyway. The
Phase 2 indexes keep every rule check O(1) without a trip to the database, and
all the existing tests run unchanged, just on a real database now. The database
is the source of truth: memory is a copy made at start-up, and it gets rebuilt
whenever the two could disagree.

How "one operation, one transaction" works:
- `rent`, `return_item` and `extend` run inside the `@audit` decorator, which opens one transaction around both the operation's writes and its audit row. `undo`, `join_waiting_list` and `add_item` open their own.
- `Database.transaction()` is a context manager: `BEGIN IMMEDIATE` on the way in, `COMMIT` on success, `ROLLBACK` on any exception. Nested use joins the outer transaction.
- If the database refuses a write (`StorageError`), the transaction rolls back and `GearShare` reloads itself from the database, so memory never keeps a change the database rejected. I tested this by forcing the audit insert to fail: the rental row was rolled back too, and memory agreed.
- Rule violations are raised before anything is written, so they never touch the database.

The layers stay clean, as the spec's hint asks: `gearshare.py` contains neither
`sqlite3` nor `SELECT`, and a test checks it. All the SQL lives in `storage/`,
always with `?` parameters, and another test checks that nothing there is built
with an f-string.

The Phase 2 benchmarks still run purely in memory from generated CSVs. Instead
of sprinkling `if storage is None` checks everywhere, they get a `NullStorage`
that has the same methods and simply saves nothing (the Null Object pattern).

**The trade-off.** Two programs writing to the same database wouldn't see each
other's changes until they reload. That's fine for one console or one API
process; anything bigger would move the availability check into SQL, as in
`tx_demo.sql`.

I skipped the optional SQLAlchemy path. Plain DB-API keeps the SQL visible,
which is the whole point of this phase.

### D27. Parameterised queries everywhere (the injection experiment)

**Problem.** Search text comes from users, so how does it reach the database?

**What happened** (`python -m sql.injection_demo`, also covered by `tests/test_injection.py`):

| Call | Rows returned |
|---|---|
| `search_unsafe("Drone")` | 1 |
| `search_unsafe("' OR '1'='1")` | 7 (every item leaked) |
| `search_safe("' OR '1'='1")` | 0 |
| `search_safe("Drone")` | 1 |

The f-string version pasted the user's text straight into the SQL, giving
`SELECT name FROM items WHERE name LIKE '%' OR '1'='1%'`. The attacker's first
quote closed the string early, so the rest was read as SQL, and
`name LIKE '%'` matches every row. The user's text changed the structure of the
query, not just a value in it. A different payload could read other tables
(`' UNION SELECT email FROM customers --`).

The parameterised version is different because the SQL text is fixed
(`... LIKE '%' || ? || '%'`), and the database parses it before it ever sees the
user's text. The text arrives separately, as a value for the `?` slot, so it can
only ever be data. `' OR '1'='1` is searched for literally, as an odd-looking
name, and matches nothing. Escaping quotes by hand isn't a real fix: it's easy
to miss a case, while placeholders make the mistake impossible.

**Decision.** Every query in the project uses `?` placeholders. The only SQL
built from strings is `search_unsafe()` in `sql/injection_demo.py`, which is a
throwaway demo that nothing imports.

There's one other place that joins SQL from pieces, and it's harmless:
`sql/index_report.py` runs `"EXPLAIN QUERY PLAN " + sql`, where `sql` is one of
my own 12 queries from `queries.sql`. EXPLAIN wraps a whole statement, so it
can't be a `?` value, and no user text is involved. I found it by searching the
whole project for SQL built from pieces.

A `?` can only stand for a value, never a table or column name. Where the SQL
itself had to vary (the row-count test for each table), I wrote out each full
query as a constant instead.

---

## Phase 4: React + API

### D28. Which HTTP status each exception gets

**Problem.** Every engine exception has to become an HTTP status plus
`{"error": code, "message": text}`, with the console's exact message.

**The rule I used** (from the spec's hint): 404 means the thing doesn't exist,
409 means it exists but its current state conflicts with the request, and 422
means the input itself makes no sense.

| Exception | Status | Why |
|---|---|---|
| `InvalidSKUError` | 422 | "123" can never be a SKU, so the input is malformed |
| `CustomerNotFoundError`, `ItemNotFoundError`, `RentalNotFoundError` | 404 | The request is well-formed, but there's no such thing |
| R1, R2/R6, R3, R4, R7, R8, `WaitingListError`, `UndoNotPossibleError` | 409 | The customer and item exist, but the shop's current state says no |
| Duplicate SKU on `POST /gear` | 409, code `R9` | That SKU already exists |
| Blank name, negative units, unknown `item_type`, missing JSON field | 422, code `ValidationError` | Bad input |
| `StorageError` | 503 | The request might be fine, but the server can't save right now; trying again later may work |

All of this lives in one `{class: status}` dict in `api/errors.py`, checked
along the exception's class hierarchy, with 409 as the default. A new rule error
automatically becomes a 409 without any new code.

FastAPI's own errors for a missing field normally look like `{"detail": [...]}`.
I convert them to `{"error": "ValidationError", "message": "sku: Field required"}`,
so the website only ever deals with one error shape.

I deliberately didn't add a pattern check on `sku` in the request model. If I
had, FastAPI would reject `{"sku": "123"}` before the engine saw it, and the
response wouldn't match the spec's sample (`InvalidSKUError`, "SKU must be exactly
10 digits."). The rule lives in the engine only. All my status codes match the
spec's samples.

### D29. One engine per API process, all endpoints `async def`

**Problem.** FastAPI runs plain `def` endpoints in a thread pool. A SQLite
connection can only be used by the thread that created it, and `GearShare`'s
in-memory data isn't thread-safe either.

**Options.** Make every endpoint `async def`, so they all run one at a time on
the single event-loop thread; keep `def` endpoints, turn off
`check_same_thread` and put a lock around every engine call; or create a new
`GearShare` for every request.

**Decision: `async def`.** Each engine call takes microseconds plus one small
SQLite write, so handling them one at a time costs nothing noticeable. It also
means two customers renting the last unit "at the same moment" are handled one
after the other: the second gets `409 R7 No units of ... are available.`, and
that's true. The lock version does the same with more code to get wrong, and a
new engine per request would reload the whole shop every time.

The engine is created once when the app starts (FastAPI's `lifespan`: open the
storage, create `GearShare`, `load_data()`) and closed on shutdown.
`create_app(db_path, today)` lets the tests give it a fresh temporary database
and a fixed date. This only works with a single API process; several workers
would each have their own copy in memory (D26).

### D30. Extra endpoints the screens needed, and CORS

**Problem.** The spec gives sample requests, but the website also needs a
customer picker, a "Join waiting list" button, the staff "Add item" form and a
category filter.

**What I added.**
- `GET /customers`, for the picker and the basket limit
- `POST /waiting-list`, which returns the console's "... is #1 on the waiting list ..." text
- `POST /gear`, to add an item
- `GET /categories`, for the filter
- `GET /gear/{sku}` also returns `price` and `top_category` for the details page, while `GET /gear` keeps exactly the eight fields of the spec's sample.

Each one just calls an existing `GearShare` method. No rule is copied into the
API (the duplicate-SKU check, for example, is `GearShare.add_item`'s own).
Filtering by `category=Photography` matches items whose category or top-level
category is Photography, so it returns both the Canon and the Sony lens.

**CORS.** Only `http://localhost:5173` (the Vite dev server) is allowed, and
that can be changed with `GEARSHARE_WEB_ORIGIN`. Only GET, POST and the
`Content-Type` header are allowed, and a test checks that any other origin is
refused. I didn't use `*`, because then any website could call the API from a
visitor's browser.

### D31. Tailwind, not Material UI

**Problem.** The spec asks me to pick Tailwind or Material UI and use it
consistently.

**Options.** MUI gives ready-made components (Card, Select, Snackbar) with
accessibility built in, but it's a big dependency with its own styling system to
learn. Tailwind is just utility classes on plain HTML elements.

**Decision: Tailwind** (version 4, through the `@tailwindcss/vite` plugin). The
screens are simple (cards, a form, a table), and Tailwind keeps them as ordinary
`<button>`, `<label>`, `<select>` and `<table>` elements, which are accessible and
keyboard-friendly by default. Explaining my code means explaining real HTML, not
a library's API. Responsiveness is visible right in the markup:
`grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` is literally "one column at 360 px".
The whole stylesheet comes out at about 14 kB, because only the classes I use are
generated.

The downside is that nothing comes ready-made, so I wrote the focus outlines,
the spinner and the toasts myself (a few lines each).

### D32. The search lives in the URL, not in useState

**Problem.** The spec asks: "A 'Back to results' link must restore the previous
search. Where must the search text live for that to work?"

**Options.** `useState` in the catalogue page, which is lost as soon as you open
an item; a context or global store, which survives navigation but not a reload
or a shared link; or the URL query string (`/?q=drone&category=Drones&sort=name`)
through `useSearchParams`.

**Decision: the URL.** It already survives navigation, reloads, the browser's
Back button and bookmarks. Each card's link passes the current search along as
`state.from`, so the details page's "Back to results" goes to `/?q=drone`, and the
catalogue rebuilds itself from that. Typing uses `{ replace: true }`, so each
letter doesn't add a history entry.

Fetching follows from this. The request is built from the URL values after a
300 ms debounce, and `useApi(path)` cancels the previous request in its cleanup
whenever the path changes. So a slow old response can never overwrite a newer
one. That's the "Slow 3G" check from the spec.

### D33. Answers to the Phase 4 questions

1. **The basket limit is checked in React and in Python. Why both, and which one must never be removed?** React's check is for the customer: instant feedback ("Basket full: ...") without waiting for the server. Python's R3 check is the actual rule. Anyone can call `POST /rentals` without going through our website (curl, a modified page), and the React basket doesn't even know about rentals that are already open. The Python check must never go; the React one is a convenience.

2. **Two customers rent the last unit at the same moment. What does the second one see, and is it true?** The API handles one request at a time (D29), and every rent is a single database transaction (D26). The first customer gets 201; the second gets `409 R7 No units of '...' are available.` That's true at the moment the server answers, even if the second customer's page still showed "1 available" from an earlier load. That's exactly why the server has the last word and its message is shown as it is.

3. **Which component would suffer most from prop drilling without context?** `GearActions`, the "Add to basket" / "Join waiting list" button. It needs the current customer and the basket, but it sits under Layout → CataloguePage → GearList → GearCard, and none of those use either. With `CustomerContext` and `BasketContext`, it reads them directly.

4. **What does each screen say when the API is down?** Every screen that loads data shows "Can't reach the rental server." with a Retry button: plain words, no error codes. The customer picker shows "(unavailable)", and checkout and the waiting-list button show the same sentence in red. Someone non-technical can understand "can't reach the server, try again".
