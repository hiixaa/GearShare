# Phase 3: From a Flat File to a Normalised Database

## 1. Start from a mess (Task 3.1)

`python -m sql.build_flat` joins the four starter CSVs into
[`data/gearshare_flat.csv`](../data/gearshare_flat.csv): **one row per rental**,
with everything about the customer, the item and the fine copied into that row.
It is the shop's paper register, typed up:

```
rental_id,customer_name,email,tier,item_name,tags,sku,category,parent_category,weight_g,price,issue_date,due_date,return_date,fine,fine_paid
RN001,Vikram Shah,vikram@example.com,Plus,DJI Mini Drone,video;aerial,1000000003,Drones,,249,38000,2026-10-24,2026-10-29,,,
RN002,Rohan Das,rohan@example.com,Basic,Canon EOS 200D,photo;dslr,1000000001,Cameras,Photography,450,45000,2026-10-28,2026-10-31,,,
RN003,Meera Joshi,meera@example.com,Pro,Manfrotto Tripod,support,1000000004,Tripods,,1200,6000,2026-10-30,2026-11-06,,,
RN004,Ananya Nair,ananya@example.com,Basic,Sony 50mm Lens,photo;lens,1000000002,Lenses,Photography,280,18000,2026-09-10,2026-09-13,2026-09-13,,
RN005,Ananya Nair,ananya@example.com,Basic,SD Card 128GB,storage,1000000007,Accessories,,2,600,2026-08-01,2026-08-03,2026-08-23,600,yes
RN006,Meera Joshi,meera@example.com,Pro,DJI Mini Drone,video;aerial,1000000003,Drones,,249,38000,2026-08-05,2026-08-12,2026-08-10,,
RN007,Vikram Shah,vikram@example.com,Plus,Canon EOS 200D,photo;dslr,1000000001,Cameras,Photography,450,45000,2026-07-10,2026-07-15,2026-07-15,,
RN008,Vikram Shah,vikram@example.com,Plus,Rode Wireless Mic,audio;interview,1000000005,Audio,,120,22000,2026-06-01,2026-06-06,2026-06-09,300,yes
RN009,Rohan Das,rohan@example.com,Basic,Rode Wireless Mic,audio;interview,1000000005,Audio,,120,22000,2026-07-01,2026-07-04,2026-07-13,450,no
RN010,Rohan Das,rohan@example.com,Basic,Canon EOS 200D,photo;dslr,1000000001,Cameras,Photography,450,45000,2026-07-20,2026-07-23,2026-07-26,150,no
```

Notice what is **missing** before anything goes wrong: Pooja Menon (C005)
and the Vintage Leica (1000000006) appear nowhere, because neither has
ever been rented.

### Three anomalies, with real rows

**Update anomaly: Rohan Das changes his email.**
`rohan@example.com` is stored in **3 rows** (RN002, RN009, RN010). Changing it
means updating all three. If the staff member updates RN002 and RN009 but
misses RN010, the file now gives Rohan two different emails, and there is no
way to tell which one is correct. The same happens with prices: the Canon EOS
200D's price `45000` is copied into 3 rows (RN002, RN007, RN010), so a price
change has to find every copy, including in rows about old, returned rentals.

**Insert anomaly: where does Pooja Menon go?**
Pooja (C005, Plus, `pooja@example.com`) is a real customer who has never
rented. Every row in the flat file **is** a rental, and `rental_id` identifies
the row, so there is nowhere to record her without inventing a fake rental,
or leaving `rental_id` empty (and then the row has no identity at all). The
same is true for new stock: the Vintage Leica (Showcase) can never be rented
(R1), so it can **never** appear in this file, and the catalogue can't list it.

