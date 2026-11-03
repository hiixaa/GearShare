# Phase 3: From a Flat File to a Normalised Database

## 1. Start from a mess (Task 3.1)

`python sql/build_flat.py` joins the four starter CSVs into
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
