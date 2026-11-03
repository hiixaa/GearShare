# Phase 3: Index Report (Task 3.6)

Reproduce (about 1 minute; builds a separate `data/gearshare_big.db`):

```powershell
python -m sql.index_report --explain Q12 Q5
```

**Data:** the starter data + 1,000 customers + 1,000 items + **100,000 rentals**
(100,010 in total, 1,019 still open), with `ANALYZE` run so the planner has real
statistics. **Times:** median of 5 runs, in ms, on a Windows laptop. Between
separate runs, the same query varied by up to about 2× (see "noise" below), so
only large differences are treated as real.

---

## 1. The two slowest queries, before any index

| query | before ms |
|---|---|
| **Q12** pair of items most often rented by the same customer | **5,527.59** |
| **Q5** items never rented | **181.29** |
| Q9 customers with ≥ 3 categories | 136.93 |
| Q10 categories with average rental > 4 days | 110.02 |
| Q4 top 3 items | 101.98 |
| (all others) | < 70 |

SQLite indexes `PRIMARY KEY` and `UNIQUE` columns automatically, but **not
foreign keys**: `rentals.sku` and `rentals.customer_id` had no index at all.

## 2. Q5: EXPLAIN before and after

**Before:**
```
SCAN i
SEARCH r USING AUTOMATIC COVERING INDEX (sku=?) LEFT-JOIN
USE TEMP B-TREE FOR ORDER BY
```
`AUTOMATIC ... INDEX` means SQLite saw no usable index, so **on every run** it
built a temporary one on `rentals(sku)` (100,000 entries), used it once, and
threw it away. Building it was most of the 181 ms.

**After** `idx_rentals_sku_covering`:
```
SCAN i
SEARCH r USING COVERING INDEX idx_rentals_sku_covering (sku=?) LEFT-JOIN
USE TEMP B-TREE FOR ORDER BY
```
A permanent index, and **COVERING**: it holds `sku` and `rental_id`, the only
two rental columns Q5 reads, so SQLite never opens the table itself.

**Result: 181.29 → 10.62 ms (17×).**

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

The inner step (building `customer_items`) now uses the covering index, but
**Result: 5,527.59 → 4,910.06 ms (1.1×), no real gain.** Why:
- `customer_items` is a temporary result (a CTE), and **indexes on base tables
  can't help a join between two temporary results**. The `b` lookup is still an
  `AUTOMATIC` index, built at run time.
- The real cost is the **answer itself**. Each customer rented about 100 distinct
  items, which is about 100 × 99 / 2 ≈ 5,000 pairs per customer, and ≈ 5 million pairs
  in total, all grouped and counted. An index makes *finding* rows fast. It
  can't reduce the number of rows the query has to produce.
- **What would fix it:** precompute the pair counts (a summary table updated when a
  rental is added, or rebuilt nightly). The question "which items go together"
  changes slowly, so it doesn't need to be recalculated live.

## 4. How the final index was found: three measured rounds

| Round | Indexes tried | What happened |
|---|---|---|
| 1 | `rentals(sku)`, `rentals(customer_id, sku)`, partial `rentals(sku) WHERE return_date IS NULL` | Q2, Q3, Q4, Q11 faster, but **Q5 0.6×, Q6 0.2×, Q10 0.4×: slower** |
| 2 | `rentals(sku, rental_id)`, `rentals(sku, return_date, issue_date)`, `rentals(customer_id, issue_date)` | Q5 24.7×, Q10 3.9×, but **Q9 0.3×: 3× slower** |
| 3 (final) | **one** `rentals(sku, return_date, issue_date, customer_id, rental_id)` | Q5 17×, Q10 3.9×, Q2 3.3×, Q11 2.3×, Q4 2.1×; **nothing measurably slower** |

**The lesson (rounds 1 and 2):** an index that is **not covering** can be slower than
no index. Q9 after round 2:
```
SCAN i
SEARCH r USING INDEX idx_rentals_sku_dates (sku=?)      <- not COVERING
SEARCH c USING INDEX sqlite_autoindex_customers_1 (customer_id=?)
```
The planner switched from reading the rentals table **once, in order** (`SCAN r`)
to "for each item, look up its rentals in the index". But the index had no
`customer_id`, so for every one of ~100,000 rentals it jumped back into the
table: 100,000 random reads instead of one sequential pass. Adding the missing
columns to the index made it covering, and Q9 went back to normal.

**Why the column order is `(sku, return_date, issue_date, customer_id, rental_id)`:**
`sku` first, because every query using it looks up "rentals of this item".
`return_date` second, so "**open** rentals of this item"
(`sku = ? AND return_date IS NULL`, used by Q11 and by every `rent()`
availability check) is one contiguous range of the index. The remaining columns
just make it covering. This one index replaced the partial index from round 1.

## 5. Final: all 12 queries before and after

| query | before ms | after ms | speed-up |
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

**Noise:** Q8 reads only the `fines` table, which a rentals index cannot
affect, yet it "changed" from 10 to 22 ms. Q7 likewise. That is the noise floor
of this laptop (other programs, OneDrive syncing, CPU speed changes), so changes
under about 2× on queries this fast are not evidence of anything.

## 6. The index I decided NOT to create

**`fines (paid)`**, which might look natural for Q8 ("fines paid vs pending").
- The column has **2 distinct values** (0 and 1). An index is useful when it
  narrows the search to a few rows. Here each value matches about half the table,
  and reading half a table through an index (one jump per row) is slower than
  reading it all in order.
- Q8 needs **every** fine anyway (it sums both groups), so there is nothing to skip.
- Every index costs on **every write**: each new fine would update the index too.

Also deliberately not kept: `rentals(customer_id, issue_date)` for Q6. It made Q9
3× slower (round 2) and gave Q6 no stable gain (about 54 ms either way).

## 7. Think-about question 3: which queries worry me at 10 million rentals?

- **Q12** first. Its cost grows with (items per customer)², not with rentals.
  Precompute the pair counts (section 3).
- **Q7, Q9 and Q10** aggregate over **all** history. They grow linearly, so 100× the
  data means about 100× the time. Fix: restrict to a period (e.g. this year), or
  keep monthly summary tables.
- **Q2, Q3 and Q11** stay fast, because they only touch **open** rentals: about 1% of
  the table, and a contiguous range of the covering index.