**Delete anomaly: deleting RN005 deletes the SD card.**
RN005 is the **only** row mentioning `SD Card 128GB`. If that old rental is
deleted (for example, a clean-up of rentals older than 3 months), the shop
also loses everything it knew about the item: its SKU 1000000007, tags
(`storage`), category (Accessories), weight (2 g), price (₹600) and the fact
that it stocks it at all, plus the record that Ananya paid a ₹600 fine. One
fact (a rental happened) was deleted, and several unrelated facts (an item
exists, it costs ₹600) went with it.

**Root cause, in one sentence:** the flat file stores facts about **four
different things** (customers, items, rentals, fines) in one table, so each fact
about a customer or item is repeated once per rental, and can only exist while
at least one rental mentions it.

---

## 2. Normalise step by step (Task 3.2)

### 2.0 Before we start: what identifies a row?

The flat file's key is `rental_id`: one row per rental. It identifies the customer
only by **name**, which is not safe as a key (two customers can share a name,
and a name can change). So the customer's real identifier `customer_id`
(C001 ...) comes back as a column from here on. The item already has its
identifier, `sku`.

### 2.1 First Normal Form (1NF): one value per cell

**Rule:** every cell holds a single, atomic value. No lists inside a cell.

**What repeats inside a cell?** `tags`: `photo;dslr` is a list of two values in
one cell. To find "all items tagged photo", you would have to split strings
with `LIKE '%photo%'`, which also matches a tag called `photography`.

**Before** (2 of the 10 rows):

| rental_id | customer_id | item_name | tags | sku | ... |
|---|---|---|---|---|---|
| RN002 | C004 | Canon EOS 200D | `photo;dslr` | 1000000001 | ... |
| RN008 | C002 | Rode Wireless Mic | `audio;interview` | 1000000005 | ... |

**After 1NF:** one row per (rental, tag), so every cell is atomic:

| rental_id | tag | customer_id | item_name | sku | ... (all other columns) |
|---|---|---|---|---|---|
| RN002 | photo | C004 | Canon EOS 200D | 1000000001 | ... |
| RN002 | dslr | C004 | Canon EOS 200D | 1000000001 | ... |
| RN008 | audio | C002 | Rode Wireless Mic | 1000000005 | ... |
| RN008 | interview | C002 | Rode Wireless Mic | 1000000005 | ... |

The key is now **(rental_id, tag)**. The 10 rentals became 18 rows: the cells are
atomic, but there is even **more** repetition. That is what 2NF fixes.

### 2.2 Second Normal Form (2NF): no column depends on only part of the key

**Rule:** with a composite key, every non-key column must depend on the
**whole** key, not just part of it.

**Which columns depend on only part of the key (rental_id, tag)?** All of them
except `tag` itself. `customer_name`, `email`, `item_name`, `price`, `issue_date`,
`fine` ... are the same for RN002/photo and RN002/dslr: they depend on
`rental_id` alone. Split them out:

**rental_tags_2nf** (the composite-key part):

| rental_id | tag |
|---|---|
| RN002 | photo |
| RN002 | dslr |

**rentals_2nf** (key: `rental_id`):

| rental_id | customer_id | customer_name | email | tier | sku | item_name | category | parent_category | weight_g | price | issue_date | due_date | return_date | fine | fine_paid |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| RN002 | C004 | Rohan Das | rohan@example.com | Basic | 1000000001 | Canon EOS 200D | Cameras | Photography | 450 | 45000 | 2026-10-28 | 2026-10-31 | | | |

**One more look at `rental_tags_2nf`:** a tag isn't a fact about a *rental*,
it's a fact about the *item*. RN002, RN007 and RN010 are all the Canon, so
they would all repeat `photo`, `dslr`. The tags really belong to the SKU
(`rental_id → sku`, and each SKU has its own set of tags). So the table
becomes **item_tags (sku, tag)**: 11 rows for 7 items (10 distinct tags,
because `photo` is shared by the Canon and the Sony lens), regardless of how
often each item is rented. This also cures part of the insert anomaly: the Leica's
`display` tag can now be stored even though it was never rented.

