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
