# GearShare Mini

GearShare Mini is a small rental system for FrameWorks Gear Rental, a shop that
lends cameras, lenses, drones, tripods and microphones to students and
creators. Until now they kept everything in a paper register. This project
replaces it in four steps:

| Phase | What I built | Status |
|-------|--------------|--------|
| 1 | Python + OOP: a console program that enforces the Rental Rulebook | Done |
| 2 | DSA: made it fast with proper data structures, and measured it | Done |
| 3 | SQL: moved everything into a SQLite database | Done |
| 4 | React + API: a website for customers, on top of a FastAPI server | Done |

Each phase builds on the one before, and all the earlier tests still pass.

## What you need

- Python 3.12 or newer (I used 3.14)
- Node.js 20.19 or newer for the website (I used Node 24)
- Git

## Getting started

From a fresh clone:

```powershell
git clone <repo-url> Mini-GearShare
cd Mini-GearShare
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # on macOS / Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m sql.setup_db              # creates data/gearshare.db with the starter data
```

You can run `python -m sql.setup_db` again at any time to reset the shop to
the starter data.

> **Note:** run the SQL scripts as modules (`python -m sql.setup_db`, not
> `python sql/setup_db.py`) and the tests with `python -m pytest`. On my laptop a
> security rule stops a plain `python file.py` from opening `.sql` files.
> DECISIONS.md (D22) has the details.

## Running the console

All the samples in the spec use **2026-11-03** as today's date. You set it with
the `TODAY` environment variable. Without it, the program uses the real date.

```powershell
# Windows PowerShell
$env:TODAY="2026-11-03"; python main.py
```

```bash
# bash / macOS / Linux
TODAY=2026-11-03 python main.py
```

In PowerShell, `$env:TODAY` stays set until you close the terminal
(`Remove-Item Env:TODAY` clears it).

The menu has options 1 to 9: list, search, rent, return, extend, join the
waiting list, a customer's rentals, the overdue report and undo. Rentals are
saved, so they are still there the next time you start the program.

## Running the website

You need two terminals.

