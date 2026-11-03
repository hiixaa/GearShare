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
