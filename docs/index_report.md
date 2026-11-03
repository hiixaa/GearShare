# Phase 3: Index Report (Task 3.6)

To reproduce (it takes about a minute and builds a separate `data/gearshare_big.db`):

```powershell
python -m sql.index_report --explain Q12 Q5
```

**The data:** the starter data plus 1,000 customers, 1,000 items and 100,000
rentals (100,010 in total, 1,019 still open). I ran `ANALYZE` first, so SQLite's
query planner has real statistics. **The times** are medians of 5 runs, in
milliseconds, on my Windows laptop. The same query could vary by up to about 2×
between separate runs (see the note on noise below), so I only treat big
differences as real.

---

## 1. The slowest queries, before adding any index

| query | before (ms) |
|---|---|
| **Q12**, the pair of items most often rented by the same customer | **5,527.59** |
| **Q5**, items never rented | **181.29** |
| Q9, customers who rented from 3+ categories | 136.93 |
| Q10, categories where the average rental is over 4 days | 110.02 |
| Q4, the top 3 items | 101.98 |
| everything else | under 70 |

SQLite automatically indexes primary keys and UNIQUE columns, but **not foreign
keys**. So `rentals.sku` and `rentals.customer_id` had no index at all.

## 2. Q5: EXPLAIN before and after

**Before:**
```
SCAN i
SEARCH r USING AUTOMATIC COVERING INDEX (sku=?) LEFT-JOIN
USE TEMP B-TREE FOR ORDER BY
```
`AUTOMATIC ... INDEX` means SQLite found no index it could use. So on every run
it built a temporary index on `rentals(sku)` (100,000 entries), used it once,
and threw it away. Building that index was most of the 181 ms.

**After** adding `idx_rentals_sku_covering`:
```
SCAN i
SEARCH r USING COVERING INDEX idx_rentals_sku_covering (sku=?) LEFT-JOIN
USE TEMP B-TREE FOR ORDER BY
```
Now there's a permanent index, and it's **covering**: it already contains `sku`
and `rental_id`, the only two rental columns Q5 needs, so SQLite never has to
read the table itself.

**Result: 181.29 → 10.62 ms, about 17× faster.**

## 3. Q12: EXPLAIN before and after

**Before:**
```
MATERIALIZE customer_items
  SCAN r
  SEARCH i USING INDEX sqlite_autoindex_items_1 (sku=?)
  USE TEMP B-TREE FOR DISTINCT
SCAN a
SEARCH b USING AUTOMATIC COVERING INDEX (customer_id=?)
USE TEMP B-TREE FOR GROUP BY
USE TEMP B-TREE FOR ORDER BY
```

**After:**
```
MATERIALIZE customer_items
  SCAN i USING INDEX sqlite_autoindex_items_1
  SEARCH r USING COVERING INDEX idx_rentals_sku_covering (sku=?)
  USE TEMP B-TREE FOR DISTINCT
SCAN a
SEARCH b USING AUTOMATIC COVERING INDEX (customer_id=?)
USE TEMP B-TREE FOR GROUP BY
USE TEMP B-TREE FOR ORDER BY
```

The inner step (building `customer_items`) now uses the new index, but
**the result was 5,527.59 → 4,910.06 ms, about 1.1×, so no real gain.** Here's why:
- `customer_items` is a temporary result (a CTE), and an index on a real table
  can't speed up a join between two temporary results. The lookup on `b` still
  builds an automatic index at run time.
- The real cost is the answer itself. Each customer rented about 100 different
  items, which is roughly 100 × 99 / 2 ≈ 5,000 pairs per customer, or about 5
  million pairs overall, all grouped and counted. An index makes finding rows
  fast, but it can't reduce the number of rows the query has to produce.
- **What would actually fix it:** precompute the pair counts, in a summary table
  updated when a rental is added or rebuilt overnight. "Which items go together"
  changes slowly, so there's no need to work it out live.

## 4. How I found the right index: three rounds of measuring