**Terminal 1, the API** (http://localhost:8000, with interactive docs at `/docs`):

```powershell
$env:TODAY="2026-11-03"; python -m uvicorn api.main:app --reload --port 8000
```

**Terminal 2, the website** (http://localhost:5173):

```powershell
cd web
npm install          # only the first time
npm run dev
```

Then open **http://localhost:5173**. A few things to know:

- Use `localhost`, not `127.0.0.1`. The API only accepts requests from
  `http://localhost:5173` (CORS).
- The website finds the API through `VITE_API_URL` in `web/.env`. It defaults to
  `http://localhost:8000`; see `web/.env.example`.
- Don't run the console and the API at the same time. Each one keeps its own
  copy of the shop in memory, so they would get out of sync (D26).

## Tests

```powershell
python -m pytest -q          # 228 tests: engine, database and API
cd web; npm test             # 8 tests: basket and form logic
```

Each Python test gets its own fresh temporary database, so the tests never
depend on each other. `tests/test_main.py` types every sample session from the
spec into the real menu and checks the output line by line.

## Phase by phase

### Phase 2: data structures

The menu got an undo option (9). Each `dsa/` module prints its part of the
spec's samples:

```powershell
python -m dsa.search          # binary search, with comparison counts
python -m dsa.sorting         # bubble / insertion / selection sort, pass by pass
python -m dsa.hashing         # group by tag, most rented, packing challenge
python -m dsa.history         # rental history as a linked list
python -m dsa.categories      # recursion and the category tree
python import_gear.py gear_with_duplicate.csv
```

The benchmarks, with my results in [docs/benchmark_report.md](docs/benchmark_report.md):

```powershell
python benchmarks/generate_data.py 10000      # make a fake shop of any size
python benchmarks/benchmark_engine.py         # 2.1: engine operations at 1k-50k items
python benchmarks/benchmark_sorts.py          # 2.2: searches and sorts (about a minute)
python benchmarks/benchmark_word_index.py     # 2.3: the word index (stretch task)
python benchmarks/benchmark_queue.py          # 2.4: list.pop(0) vs deque.popleft()
```

### Phase 3: the database

```powershell
python -m sql.setup_db                        # create or reset: schema, seed data, indexes
python -m sql.run_sql sql/queries.sql         # the 12 business questions
python -m sql.run_sql sql/tx_demo.sql         # renting as one transaction, and a rollback
python -m sql.index_report --explain Q12 Q5   # 100,000 rentals, EXPLAIN before and after
python -m sql.injection_demo                  # the SQL injection experiment
python -m sql.build_flat                      # rebuilds data/gearshare_flat.csv
```

Write-ups for this phase:
- [docs/normalisation.md](docs/normalisation.md): the flat file, its anomalies, and 1NF → 2NF → 3NF
- [docs/GearShare_ER_Diagram.png](docs/GearShare_ER_Diagram.png): the ER diagram, drawn in dbdiagram.io
- [docs/index_report.md](docs/index_report.md): EXPLAIN before and after, and the index I didn't add
- [docs/query_results.txt](docs/query_results.txt) and [docs/injection_evidence.txt](docs/injection_evidence.txt): saved output

### Phase 4: the website

- [docs/wireframes.md](docs/wireframes.md): the five screens
- [docs/component_tree.md](docs/component_tree.md): the React components, and where each piece of state lives
- [docs/behaviour_table.md](docs/behaviour_table.md): the spec's behaviour table, all 16 rows checked in the browser

The test output for every phase is saved in `docs/pytest_phase1.txt` to
`docs/pytest_phase4.txt`.

## Project layout

```
main.py         the console menu (input and output only, no rules)
gearshare.py    the GearShare service, which enforces the Rulebook
items.py        GearItem (abstract) -> Equipment, Accessory, DisplayItem
customers.py    Customer (abstract) -> BasicCustomer, PlusCustomer, ProCustomer
rentals.py      Rental and Fine
errors.py       GearShareError and its subclasses
import_gear.py  imports a gear CSV and skips duplicate SKUs (Phase 2)
dsa/            Phase 2: search, sorting, hashing, history, categories
benchmarks/     Phase 2: the fake-data generator and the timing scripts
storage/        Phase 3: the only code that talks SQL (one class per table group)
sql/            Phase 3: schema, seed, queries, tx_demo, indexes, and scripts to run them
api/            Phase 4: the FastAPI app (main.py, errors.py, schemas.py)
web/            Phase 4: the Vite + React website
data/           starter CSVs, the flat file, and gearshare.db (created locally, not in git)
docs/           diagrams, reports, write-ups and saved test output
tests/          the pytest tests
DECISIONS.md    my design decisions and the options I turned down
```

## Rulebook: where each rule is enforced and tested

| Rule | In short | Enforced by | Tested by (in `tests/`) |
|------|----------|-------------|--------------------------|
| R1 | Display items are never rented | `DisplayItem.is_rentable()`, checked in step 3 of `GearShare.rent()` | `test_gearshare.py::test_r1_display_item_cannot_be_rented`, `test_models.py::test_r1_r2_item_types_answer_differently` |
| R2 | Accessories: always 2 days, never extended | `Accessory.rental_days()` and `Accessory.can_extend()`, checked in `GearShare.extend()` | `test_models.py::test_due_dates_worked_example`, `test_gearshare.py::test_r2_accessories_cannot_be_extended` |
| R3 | No more items than the tier allows | `Customer.max_items()`, checked in step 5 of `GearShare.rent()` | `test_gearshare.py::test_r3_item_limit` |
| R4 | Unpaid fines over ₹500 block renting | `GearShare.unpaid_fines()`, checked in step 4 of `GearShare.rent()` | `test_gearshare.py::test_r4_unpaid_fines_above_500_block_renting`, `test_r4_fines_of_exactly_500_still_allowed` |
| R5 | Late fee = days late × rate, capped at the price | `Rental.late_fee()` | `test_models.py::test_late_fees_worked_example`, `test_r5_fee_never_more_than_replacement_price` |
| R6 | At most 2 extensions, none if someone is waiting | `GearShare.extend()`, `Rental.extend()`, `Rental.MAX_EXTENSIONS` | `test_gearshare.py::test_r6_extend_twice_then_refused`, `test_r6_no_extension_when_someone_is_waiting` |
| R7 | Waiting list, first come first served | `GearShare.join_waiting_list()`, `return_item()`, and step 7 of `rent()` | `test_gearshare.py::test_r7_no_unit_free`, `test_r7_first_in_waiting_list_is_served_first` |
| R8 | Only one unit of the same item per customer | step 6 of `GearShare.rent()` (the `held_skus` set) | `test_gearshare.py::test_r8_no_two_units_of_same_item` |
| R9 | A SKU is exactly 10 digits and unique | `items.validate_sku()` (the `GearItem.sku` setter) and `GearShare.add_item()`; in the database, `items.sku` is the primary key with a CHECK | `test_models.py::test_r9_sku_must_be_exactly_10_digits`, `test_gearshare.py::test_invalid_sku` |
| R10 | Returning on the due date isn't late | `Rental.days_late()` | `test_models.py::test_r10_return_on_due_date_is_not_late` |

Every custom exception has a test that expects it with `pytest.raises`:
`InvalidSKUError`, `ItemNotFoundError`, `CustomerNotFoundError`,
`RentalNotFoundError`, `ItemNotRentableError`, `UnpaidFinesError`,
`RentalLimitExceededError`, `DuplicateRentalError`, `ItemNotAvailableError`,
`ExtensionNotAllowedError`, `WaitingListError`, `UndoNotPossibleError` (added in
Phase 2) and `StorageError` (added in Phase 3).

## Design notes

- [docs/class_diagram.md](docs/class_diagram.md): the class diagram, inheritance vs composition, and CRC cards
- [docs/benchmark_report.md](docs/benchmark_report.md): what I measured in Phase 2
- [DECISIONS.md](DECISIONS.md): every design decision, with the options I considered
