# Phase 3: From a Flat File to a Normalised Database

## 1. Starting from a mess (Task 3.1)

`python -m sql.build_flat` joins the four starter CSVs into one file,
[`data/gearshare_flat.csv`](../data/gearshare_flat.csv), with one row per
rental. Everything about the customer, the item and the fine is copied into that
row. It's basically the shop's paper register, typed up:

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

Something is wrong before anything has even happened: Pooja Menon (C005) and
the Vintage Leica (1000000006) aren't in it at all, because neither has ever
been rented.

### Three anomalies, using real rows

**Update anomaly: Rohan Das changes his email.** `rohan@example.com` appears in
three rows (RN002, RN009 and RN010), so changing it means updating all three. If
someone updates two and misses RN010, the file now gives Rohan two different
emails, and there's no way to tell which is right. Prices have the same problem:
the Canon's price of 45000 is copied into three rows (RN002, RN007, RN010), so a
price change has to find every copy, including in rows about old, returned
rentals.

**Insert anomaly: where does Pooja Menon go?** Pooja (C005, Plus,
`pooja@example.com`) is a real customer who has never rented anything. Every row
in the file is a rental, identified by `rental_id`, so there's nowhere to put
her without inventing a fake rental or leaving `rental_id` empty (and then the
row has no identity). New stock has the same problem: the Vintage Leica can never
be rented (R1), so it can never appear in this file, and the catalogue can't
list it.

**Delete anomaly: deleting RN005 deletes the SD card.** RN005 is the only row
that mentions the SD Card 128GB. If that old rental gets deleted (say, during a
clean-up of rentals older than three months), the shop also loses everything it
knew about the item: its SKU (1000000007), its tag, its category, its weight (2 g),
its price (₹600), and the fact that the shop stocks it at all. The record that
Ananya paid a ₹600 fine goes with it. One fact was deleted, and several
unrelated facts disappeared with it.

**The root cause:** the flat file stores facts about four different things
(customers, items, rentals and fines) in one table. Every fact about a customer
or an item is repeated once per rental, and it can only exist while at least one
rental mentions it.

---

## 2. Normalising, step by step (Task 3.2)

### Before starting: what identifies a row?

The flat file's key is `rental_id`, one row per rental. It identifies customers
only by name, which isn't safe as a key: two people can share a name, and names
change. So from here on I bring back the customer's real ID, `customer_id`
(C001 ...). Items already have theirs, `sku`.

### First Normal Form (1NF): one value per cell

**The rule:** every cell holds one single value, never a list.

**What repeats inside a cell?** `tags`. `photo;dslr` is two values squeezed into
one cell. To find "every item tagged photo", you'd have to search inside strings
with `LIKE '%photo%'`, which would also match a tag called "photography".

**Before** (2 of the 10 rows):

| rental_id | customer_id | item_name | tags | sku | ... |
|---|---|---|---|---|---|
| RN002 | C004 | Canon EOS 200D | `photo;dslr` | 1000000001 | ... |
| RN008 | C002 | Rode Wireless Mic | `audio;interview` | 1000000005 | ... |

**After 1NF:** one row per rental and tag, so every cell holds one value:

| rental_id | tag | customer_id | item_name | sku | ... (all other columns) |
|---|---|---|---|---|---|
| RN002 | photo | C004 | Canon EOS 200D | 1000000001 | ... |
| RN002 | dslr | C004 | Canon EOS 200D | 1000000001 | ... |
| RN008 | audio | C002 | Rode Wireless Mic | 1000000005 | ... |
| RN008 | interview | C002 | Rode Wireless Mic | 1000000005 | ... |

The key is now (rental_id, tag), and the 10 rentals have become 18 rows. Every
cell is a single value, but there's even more repetition than before. That's
what 2NF deals with.

### Second Normal Form (2NF): nothing depends on just part of the key

**The rule:** when the key has more than one column, every other column has to
depend on the whole key, not just part of it.

**Which columns depend on only part of the key (rental_id, tag)?** All of them
except the tag. The customer name, email, item name, price, dates and fine are
identical for RN002/photo and RN002/dslr: they depend on `rental_id` alone. So
they move out into their own table:

**rental_tags_2nf** (the composite-key part):

| rental_id | tag |
|---|---|
| RN002 | photo |
| RN002 | dslr |

**rentals_2nf** (key: `rental_id`):