### 2.3 Third Normal Form (3NF): no column depends on another non-key column

**Rule:** every non-key column depends on the key, the whole key, and
**nothing but the key**. There must be no chain `key → A → B`.

In `rentals_2nf`, several columns depend on the key only **through** another column:

| Chain (transitive dependency) | Columns that move | New table |
|---|---|---|
| `rental_id → customer_id → name, email, tier` | customer_name, email, tier | **customers** (customer_id, name, email, tier) |
| `customer → tier → max_items, rental_days, late_fee_per_day` | the Rulebook's numbers (not in the flat file, but they *are* facts about a tier) | **membership_tiers** (tier, max_items, rental_days, late_fee_per_day) |
| `rental_id → sku → name, category, weight, price, item_type, units` | item_name, category, weight_g, price | **items** (sku, name, category, item_type, weight_g, price, total_units) |
| `sku → category → parent_category` | parent_category | **categories** (category_id, name, parent_id → categories): self-reference |
| `rental_id → fine → fine_paid` | fine, fine_paid | **fines** (rental_id, amount, paid) |

**Think about tier and its limits:** if `max_items = 2` were stored on every
Basic customer, changing the Basic limit to 3 would mean updating every Basic
customer: the update anomaly again. In `membership_tiers` it is one row.

**Think about category and its parent:** "Cameras is under Photography" is
one fact. In `rentals_2nf` it is repeated in every Cameras and Lenses rental.
As a `categories` row with `parent_id`, it is stored once. And because
`parent_id` points back into the **same** table, a tree of any depth
(Gear Hub → Photography → Cameras → Mirrorless ...) fits without changing the schema.

**Why fines get their own table, not two columns on rentals:** most rentals
(6 of 10) have no fine, so `fine`/`fine_paid` would mostly be empty. And
`fine_paid` depends on the *fine*, not on the rental: paying is something that
happens to the fine. A separate table also leaves room for a later change, such as
part-payments or several fines per rental, without touching `rentals`.

**What remains in rentals** depends only on the rental itself:
**rentals** (rental_id, customer_id, sku, issue_date, due_date, return_date, extensions).

### 2.4 The final tables

The 3 anomalies are gone: Rohan's email is in **one** row, Pooja is a
customers row with no rentals, the Leica is an items row with no rentals, and
deleting RN005 deletes a rental and nothing else.

| Table | Key | Holds | From |
|---|---|---|---|
| `membership_tiers` | tier | max_items, rental_days, late_fee_per_day (the Rulebook) | 3NF: tier → limits |
| `customers` | customer_id | name, email (UNIQUE), tier → membership_tiers | 3NF |
| `categories` | category_id | name (UNIQUE), parent_id → categories | 3NF: category → parent |
| `items` | sku | name, category_id, item_type, weight_g, price, total_units | 3NF |
| `tags` | tag_id | name (UNIQUE) | 1NF/2NF: split the tag list |
| `item_tags` | (sku, tag_id) | junction table: which item has which tag (many-to-many) | 1NF/2NF |
| `rentals` | rental_id | customer_id, sku, issue_date, due_date, return_date, extensions | what's left |
| `fines` | rental_id | amount, paid | 3NF |
| `waiting_list` | entry_id | sku, customer_id, joined_at, status (`waiting` / `reserved`) | the engine's R7 queue + reservations (D7) |
| `audit_log` | log_id | logged_at, action, customer_id, sku, rental_id | the engine's `@audit` |

`tags` + `item_tags` vs storing `tag` text directly in `item_tags`: a separate
`tags` table means a tag name is spelled once ("interview" can't also appear
as "Interview " on another item), and renaming a tag is one row.

Expected counts after loading the starter data (Task 3.4):
7 items, **10 tags**, 5 customers, 10 rentals, 4 fines, **8 categories**
(the 7 used by items, plus Photography as the parent of Cameras and Lenses), 3 tiers.
