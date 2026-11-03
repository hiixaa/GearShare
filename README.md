# GearShare Mini

A rental system for **FrameWorks Gear Rental**, built in four phases:

| Phase | Topic         | Status      |
|-------|---------------|-------------|
| 1     | Python + OOP  | Done        |
| 2     | DSA           | Done        |
| 3     | SQL           | —           |
| 4     | React + API   | —           |

## Requirements

- Python 3.12 or newer (developed on 3.14)
- Git

## Setup (from a clean copy)

```powershell
git clone <repo-url> Mini-GearShare
cd Mini-GearShare
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # macOS / Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## Run the console

Every sample in the spec uses today = **2026-11-03**. Set it with the `TODAY`
environment variable (if it is not set, the real date is used):

```powershell
# Windows PowerShell
$env:TODAY="2026-11-03"; python main.py
```

```bash
# bash / Git Bash / macOS / Linux
TODAY=2026-11-03 python main.py
```

In PowerShell, `$env:TODAY` stays set for the rest of that terminal session.
Remove it with `Remove-Item Env:TODAY`.

## Run the tests

```powershell
python -m pytest -v
```

Each test loads a fresh copy of the starter data, so tests never depend on
each other. `tests/test_main.py` replays every sample transcript from the spec
through the real menu and compares the output line by line.

## Phase 2: data structures, demos and benchmarks

The menu gains **option 9 (Undo)**, which reverses the latest rent or return.

Each `dsa/` module prints its part of the spec's Phase 2 sample:

```powershell
python -m dsa.search          # binary search with comparison counts
python -m dsa.sorting         # bubble / insertion / selection passes + catalogue sort
python -m dsa.hashing         # group by tag, most rented, packing challenge
python -m dsa.history         # rental history linked lists
python -m dsa.categories      # recursion warm-ups and the category tree
python import_gear.py gear_with_duplicate.csv
```

Benchmarks (results and conclusions: [docs/benchmark_report.md](docs/benchmark_report.md)):

```powershell
python benchmarks/generate_data.py 10000      # fake shop of any size
python benchmarks/benchmark_engine.py         # 2.1 engine operations, 1k-50k
python benchmarks/benchmark_sorts.py          # 2.2 searches and sorts (~1 min)
python benchmarks/benchmark_word_index.py     # 2.3 stretch: word index
python benchmarks/benchmark_queue.py          # 2.4 list.pop(0) vs deque.popleft()
```

## Project layout

```
main.py         console menu (input/output only, no rules)
gearshare.py    GearShare service: enforces the Rulebook
items.py        GearItem (abstract) -> Equipment, Accessory, DisplayItem
customers.py    Customer (abstract) -> BasicCustomer, PlusCustomer, ProCustomer
rentals.py      Rental, Fine
errors.py       GearShareError and its children
import_gear.py  import a gear CSV, skipping duplicate SKUs (Phase 2)
dsa/            Phase 2: search, sorting, hashing, history, categories
benchmarks/     Phase 2: fake-data generator and timing scripts
data/           starter CSV files (+ gear_with_duplicate.csv)
docs/           class diagram, CRC cards, benchmark report, test output
tests/          pytest tests
DECISIONS.md    design decision log
```

## Rulebook traceability

| Rule | Statement (short) | Enforced by | Proved by (tests/...) |
|------|-------------------|-------------|-----------------------|
| R1 | Display items are never rented | `DisplayItem.is_rentable()`, checked in `GearShare.rent()` step 3 | `test_gearshare.py::test_r1_display_item_cannot_be_rented`, `test_models.py::test_r1_r2_item_types_answer_differently` |
| R2 | Accessories: 2 days, no extension | `Accessory.rental_days()`, `Accessory.can_extend()`, checked in `GearShare.extend()` | `test_models.py::test_due_dates_worked_example`, `test_gearshare.py::test_r2_accessories_cannot_be_extended` |
| R3 | No more items than the tier allows | `Customer.max_items()`, checked in `GearShare.rent()` step 5 | `test_gearshare.py::test_r3_item_limit` |
| R4 | Unpaid fines above ₹500 block renting | `GearShare.unpaid_fines()`, checked in `GearShare.rent()` step 4 | `test_gearshare.py::test_r4_unpaid_fines_above_500_block_renting`, `test_r4_fines_of_exactly_500_still_allowed` |
| R5 | Late fee = days × rate, capped at price | `Rental.late_fee()` | `test_models.py::test_late_fees_worked_example`, `test_r5_fee_never_more_than_replacement_price` |
| R6 | Max 2 extensions; none if someone waits | `GearShare.extend()`, `Rental.extend()`, `Rental.MAX_EXTENSIONS` | `test_gearshare.py::test_r6_extend_twice_then_refused`, `test_r6_no_extension_when_someone_is_waiting` |
| R7 | Waiting list, first come first served | `GearShare.join_waiting_list()`, `return_item()`, `rent()` step 7 | `test_gearshare.py::test_r7_no_unit_free`, `test_r7_first_in_waiting_list_is_served_first` |
| R8 | One unit of the same item per customer | `GearShare.rent()` step 6 (`held_skus` set) | `test_gearshare.py::test_r8_no_two_units_of_same_item` |
| R9 | SKU is exactly 10 digits and unique | `items.validate_sku()` (`GearItem.sku` setter), duplicate check in `load_data()` | `test_models.py::test_r9_sku_must_be_exactly_10_digits`, `test_gearshare.py::test_invalid_sku` |
| R10 | Due date is not late; the next day is | `Rental.days_late()` | `test_models.py::test_r10_return_on_due_date_is_not_late` |

Every exception has a `pytest.raises` test: `InvalidSKUError`, `ItemNotFoundError`,
`CustomerNotFoundError`, `RentalNotFoundError`, `ItemNotRentableError`,
`UnpaidFinesError`, `RentalLimitExceededError`, `DuplicateRentalError`,
`ItemNotAvailableError`, `ExtensionNotAllowedError`, `WaitingListError`.

## Design

- [docs/class_diagram.md](docs/class_diagram.md): class diagram, inheritance vs composition, CRC cards
- [DECISIONS.md](DECISIONS.md): every design decision and the alternatives rejected