| rental_id | customer_id | customer_name | email | tier | sku | item_name | category | parent_category | weight_g | price | issue_date | due_date | return_date | fine | fine_paid |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| RN002 | C004 | Rohan Das | rohan@example.com | Basic | 1000000001 | Canon EOS 200D | Cameras | Photography | 450 | 45000 | 2026-10-28 | 2026-10-31 | | | |

Looking at `rental_tags_2nf` again, though: a tag isn't really a fact about a
rental, it's a fact about the item. RN002, RN007 and RN010 are all the Canon, so
they'd all repeat "photo" and "dslr". The tags belong to the SKU, so the table
becomes **item_tags (sku, tag)**: 11 rows for 7 items (10 different tags, since
the Canon and the Sony lens share "photo"), however often each item is rented.
That also fixes part of the insert anomaly: the Leica's "display" tag can now be
stored even though it's never been rented.

### Third Normal Form (3NF): nothing depends on another non-key column

**The rule:** every column depends on the key, the whole key, and nothing but
the key. There must be no chains like key → A → B.

In `rentals_2nf`, several columns depend on the key only through another column:

| Chain | Columns that move | New table |
|---|---|---|
| `rental_id → customer_id → name, email, tier` | customer_name, email, tier | **customers** (customer_id, name, email, tier) |
| `customer → tier → max_items, rental_days, late_fee_per_day` | the Rulebook's numbers (not in the flat file, but they are facts about a tier) | **membership_tiers** (tier, max_items, rental_days, late_fee_per_day) |
| `rental_id → sku → name, category, weight, price, item_type, units` | item_name, category, weight_g, price | **items** (sku, name, category, item_type, weight_g, price, total_units) |
| `sku → category → parent_category` | parent_category | **categories** (category_id, name, parent_id → categories), which points to itself |
| `rental_id → fine → fine_paid` | fine, fine_paid | **fines** (rental_id, amount, paid) |

**Tiers and their limits.** If every Basic customer stored `max_items = 2`,
changing the Basic limit to 3 would mean updating every Basic customer, which is
the update anomaly all over again. In `membership_tiers` it's one row.

**Categories and their parents.** "Cameras belongs under Photography" is one
fact, but in `rentals_2nf` it's repeated in every Cameras and Lenses rental. As a
row in `categories` with a `parent_id`, it's stored once. And because `parent_id`
points back into the same table, a tree of any depth (Gear Hub → Photography →
Cameras → Mirrorless ...) fits without changing the schema.

**Why fines get their own table instead of two columns on rentals.** Most
rentals (6 of the 10) have no fine, so those columns would mostly be empty. And
"paid" depends on the fine, not the rental: paying is something that happens to
the fine. A separate table also leaves room for things like part-payments later,
without touching `rentals`.

**What's left in rentals** depends only on the rental itself: **rentals**
(rental_id, customer_id, sku, issue_date, due_date, return_date, extensions).

### The final tables

All three anomalies are gone. Rohan's email is in one row. Pooja is a customer
with no rentals. The Leica is an item with no rentals. Deleting RN005 deletes a
rental and nothing else.

| Table | Key | Holds | Where it came from |
|---|---|---|---|
| `membership_tiers` | tier | max_items, rental_days, late_fee_per_day | 3NF: tier → limits |
| `customers` | customer_id | name, email (unique), tier | 3NF |
| `categories` | category_id | name (unique), parent_id (points to its own table) | 3NF: category → parent |
| `items` | sku | name, category_id, item_type, weight_g, price, total_units | 3NF |
| `tags` | tag_id | name (unique) | 1NF/2NF: splitting the tag list |
| `item_tags` | (sku, tag_id) | which item has which tag (many-to-many) | 1NF/2NF |
| `rentals` | rental_id | customer_id, sku, issue_date, due_date, return_date, extensions | what's left |
| `fines` | rental_id | amount, paid | 3NF |
| `waiting_list` | entry_id | sku, customer_id, joined_at, status (waiting / reserved) | the engine's R7 queue and reservations (D7) |
| `audit_log` | log_id | logged_at, action, customer_id, sku, rental_id | the engine's audit log |

I gave tags their own table, instead of storing the tag text directly in
`item_tags`, so each tag name is spelled exactly once. "interview" can't also
show up as "Interview " on another item, and renaming a tag is a one-row change.

After loading the starter data (Task 3.4), the counts are: 7 items, 10 tags,
5 customers, 10 rentals, 4 fines, 8 categories (the 7 used by items, plus
Photography as the parent of Cameras and Lenses), and 3 tiers.
