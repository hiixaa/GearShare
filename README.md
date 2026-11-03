# GearShare Mini

A rental system for **FrameWorks Gear Rental**, built in four phases:

| Phase | Topic         | Status      |
|-------|---------------|-------------|
| 1     | Python + OOP  | Done        |
| 2     | DSA           | Done        |
| 3     | SQL           | Done        |
| 4     | React + API   | Done        |

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

## Create the database (once)

Since Phase 3, everything is saved in a SQLite database, `data/gearshare.db`.
Create it (or reset it to the starter data at any time) with:

```powershell
python -m sql.setup_db
```

Always run the SQL scripts with `python -m ...` (not `python sql/...py`), and
the tests with `python -m pytest`. See DECISIONS D22 for why.

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

Each test gets its own fresh temporary database with the starter data, so
tests never depend on each other, and every Phase 1 and 2 test runs with the
real database underneath. `tests/test_main.py` replays every sample transcript from the spec
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

## Phase 3: the database

The engine now loads from and saves to `data/gearshare.db`: a rental made
today is still there after the program is closed and opened again.

```powershell
python -m sql.setup_db                        # create / reset: schema + seed + indexes
python -m sql.run_sql sql/queries.sql         # the 12 business queries
python -m sql.run_sql sql/tx_demo.sql         # rent as one transaction; rollback leaves no trace
python -m sql.index_report --explain Q12 Q5   # 100,000 rentals, EXPLAIN before/after (~1 min)
python -m sql.injection_demo                  # the SQL injection experiment
python -m sql.build_flat                      # rebuild data/gearshare_flat.csv
```

Write-ups:
- [docs/normalisation.md](docs/normalisation.md): flat file, anomalies, 1NF → 2NF → 3NF
- [docs/GearShare_ER_Diagram.png](docs/GearShare_ER_Diagram.png): ER diagram (dbdiagram.io)
- [docs/index_report.md](docs/index_report.md): EXPLAIN before/after, and the index not created
- [docs/query_results.txt](docs/query_results.txt): output of the 12 queries

## Phase 4: the website and the API

Requirements: Python packages from `requirements.txt` (adds `fastapi`,
`uvicorn`, `httpx`) and **Node.js 20.19+** (developed on Node 24).

**Terminal 1: the API** (http://localhost:8000, interactive docs at `/docs`):

```powershell
python -m sql.setup_db                                   # once, or to reset the data
$env:TODAY="2026-11-03"; python -m uvicorn api.main:app --reload --port 8000
```

**Terminal 2: the website** (http://localhost:5173):

```powershell
cd web
npm install                                              # once
npm run dev
```

- Open **http://localhost:5173** (not 127.0.0.1: the API's CORS allows only that origin).
- The API URL comes from `web/.env` (`VITE_API_URL`, default `http://localhost:8000`). See `web/.env.example`.
- Don't run the console `main.py` at the same time as the API (DECISIONS D26).

Tests:

```powershell
python -m pytest -q          # engine + database + API
cd web; npm test             # basket reducer + form validation
```

Phase 4 documents:
- [docs/component_tree.md](docs/component_tree.md): component tree, and where each piece of state lives
- [docs/wireframes.md](docs/wireframes.md): the five screens
- [docs/behaviour_table.md](docs/behaviour_table.md): the spec's behaviour table, as a checklist

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
storage/        Phase 3: the only code that talks SQL (one class per table group)
api/            Phase 4: FastAPI app over GearShare (api/main.py, errors.py, schemas.py)
web/            Phase 4: Vite + React website (src/pages, components, context, hooks, lib)
sql/            Phase 3: schema, seed, queries, tx_demo, indexes + scripts that run them
data/           starter CSVs, gearshare_flat.csv, gearshare.db (created, not committed)
docs/           diagrams, reports, normalisation write-up, test and query output
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
| R9 | SKU is exactly 10 digits and unique | `items.validate_sku()` (`GearItem.sku` setter), `GearShare.add_item()`; in the database `items.sku` is the PRIMARY KEY with a 10-digit CHECK | `test_models.py::test_r9_sku_must_be_exactly_10_digits`, `test_gearshare.py::test_invalid_sku` |
| R10 | Due date is not late; the next day is | `Rental.days_late()` | `test_models.py::test_r10_return_on_due_date_is_not_late` |

Every exception has a `pytest.raises` test: `InvalidSKUError`, `ItemNotFoundError`,
`CustomerNotFoundError`, `RentalNotFoundError`, `ItemNotRentableError`,
`UnpaidFinesError`, `RentalLimitExceededError`, `DuplicateRentalError`,
`ItemNotAvailableError`, `ExtensionNotAllowedError`, `WaitingListError`,
`UndoNotPossibleError` (Phase 2), `StorageError` (Phase 3).

## Design

- [docs/class_diagram.md](docs/class_diagram.md): class diagram, inheritance vs composition, CRC cards
- [docs/benchmark_report.md](docs/benchmark_report.md): Phase 2 measurements
- [docs/normalisation.md](docs/normalisation.md), [docs/index_report.md](docs/index_report.md): Phase 3
- [DECISIONS.md](DECISIONS.md): every design decision and the alternatives rejected
