# GearShare Mini: Project Handoff

**Purpose:** let a fresh Claude Code session (or a person) continue this project
without the previous conversation. Written 2026-11-03, at the start of Phase 4.

**State at handoff:**

| Item | Status |
|---|---|
| Git branch | `phase-4` (clean, created from `main`) |
| Tags | `phase-1`, `phase-2`, `phase-3` (each = a merge commit on `main`) |
| Tests | **208 passed** (`python -m pytest -q`) |
| Phases 1-3 | Done, merged, tagged |
| Phase 4 (React + API, 30 marks) | **Not started.** No `api/` or `web/` folder yet |
| Node.js / npm | Installed: v24.22.1 / 11.19.1 |
| FastAPI / uvicorn / httpx | **Not installed yet** (only `pytest` is in the venv) |
| Decisions logged | D1-D27 in `DECISIONS.md` |

The original spec PDF ("GearShare Mini: Python, DSA, SQL and React Project")
was **deleted by the user**. Everything still needed from it for Phase 4 is
copied verbatim into [section 4](#4-what-remains-phase-4-react--api-full-spec).

---

## 0. How to work with this user (read first)

The user asked for these working rules at the start, and they still apply:

1. **Follow the spec strictly.** Match sample messages, spacing and numbers exactly.
2. **One numbered task at a time** (4.0, 4.1, ... 4.7). After each task, **stop** and give:
   - a summary of what was built,
   - which lines changed in `DECISIONS.md` / `README.md`,
   - the exact git commands, **one command per code block** (long multi-command blocks confused them).
   Then wait for "done", and check with `git status` / `git log` before continuing.
3. **The user runs git and creates folders themselves.** Tell them which folders to `mkdir`. Don't commit for them.
4. **Git workflow:**
   - One commit per numbered task (the spec requires at least one).
   - Work on branch `phase-4`. At the end of the phase: `git checkout main`, `git merge --no-ff phase-4 -m "..."`, `git tag -a phase-4 -m "..."`.
   - When OneDrive asks *"Deletion of directory ... failed. Should I try again? (y/n)"* during `git checkout`, answer **n**. It's harmless.
5. **The spec demands:** `DECISIONS.md` gets at least 3 entries per phase (problem / options / chosen / why). The user must be able to explain all code, so explain the key idea at the end of each task.
6. **The user is on Windows PowerShell 5.1** inside VS Code, with the project in a OneDrive folder. Give PowerShell syntax: `$env:TODAY="2026-11-03"; python main.py`, not `TODAY=... python`.

---

## 1. Architecture and folder structure

```
Customer / Staff -> React website (web/, Phase 4) -> HTTP API (api/, Phase 4)
                 -> Python engine: GearShare (OOP + data structures, Phases 1-2)
                 -> storage/ (the only SQL code) -> SQLite data/gearshare.db (Phase 3)
```

```
Mini-GearShare/
├── main.py              console menu (I/O only, no rules). Options 1-9, 0 = exit
├── gearshare.py         GearShare service: ALL rules R1-R10, reports, undo, waiting list.
│                        Loads from storage, writes through. Contains NO SQL.
├── items.py             GearItem (ABC) -> Equipment, Accessory, DisplayItem; validate_sku(),
│                        ITEM_TYPES dict, item_from_row()
├── customers.py         Customer (ABC) -> BasicCustomer, PlusCustomer, ProCustomer; TIER_CLASSES
├── rentals.py           Rental (class-attribute ID counter, days_late, late_fee, extend), Fine,
│                        parse_date()
├── errors.py            GearShareError and its children, each with .code and .message
├── import_gear.py       Phase 2: import a gear CSV, skipping duplicate SKUs
├── dsa/                 Phase 2: search.py, sorting.py, hashing.py, history.py, categories.py
├── benchmarks/          Phase 2: generate_data.py (fake shop CSVs), benchmark_*.py
├── storage/             Phase 3: __init__.py, database.py (Database, Storage, transaction()),
│                        items.py, customers.py, rentals.py (one repository per table group),
│                        null.py (NullStorage: in-memory mode)
├── sql/                 Phase 3 (a package; run everything with python -m):
│                        schema.sql, seed.sql, queries.sql, tx_demo.sql, indexes.sql,
│                        run_sql.py, setup_db.py, build_flat.py, index_report.py,
│                        injection_demo.py
├── data/                gear.csv, customers.csv, rentals.csv, fines.csv (starter data),
│                        gear_with_duplicate.csv, gearshare_flat.csv,
│                        gearshare.db (created by setup_db, git-ignored),
│                        gearshare_big.db (100k rentals, git-ignored)
├── docs/                class_diagram.md (Mermaid + CRC), benchmark_report.md,
│                        normalisation.md, index_report.md, GearShare_ER_Diagram.png,
│                        query_results.txt, injection_evidence.txt, pytest_phase1..3.txt
├── tests/               conftest.py + 11 test files (208 tests)
├── DECISIONS.md         D1-D27
├── README.md            setup, run, Phase 2/3 commands, R1-R10 traceability table
├── PROJECT_HANDOFF.md   this file
├── requirements.txt     pytest>=8.4  (Phase 4 must add fastapi, uvicorn, httpx)
├── pytest.ini           testpaths = tests, pythonpath = .
├── .gitignore           .venv, __pycache__, *.db, node_modules/, dist/, .env,
│                        benchmarks/generated/
└── .gitattributes       * text=auto eol=lf
```

Planned for Phase 4 (folders not yet created): **`api/`** (FastAPI app) and
**`web/`** (Vite + React app).

---

## 2. What has been completed

### Phase 1: Python + OOP (25 marks), done

- **The Rulebook, enforced in `GearShare`:**

| Tier | Max items | Rental period | Late fee / day |
|---|---|---|---|
| Basic | 2 | 3 days | ₹50 |
| Plus | 4 | 5 days | ₹100 |
| Pro | 8 | 7 days | ₹150 |

  - R1: display items never rented
  - R2: accessories always 2 days, never extended
  - R3: tier item limit
  - R4: unpaid fines **above** ₹500 block renting
  - R5: fee = days late × rate, capped at the item price
  - R6: max 2 extensions; each adds the tier period; none if someone is waiting
  - R7: waiting list, first come first served
  - R8: one unit of the same item per customer
  - R9: SKU exactly 10 digits, unique
  - R10: returning on the due date is not late
- **Order of checks in `rent()`** (the first failure is reported):
  1. customer exists
  2. SKU valid and exists
  3. R1
  4. R4
  5. R3
  6. R8
  7. availability (R7)
- **Polymorphism:** no `if tier ==` anywhere. Tier and type behaviour come from subclass methods, and CSV strings map to classes through the dicts `TIER_CLASSES` / `ITEM_TYPES`.
- **Validation:** `@property` setters reject a bad SKU (`InvalidSKUError`), a blank name, an email without `@`, and negative units/prices/fines (`ValueError`).
- **Pythonic layer:**
  - the `@audit` decorator (it now also wraps each operation in a database transaction);
  - the generator `iter_overdue(today)`;
  - reports built with comprehensions, `sorted(key=lambda)` and `map`/`filter`: `overdue_report`, `items_by_category`, `customers_with_unpaid_fines`.
- `today` is always a parameter. `main.py` reads the `TODAY` env var (falling back to the real date).
- **Every sample transcript in the spec reproduces exactly.** `tests/test_main.py` replays them through the real menu.

### Phase 2: DSA (20 marks), done

- 2.1 Complexity audit. Indexes added (`open_rentals`, `rentals_by_customer`, `fines_by_rental`) made `rent`/`return` O(1). See `docs/benchmark_report.md`.
- 2.2 Linear and binary search (with comparison counts), bubble/insertion/selection sort by hand (printing each pass), and the catalogue sort (top-level category ↑, weight ↓, name ↑).
- 2.3 Hashing: duplicate SKUs, group by tag, most rented, two-sum packing challenge, and the stretch `WordIndex`.
- 2.4 Undo stack (menu option 9, `deque(maxlen=20)`), waiting list as a `deque`, rental history as a linked list.
- 2.5 Recursion: warm-ups, the category tree (print/count/path), iterative versions, and the recursion-limit experiment.

### Phase 3: SQL (25 marks), done

- 3.1 `data/gearshare_flat.csv`, plus update/insert/delete anomalies using real rows.
- 3.2 1NF → 2NF → 3NF write-up (`docs/normalisation.md`).
- 3.3 `sql/schema.sql` (10 tables) and the ER diagram PNG.
- 3.4 `sql/seed.sql`. Counts: 7 items, 10 tags, 5 customers, 10 rentals, 4 fines, 8 categories, 3 open rentals.
- 3.5 `sql/queries.sql`: 12 queries, all matching the expected output (tested).
- 3.6 `sql/tx_demo.sql` (a rollback leaves no trace) and `sql/indexes.sql`: one covering index, chosen over three measured rounds (`docs/index_report.md`).
- 3.7 `storage/` package. `GearShare` loads from SQLite and writes through, with one transaction per operation. All tests run on a fresh temporary database. A rental survives a restart.
- 3.8 SQL injection experiment (`python -m sql.injection_demo`).

---

## 3. Implemented features and their current status

| Feature | Where | Status |
|---|---|---|
| Catalogue list / search (name or tag, case-insensitive, substring) | `GearShare.list_items()`, `.search(text)` | ✅ |
| Rent with ordered checks | `GearShare.rent(customer_id, sku, today)` → `Rental` | ✅ persisted |
| Return with late fee, fine, serving the waiting list | `GearShare.return_item(rental_id, today)` → `ReturnReceipt(rental, days_late, fee, next_customer)` | ✅ persisted |
| Extend (R2/R6) | `GearShare.extend(rental_id, today)` → `Rental` | ✅ persisted |
| Join waiting list | `GearShare.join_waiting_list(customer_id, sku)` → position (int) | ✅ persisted |
| Undo latest rent/return | `GearShare.undo()` → `(action, rental)` or `None` | ✅ persisted |
| Customer's open rentals | `GearShare.customer_rentals(customer_id)` → `[Rental]` | ✅ |
| Unpaid fines | `GearShare.unpaid_fines(customer_id)` → int | ✅ |
| Overdue report | `GearShare.overdue_report(today)` → `[(rental, days, fine_so_far)]` | ✅ |
| Add item (staff) | `GearShare.add_item(item)` (raises `ValueError` on a duplicate SKU) | ✅ persisted |
| Catalogue sort for the website | `dsa.sorting.catalogue_sort(items)` | ✅ |
| Audit log | `GearShare.audit_log` + the `audit_log` table | ✅ |
| Waiting list display | `GearShare.waiting_list(sku)` → `[Customer]` | ✅ |
| Paying fines | (none) | ❌ not in the spec, not implemented |

**Useful object attributes for the API's JSON:**
- `GearItem`: `.sku`, `.name`, `.tags` (list), `.category` (leaf, e.g. "Cameras"), `.parent_category`, `.top_category`, `.weight_g`, `.price`, `.total_units`, `.available_units`, `.type_name()` → "Equipment"/"Accessory"/"Display", `.is_rentable()`, `.availability_text()`.
- `Customer`: `.customer_id`, `.name`, `.email`, `.tier_name()`, `.max_items()`, `.rental_period()`, `.late_fee_per_day()`.
- `Rental`: `.rental_id`, `.customer`, `.item`, `.issue_date`, `.due_date` (date objects), `.return_date`, `.extensions`, `.is_open()`, `.is_overdue(today)`, `.days_late(today)`, `.late_fee(today)`.

**Error classes and codes** (in `errors.py`; every one has `.code` and `.message`):

| Class | `.code` | Typical message |
|---|---|---|
| `InvalidSKUError` | `InvalidSKUError` | `SKU must be exactly 10 digits.` |
| `ItemNotFoundError` | `ItemNotFoundError` | `No item with SKU 1000000999.` |
| `CustomerNotFoundError` | `CustomerNotFoundError` | `No customer with ID C009.` |
| `RentalNotFoundError` | `RentalNotFoundError` | `No open rental with ID RN004.` |
| `ItemNotRentableError` | `R1` | `'Vintage Leica (Showcase)' is a display item and cannot be rented.` |
| `UnpaidFinesError` | `R4` | `Rohan Das has unpaid fines of ₹600 (limit ₹500).` |
| `RentalLimitExceededError` | `R3` | `Ananya Nair already has 2 of 2 items on rental.` |
| `DuplicateRentalError` | `R8` | `Ananya Nair already has a unit of 'Sony 50mm Lens'.` |
| `ItemNotAvailableError` | `R7` | `No units of 'DJI Mini Drone' are available.` |
| `WaitingListError` | `R7` | `... is already on the waiting list ...` / `... has a unit available. Rent it instead.` |
| `ExtensionNotAllowedError` | `R2` or `R6` | `Accessories cannot be extended.` / `... already been extended 2 times.` / `... because another customer is waiting.` |
| `UndoNotPossibleError` | `UndoNotPossibleError` | `Cannot undo ...` |
| `StorageError` | `StorageError` | `Database error: ...` / `No database at ...` |

---

## 4. What remains: Phase 4, React + API (full spec)

**Training phase: React JS | Marks: 30.** The spec text below is copied from
the deleted PDF, so treat it as the specification.

> **The task.** Customers can't use a console program. The owner wants a website where customers search the catalogue, see what is available, fill a rental basket and view their own rentals. This is the small, real-shaped full-stack app: a React front end, an HTTP API in front of your Python engine, and your database underneath.

### 4.0 Put an HTTP API in front of your engine
- FastAPI (recommended) or Flask.
- Create the endpoints in the sample below. Each one calls the existing `GearShare` methods. **Do not copy rules into the API.**
- Convert every custom exception into an HTTP status and a JSON body `{"error": "R3", "message": "..."}`, using the **same message text as the console**. Decide for each exception which status fits, and write why.
- Allow requests only from the origin of the React development server (CORS). Read `TODAY` from the environment as before.
- Hint: 404 = the thing doesn't exist; 409 = it exists but its state conflicts with the request; 422 = the input itself doesn't make sense.

### 4.1 Set up and wireframe
- Create a Vite React app in `web/`. Keep the API URL in an environment variable.
- Sketch five screens on paper: Catalogue, Item details, My rentals, Rental basket, Add item (staff).
- Draw the component tree. Next to every component, write the state it owns and the props it receives.

### 4.2 Components and props
- Build `Navbar`, `Layout` (using `children`), `GearCard`, `GearList` and `AvailabilityBadge`, with hard-coded JSON first.
- Every component receives what it needs through props and knows nothing about where the data came from.

### 4.3 State, events and effects
- A controlled search box, a category filter and a sort dropdown that all control the same list.
- Fetch from the API in `useEffect` with a correct dependency array. **Debounce** typing, and **cancel the old request in the cleanup function** (`AbortController`).
- Throttle the network to "Slow 3G" in browser tools and type quickly. Does an old response ever overwrite a newer one? Fix it if it does.

### 4.4 Conditional rendering, lists and forms
- Different UI for **loading, error, empty and results**. Show "Join waiting list" instead of "Add to basket" when nothing is available.
- Render lists with a stable `key` (the SKU). Be ready to explain what goes wrong with the array index.
- The staff **Add item** form uses controlled inputs and validation: SKU exactly 10 digits, units at least 1, name required. Errors appear next to the field, and submit stays disabled until the form is valid.

### 4.5 Routing
- Routes: `/` catalogue, `/gear/:sku` details, `/me` my rentals, `/basket`, `/admin/add`, plus a friendly 404 page.
- A "Back to results" link must restore the previous search. (Where must the search text live? Answer: in the URL query string, e.g. `/?q=drone&category=Drones&sort=name`, via `useSearchParams`.)

### 4.6 State beyond useState
- A `CustomerContext` that holds "who am I" (a customer picker in the navbar is enough; no passwords).
- The basket uses `useReducer` with actions `ADD`, `REMOVE` and `CLEAR`. It blocks adding more than the customer's limit (2 / 4 / 8) with a message.
- On checkout, call `POST /rentals` for each item. **The server has the last word.** Show its message to the customer exactly.

### 4.7 Styling, responsiveness, polish
- Pick Tailwind or Material UI and use it consistently.
- Every screen must work at 360 px width. Every input has a label, every image an `alt`, and every action is reachable by keyboard.

### Sample API requests and responses (`TODAY=2026-11-03`), verbatim

```
GET /gear?q=drone&sort=name
200 [
  {"sku": "1000000003", "name": "DJI Mini Drone",
   "tags": ["video", "aerial"], "category": "Drones",
   "item_type": "Equipment", "available": 0, "total": 1, "weight_g": 249}
]

GET /gear?q=zzz
200 []

GET /gear/1000000999
404 {"error": "ItemNotFoundError", "message": "No item with SKU 1000000999."}

POST /rentals
{"customer_id": "C001", "sku": "1000000002"}
201 {"rental_id": "RN011", "due_date": "2026-11-06"}

POST /rentals            (same body again)
409 {"error": "R8", "message": "Ananya Nair already has a unit of 'Sony 50mm Lens'."}

POST /rentals
{"customer_id": "C004", "sku": "1000000004"}
409 {"error": "R4", "message": "Rohan Das has unpaid fines of ₹600 (limit ₹500)."}

POST /rentals
{"customer_id": "C003", "sku": "1000000006"}
409 {"error": "R1", "message": "'Vintage Leica (Showcase)' is a display item and cannot be rented."}

POST /rentals
{"customer_id": "C009", "sku": "1000000002"}
404 {"error": "CustomerNotFoundError", "message": "No customer with ID C009."}

POST /rentals
{"customer_id": "C001", "sku": "123"}
422 {"error": "InvalidSKUError", "message": "SKU must be exactly 10 digits."}

POST /rentals/RN001/return
200 {"rental_id": "RN001", "days_late": 5, "fine": 500,
     "next_in_waiting_list": "Meera Joshi"}      (null if nobody is waiting)

GET /customers/C002/rentals
200 {"customer": "Vikram Shah", "membership_type": "Plus",
     "max_items": 4, "unpaid_fines": 0,
     "active": [{"rental_id": "RN001", "item": "DJI Mini Drone",
                 "due_date": "2026-10-29", "days_overdue": 5}]}
```
*"If the status codes you choose differ from these, explain why in DECISIONS.md. The error messages must match."*

### Catalogue wireframe (from the spec)

```
+---------------------------------------------------------------------+
| GearShare Mini   Catalogue  My rentals  Basket (2)  [Ananya Nair v]  |
+---------------------------------------------------------------------+
| Search [ drone______ ]  Category [All v]  Sort [Name v]             |
|                                                                     |
| 1 result                                                            |
| +-----------------------------+                                     |
| | DJI Mini Drone              |                                     |
| | video, aerial               |                                     |
| | Drones                      |                                     |
| | 0 of 1 available            |                                     |
| | [Join waiting list]         |                                     |
| +-----------------------------+                                     |
+---------------------------------------------------------------------+
```

### Behaviour table: what the screen must do (the spec's acceptance checklist)

| Action | Expected result |
|---|---|
| Open `/` | Spinner `Loading catalogue...` then 7 cards |
| Type `drone` | List shows only DJI Mini Drone. Text: `1 result` |
| Type `zzz` | `No items match 'zzz'. Try a different word.` |
| Click the Sony 50mm Lens card | URL becomes `/gear/1000000002`. Shows `1 of 1 available` |
| Open DJI Mini Drone | `0 of 1 available`. Button reads `Join waiting list` |
| Open Vintage Leica (Showcase) | `Display item: view in the shop only`. No rent button |
| Pick Ananya (Basic). Add 2 items, try a 3rd | Message: `Basket full: Basic members can rent 2 items.` 3rd button disabled |
| Click Rent with a valid basket | Button shows `Renting...` then toast: `Rented Sony 50mm Lens. Due 2026-11-06.` |
| Back on the catalogue after renting | Sony 50mm Lens now shows `0 of 1 available` |
| Pick Rohan. Try to rent Manfrotto Tripod | Red message from the server: `Rohan Das has unpaid fines of ₹600 (limit ₹500).` |
| Pick Vikram. Open My rentals | Table row: DJI Mini Drone, due 2026-10-29, `OVERDUE (5 days)` |
| Stop the API server, reload | `Can't reach the rental server.` with a Retry button |
| Open `/nothing` | 404 page with a link back to the catalogue |
| Add item: SKU `123` | Under the field: `SKU must be exactly 10 digits.` Submit disabled |
| Add item: all fields valid | Success message, form clears, item appears in the catalogue |
| Resize to 360 px wide | One column of cards, nothing cut off, no sideways scrolling |

### Think-about questions (Phase 4; answer them in DECISIONS / the explanation session)
1. The basket limit exists in React and in Python. Why is each useful, and which one must never be removed? *(Python: the server is the authority.)*
2. Two customers rent the last unit at the same moment. What does the second customer see, and is it true?
3. Which component would suffer most from prop drilling without context? What would you change?
4. What does each screen say when the API is down? Would a non-technical customer understand it?

### What to hand in (Phase 4)
- `api/` and `web/` folders, with a README that explains how to start both
- Component tree diagram and a note on where each piece of state lives
- A 2-minute screen recording, or screenshots of all five screens, including loading, empty and error states
- The behaviour table above, ticked off, with a note on anything that doesn't work yet
- `DECISIONS.md`: Tailwind vs MUI, where search state lives, status code choices

### You are done when
- A customer can search, open an item, fill the basket and rent it end to end against the real API and database
- Every screen that fetches data handles loading, empty and error
- An old response never overwrites a newer one
- Everything in the behaviour table works

### Scoring (whole project, 100 marks)
P1 Python + OOP 25 · P2 DSA 20 · P3 Database 25 · **P4 React 30**: API plus website work end to end; every behaviour-table row passes; states handled; race condition handled; basic accessibility.

---

## 5. Backend API: endpoints and integration requirements

### 5.1 Endpoints to build (the spec's samples, plus what the screens need)

| Method + path | Calls | Success | Notes |
|---|---|---|---|
| `GET /gear?q=&category=&sort=` | `shop.search(q)` or `shop.list_items()`, then filter + sort | 200 `[item, ...]` | Item JSON exactly: `sku, name, tags, category, item_type, available, total, weight_g`. `category` is the **leaf** category ("Drones", "Cameras"). `sort=name` must work; suggested extras: `sort=catalogue` (`dsa.sorting.catalogue_sort`), `sort=weight`. |
| `GET /gear/{sku}` | `shop.get_item(sku)` | 200 item JSON | 404 sample above; 422 for a bad SKU. The details screen also needs `price` and maybe `top_category`; adding fields is fine. |
| `POST /rentals` body `{customer_id, sku}` | `shop.rent(cid, sku, TODAY)` | **201** `{"rental_id", "due_date"}` | Errors as in the samples |
| `POST /rentals/{rental_id}/return` | `shop.return_item(rid, TODAY)` | 200 `{"rental_id", "days_late", "fine", "next_in_waiting_list"}` | `next_in_waiting_list` = the customer's name or `null` |
| `GET /customers/{id}/rentals` | `get_customer`, `customer_rentals`, `unpaid_fines` | 200 (shape above) | `days_overdue` = `rental.days_late(TODAY)` (0 when not overdue) |
| `GET /customers` | `shop.customers.values()` | 200 `[{customer_id, name, membership_type, max_items}]` | **Not in the spec, but needed** for the navbar customer picker and the basket limit |
| `POST /waiting-list` body `{customer_id, sku}` | `shop.join_waiting_list` | 201 `{"position": 1}` | Needed for the "Join waiting list" button |
| `POST /gear` body `{sku, name, tags, category, parent_category, item_type, weight_g, price, total_units}` | build with `items.ITEM_TYPES[item_type](...)`, then `shop.add_item(item)` | 201 item JSON | For `/admin/add`. A duplicate SKU raises `ValueError`, so map it to 409. A bad SKU raises `InvalidSKUError` (422). |
| (optional) `POST /rentals/{id}/extend`, `POST /undo`, `GET /overdue` | existing methods | | Not required by the screens |

### 5.2 Status code mapping (recommended; matches every spec sample)

| Exception | Status | Why |
|---|---|---|
| `InvalidSKUError` | **422** | The input itself is malformed |
| `CustomerNotFoundError`, `ItemNotFoundError`, `RentalNotFoundError` | **404** | The thing doesn't exist |
| `ItemNotRentableError` (R1), `UnpaidFinesError` (R4), `RentalLimitExceededError` (R3), `DuplicateRentalError` (R8), `ItemNotAvailableError` (R7), `WaitingListError` (R7), `ExtensionNotAllowedError` (R2/R6), `UndoNotPossibleError` | **409** | The things exist, but their state conflicts with the request |
| `ValueError` from `add_item` (duplicate SKU) | **409** | The SKU already exists |
| `ValueError` from model setters (blank name, negative units) | **422** | Bad input |
| `StorageError` | **503** (or 500) | The server can't save right now |

Implement this **once**, as a FastAPI exception handler for `GearShareError`
plus a `{class: status}` dict. Body: `{"error": e.code, "message": e.message}`.
Note that `e.code` is already `"R3"` for rule errors and the class name for the others.

**Pydantic gotcha:** FastAPI's own 422 for a missing or mistyped JSON field has
a different body shape (`{"detail": [...]}`). Either override
`RequestValidationError` to return `{"error": "ValidationError", "message": ...}`,
or accept it and note it in DECISIONS. The spec sample `{"sku": "123"}` is a
valid string, so it reaches `GearShare` and correctly gives `InvalidSKUError`.
**Don't** add a Pydantic `pattern` on `sku`, or that sample would get
FastAPI's 422 instead of the spec's body.

### 5.3 Integration requirements and gotchas

1. **One `GearShare` per API process**, created at start-up (FastAPI `lifespan`): `storage = Storage(DB_PATH); shop = GearShare(storage); shop.load_data()`. Close the storage on shutdown.
2. **SQLite and threads (must fix before the API works):** FastAPI runs plain `def` endpoints in a **thread pool**, but `storage/database.py` opens the connection with the default `check_same_thread=True`. That raises `ProgrammingError: SQLite objects created in a thread can only be used in that same thread`. Choose one fix and record it in DECISIONS:
   - (a) make every endpoint `async def`, so all of them run on the event-loop thread (simplest; the calls are fast); or
   - (b) add `check_same_thread=False` in `Database.__init__` **plus** a `threading.Lock` around each `GearShare` call, since `GearShare`'s memory isn't thread-safe either.

   Option (a) also serialises requests, which keeps GearShare's in-memory state consistent.
3. **`TODAY`:** read it once with `main.today_from_env(os.environ)` (reuse it rather than duplicating it). Pass `today` into `rent` / `return_item` / `extend`.
4. **CORS:** `CORSMiddleware` with `allow_origins=["http://localhost:5173"]` (Vite's default dev origin), ideally read from an env var. Not `*`.
5. **Write-through cache caveat (D26):** each process keeps its own in-memory copy of the shop. **Don't run the console (`main.py`) and the API at the same time against the same database**, or each will have stale data. A rental ID collision would be caught by the database (UNIQUE → `StorageError` → automatic reload), but the counts shown could be stale. Run one at a time, or restart the API after using the console.
6. **Rental IDs** come from the class attribute `Rental._next_number`, reset from the database on `load_data()`. That's fine with one API process.
7. **Laptop security rule (D22):** a Python process started as `python something.py` (and the `pytest.exe` / likely `uvicorn.exe` launchers) **cannot read `.sql` files**. The API never reads `.sql` files (the database already exists), so it's fine. Still, start it as a module to be safe: `python -m uvicorn api.main:app --reload --port 8000`. API tests run under `python -m pytest`, where the fixtures read the `.sql` files, which is allowed.
8. **API tests:** use `fastapi.testclient.TestClient` (needs `httpx`). Build the app with a factory, `create_app(db_path, today)`, so tests can inject the per-test temporary database from `tests/conftest.py` (the `db_path` fixture). Add `tests/test_api.py` covering every sample request above.

---

## 6. Database schema and connectivity

- **Engine:** SQLite. File `data/gearshare.db` (git-ignored). Create or reset it with `python -m sql.setup_db`, which runs `schema.sql`, then `seed.sql`, then `indexes.sql`.
- **Tables (10)**, keys and the important constraints:

| Table | Key | Notes |
|---|---|---|
| `membership_tiers` | tier | max_items, rental_days, late_fee_per_day |
| `customers` | customer_id (`C...`) | name, email UNIQUE + contains `@`, tier → membership_tiers (RESTRICT) |
| `categories` | category_id | name UNIQUE, parent_id → categories (self-reference, RESTRICT). Photography is the parent of Cameras and Lenses. |
| `items` | sku (10 digits, CHECK) | name, category_id → categories, item_type IN (Equipment, Accessory, Display), weight_g, price, total_units ≥ 0 |
| `tags` | tag_id | name UNIQUE |
| `item_tags` | (sku, tag_id) | CASCADE on both. **Tag order = rowid** (insertion order), so the "video, aerial" order is kept. |
| `rentals` | rental_id (`RN...`) | customer_id / sku (RESTRICT), ISO date text with `CHECK (date(x) IS x)`, due ≥ issue, extensions 0..2 |
| `fines` | rental_id → rentals (RESTRICT) | amount ≥ 0, paid 0/1 |
| `waiting_list` | entry_id AUTOINCREMENT | sku, customer_id (CASCADE), joined_at, status IN (waiting, reserved), UNIQUE(sku, customer_id) |
| `audit_log` | log_id | **No foreign keys on purpose** (history outlives rows). action IN (rent, return_item, extend, undo_rent, undo_return) |

- **Index:** `idx_rentals_sku_covering ON rentals(sku, return_date, issue_date, customer_id, rental_id)`.
- **Python access:** only through `storage/`:
  - `Storage(path)` exposes `.items` (`all()`, `add(item)`), `.customers` (`all()`) and `.rentals` (`all()`, `add`, `update`, `delete`, `all_fines`, `add_fine`, `delete_fine`, `all_waiting`, `add_waiting`, `set_waiting_status`, `remove_waiting`, `all_audit`, `add_audit`), plus `.transaction()` and `.close()`.
  - `Database` uses `isolation_level=None`, `PRAGMA foreign_keys = ON`, `row_factory = sqlite3.Row`, and wraps `sqlite3.Error` in `StorageError`.
  - `transaction()` is nestable (`BEGIN IMMEDIATE` / `COMMIT` / `ROLLBACK`).
- **`GearShare(storage)` modes:**
  - `GearShare(Storage(path))` + `load_data()` loads from the database and writes through.
  - `GearShare()` (`NullStorage`) + `load_data(folder)` runs in memory from CSVs. Phase 2 benchmarks and demos use this.
- On any `StorageError` inside an operation, the transaction rolls back **and** `GearShare` reloads itself from the database.

---

## 7. Commands

All from the project root, in PowerShell, with the venv active (`.\.venv\Scripts\Activate.ps1`).

```powershell
# setup (clean copy)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt          # if pip can't reach pypi.org: .\.venv\Scripts\python.exe -m pip install ...
python -m sql.setup_db                   # create / reset data/gearshare.db

# console
$env:TODAY="2026-11-03"; python main.py

# tests (ALWAYS python -m pytest, never plain pytest)
python -m pytest -q                      # expect 208 passed (before Phase 4)

# Phase 2 demos and benchmarks
python -m dsa.search
python -m dsa.sorting
python -m dsa.hashing
python -m dsa.history
python -m dsa.categories
python import_gear.py gear_with_duplicate.csv
python benchmarks/benchmark_engine.py    # also: benchmark_sorts.py, benchmark_word_index.py, benchmark_queue.py

# Phase 3
python -m sql.run_sql sql/queries.sql
python -m sql.run_sql sql/tx_demo.sql
python -m sql.index_report --explain Q12 Q5     # ~1 minute
python -m sql.injection_demo
python -m sql.build_flat

# Phase 4 (planned, not yet existing)
pip install fastapi uvicorn httpx        # then add them to requirements.txt
python -m uvicorn api.main:app --reload --port 8000
cd web; npm install; npm run dev         # Vite on http://localhost:5173
```

---

## 8. Known issues, quirks and pending fixes

There are no failing tests. All 208 pass. These are the things a new session must know:

| # | Issue | Impact / what to do |
|---|---|---|
| 1 | **Laptop security rule:** `python file.py` can't read `.sql` files (`PermissionError: [Errno 13]`), even outside OneDrive; `python -m ...` and `python -c` can. | Run SQL scripts as modules and tests with `python -m pytest`. Don't make `main.py` or the API read `.sql`. (D22) |
| 2 | **SQLite `check_same_thread`** | Must be handled for FastAPI (section 5.3, item 2). **Pending.** |
| 3 | **Write-through cache:** two processes on one database don't see each other's changes | Don't run the console and the API together (section 5.3, item 5). Documented in D26. |
| 4 | **Piping input in PowerShell** (`"3`n..." \| python main.py`) adds a BOM, so the first menu choice is "invalid" | Only affects piped testing, not real typing. Use the bash pipe or the transcript tests. |
| 5 | **pip / npm network is flaky** on this laptop (DNS `getaddrinfo failed` at times) | Retry, open a fresh terminal, or use `.\.venv\Scripts\python.exe -m pip install ...`. `npm install` may need retrying too. |
| 6 | **OneDrive** prompts "Deletion of directory failed" on `git checkout main` | Answer `n`. Harmless. |
| 7 | **Undo of a rent that used a reservation** re-inserts the waiting row with a new `entry_id` | If several people hold reservations for the same item, the restored one moves behind them. A rare edge case, not fixed. |
| 8 | **Tag order relies on `item_tags.rowid`** | Fine for inserts. A position column would be more explicit (not done, to keep the ER diagram unchanged). |
| 9 | **Fines can't be paid** (there's no method) | Not in the spec. R4 only ever increases. |
| 10 | `docs/query_results.txt`, `injection_evidence.txt` and `pytest_phase*.txt` were written by PowerShell 5.1 `Out-File -Encoding utf8` | They have a BOM and CRLF. Cosmetic only. |
| 11 | **For Claude's own Bash tool:** heredocs with apostrophes inside Python strings sometimes fail to parse ("unexpected EOF") | Use the Write/Edit tools, or write a script file to the scratchpad and run it. |
| 12 | `sql/index_report.py` builds SQL as `"EXPLAIN QUERY PLAN " + sql` (trusted, not user input) | A documented exception in D27. The only other string-built SQL is the deliberate `sql/injection_demo.py`. |

**Pending for Phase 4 (not bugs):** `api/`, `web/`, the FastAPI deps in
`requirements.txt`, the API tests, the README Phase 4 section, at least 3
DECISIONS entries, the screenshots, the component tree, and the ticked behaviour table.

---

## 9. Important files and dependencies

**Python:** 3.14.8 (3.12+ works). Packages in `requirements.txt`: `pytest>=8.4`
(9.2.0 installed). The standard library covers everything else (`sqlite3`,
`csv`, `dataclasses`, `collections`, `contextlib`).

**Phase 4 will add:**
- Python: `fastapi`, `uvicorn`, `httpx` (for `TestClient`).
- Node: `vite` + `react` + `react-dom` (from `npm create vite@latest web -- --template react`), and `react-router-dom`.
- Styling: Tailwind (`tailwindcss` + `@tailwindcss/vite`) **or** MUI. Choose one and log it in DECISIONS.
- `web/.env`: `VITE_API_URL=http://localhost:8000`. Commit a `web/.env.example`; `.env` is git-ignored.

**Files a new session should read first:**
1. this file
2. `gearshare.py` (all rules and the public methods the API will call)
3. `errors.py`
4. `storage/database.py`
5. `main.py` (`today_from_env`, the message formats)
6. `tests/conftest.py` (fixtures: `template_db`, `db_path`, `shop`, `today`)
7. `DECISIONS.md` (D1-D27; the API must not contradict them)

**Decisions so far (one line each):**
- D1 tiers as subclasses
- D2 item types as subclasses
- D3 the fee is calculated in `Rental`
- D4 class-attribute rental counter
- D5 validation errors + `RentalNotFoundError`
- D6 collections per use
- D7 the reservation meaning of R7
- D8 `@audit` decorator, real-clock time
- D9 Phase 2 indexes
- D10 catalogue sort with a tuple key
- D11 hand sorts return a copy
- D12 word index kept separate
- D13 two-sum dict
- D14 undo entry contents
- D15 deque waiting list
- D16 menu option 9
- D17 recursive + iterative tree
- D18 SQLite
- D19 availability calculated
- D20 ON DELETE choices
- D21 `CHECK` uses `IS`
- D22 run scripts with `-m`
- D23 Q11 display item
- D24 join choices
- D25 covering index
- D26 load once, write through
- D27 parameterised queries

---

## 10. Exact next steps to finish Phase 4

Follow the working rules in section 0: one task, then summary + git commands, then wait for "done".

**Step 0 (user):**
- `mkdir api` (and later `web` is created by Vite).
- `pip install fastapi uvicorn httpx`, then add `fastapi`, `uvicorn` and `httpx` to `requirements.txt`.
- Confirm the branch is `phase-4`.

**4.0 API (`api/`)**
1. `api/__init__.py`, and `api/main.py` with `create_app(db_path=DB_PATH, today=None)` plus a module-level `app = create_app()`.
2. A lifespan that opens `Storage`, creates `GearShare(storage)` and calls `load_data()`; on shutdown, `storage.close()`.
3. `api/errors.py`: a `{ExceptionClass: status}` dict + an exception handler giving `{"error": e.code, "message": e.message}`. Also handle `ValueError` from `add_item` (409) and from model setters (422).
4. `api/schemas.py`: Pydantic bodies `RentalRequest(customer_id: str, sku: str)`, `WaitingListRequest`, `NewItem`. **No regex on `sku`** (see 5.2).
5. Endpoints from section 5.1. Use `async def`, or handle threads as in 5.3 item 2.
6. CORS for `http://localhost:5173`, and `TODAY` via `main.today_from_env`.
7. `tests/test_api.py` with `TestClient` + the `db_path` fixture: every sample request/response in section 4, **exact bodies**. Keep all 208 earlier tests green.
8. DECISIONS (D28+): status code per exception, why `async`/thread handling, why `GET /customers`, `POST /waiting-list` and `POST /gear` were added, and the CORS origin.
9. Commit: `4.0: FastAPI layer over GearShare with exception-to-HTTP mapping and API tests`.

**4.1 Vite app + wireframes**
- `npm create vite@latest web -- --template react`, then `cd web`, `npm install`, `npm install react-router-dom`.
- `web/.env.example` with `VITE_API_URL=http://localhost:8000`, read as `import.meta.env.VITE_API_URL` in `web/src/api.js`. That one module wraps every fetch call and turns a network failure into "Can't reach the rental server.".
- `docs/wireframes.md` (5 screens in ASCII, or photos) and `docs/component_tree.md`, listing for every component its **state owned** and its **props received**.
- A suggested tree (adjust as needed):

```
App (BrowserRouter)
└─ CustomerProvider (context: customers[], current customer)
   └─ BasketProvider (useReducer: items[])
      └─ Layout(children)
         ├─ Navbar (picker, basket count)
         └─ Routes
            ├─ CataloguePage
            │    (search params: q/category/sort; fetch state: status/data/error)
            │  ├─ SearchBar
            │  └─ GearList → GearCard → AvailabilityBadge
            ├─ GearDetailsPage
            ├─ MyRentalsPage
            ├─ BasketPage
            ├─ AddItemPage
            └─ NotFoundPage
```

**4.2 Components with hard-coded JSON:** `Navbar`, `Layout` (with `children`), `GearCard`, `GearList`, `AvailabilityBadge`. Use the 7 starter items as a fixture, and props only.

**4.3 Live data:**
- The search box, category filter and sort dropdown live in `useSearchParams` (this also solves "Back to results" in 4.5).
- Debounce `q` by about 300 ms.
- `useEffect([debouncedQ, category, sort])` uses an `AbortController`, with `controller.abort()` in the cleanup.
- Ignore `AbortError`. Test with Slow 3G.
- Show `Loading catalogue...`, `1 result` / `7 results`, and `No items match 'zzz'. Try a different word.`

**4.4 States and form:**
- Loading / error (with **Retry**) / empty / results on every fetching screen.
- `key={item.sku}`.
- Availability 0 → a "Join waiting list" button (`POST /waiting-list`). Display item → `Display item: view in the shop only`, with no button.
- `AddItemPage` uses controlled inputs. Messages appear under each field: `SKU must be exactly 10 digits.`, units ≥ 1, name required. Submit is disabled until valid. On success: a message, the form clears, and the item appears in the catalogue.

**4.5 Routing:** `/`, `/gear/:sku`, `/me`, `/basket`, `/admin/add` and `*` (404 with a link home). The details page's "Back to results" must keep the query string.

**4.6 Context and reducer:**
- `CustomerContext` with a picker in the navbar, fed by `GET /customers`.
- The basket uses `useReducer` (`ADD` / `REMOVE` / `CLEAR`). Block more than `max_items` with `Basket full: Basic members can rent 2 items.` and disable the add button.
- Checkout calls `POST /rentals` for each item. The button shows `Renting...`, then a toast `Rented Sony 50mm Lens. Due 2026-11-06.`
- Show server errors exactly, in red. Refresh the catalogue afterwards (Sony → `0 of 1 available`).
- `MyRentalsPage` uses `GET /customers/{id}/rentals`. Show `OVERDUE (5 days)` when `days_overdue > 0`, otherwise `On rental`.

**4.7 Styling and accessibility:**
- Tailwind (recommended: it's quick to keep consistent) or MUI.
- One column at 360 px, with no horizontal scroll.
- Every input has a `<label>`, every image an `alt`, and everything works with the keyboard.

**Finish Phase 4:**
- README: a "Phase 4" section (start the API, start the web app, env vars).
- `docs/behaviour_table.md`: every row ticked, plus notes.
- Screenshots in `docs/screenshots/`.
- At least 3 DECISIONS entries: Tailwind vs MUI, where search state lives (the URL), status codes, plus the answers to the Phase 4 think-about questions.
- Save the pytest output to `docs/pytest_phase4.txt`, then merge `phase-4` into `main` with `--no-ff` and tag `phase-4`.