| Round | What I tried | What happened |
|---|---|---|
| 1 | `rentals(sku)`, `rentals(customer_id, sku)`, and a partial index on `rentals(sku) WHERE return_date IS NULL` | Q2, Q3, Q4 and Q11 got faster, but **Q5 (0.6×), Q6 (0.2×) and Q10 (0.4×) got slower** |
| 2 | `rentals(sku, rental_id)`, `rentals(sku, return_date, issue_date)`, `rentals(customer_id, issue_date)` | Q5 24.7× faster and Q10 3.9× faster, but **Q9 got 3× slower** |
| 3 (final) | **one** index: `rentals(sku, return_date, issue_date, customer_id, rental_id)` | Q5 17×, Q10 3.9×, Q2 3.3×, Q11 2.3× and Q4 2.1× faster, and **nothing measurably slower** |

**What rounds 1 and 2 taught me:** an index that isn't covering can be slower than
no index at all. Here's Q9's plan after round 2:
```
SCAN i
SEARCH r USING INDEX idx_rentals_sku_dates (sku=?)      <- not COVERING
SEARCH c USING INDEX sqlite_autoindex_customers_1 (customer_id=?)
```
Before, the planner read the rentals table once, from start to finish
(`SCAN r`). With the new index, it switched to "for each item, look up its
rentals in the index". But that index didn't contain `customer_id`, so for every
one of the ~100,000 rentals it had to jump back into the table to get it. That's
100,000 jumps to random places instead of one straight read. Once I added the
missing columns to the index, Q9 went back to normal.

**Why the columns are in that order** (`sku, return_date, issue_date, customer_id, rental_id`):
`sku` comes first because every query that uses this index looks up "the rentals
of this item". `return_date` is second, so that "the open rentals of this item"
(`sku = ? AND return_date IS NULL`, which Q11 and every availability check in
`rent()` use) are all next to each other in the index. The other columns are
there to make it covering. This single index also replaced the partial index
from round 1.

## 5. All 12 queries, before and after

| query | before (ms) | after (ms) | speed-up |
|---|---|---|---|
| Q1 | 0.05 | 0.06 | 0.9x |
| Q2 | 15.52 | 4.65 | 3.3x |
| Q3 | 13.36 | 9.29 | 1.4x |
| Q4 | 101.98 | 49.10 | 2.1x |
| **Q5** | **181.29** | **10.62** | **17.1x** |
| Q6 | 57.78 | 54.19 | 1.1x |
| Q7 | 69.43 | 106.59 | 0.7x |
| Q8 | 10.27 | 22.06 | 0.5x |
| Q9 | 136.93 | 127.31 | 1.1x |
| Q10 | 110.02 | 28.25 | 3.9x |
| Q11 | 9.65 | 4.18 | 2.3x |
| **Q12** | **5,527.59** | **4,910.06** | **1.1x** |

**A note on noise.** Q8 only reads the `fines` table, which a rentals index
can't possibly affect, yet it "changed" from 10 to 22 ms. Q7 did something
similar. That's just how noisy timing is on this laptop (other programs,
OneDrive syncing, the CPU changing speed), so a change of less than about 2× on
queries this fast doesn't mean anything.

## 6. The index I chose not to create

**`fines(paid)`**, which might seem obvious for Q8 ("fines paid vs pending"):
- The column only has two values, 0 and 1. An index helps when it narrows the
  search down to a few rows, but here each value matches about half the table,
  and reading half a table through an index (one jump per row) is slower than
  just reading all of it in order.
- Q8 needs every fine anyway, since it adds up both groups, so there's nothing
  to skip.
- Every index costs something on every write: each new fine would have to update
  it too.

I also dropped `rentals(customer_id, issue_date)`, which I tried for Q6. It made
Q9 3× slower (round 2) and didn't give Q6 a consistent gain (about 54 ms either way).

## 7. Which queries would worry me at 10 million rentals?

- **Q12** first. Its cost grows with the square of how many items each customer
  rents, not just with the number of rentals. Precomputing the pair counts is
  the fix (section 3).
- **Q7, Q9 and Q10** add up the whole rental history, so they grow in a straight
  line: 100× the data means about 100× the time. I'd limit them to a period (say,
  this year) or keep monthly summary tables.
- **Q2, Q3 and Q11** would stay fast, because they only touch open rentals
  (about 1% of the table), which sit together in the covering index.
