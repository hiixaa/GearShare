-- GearShare Mini: indexes (Task 3.6). Measurements: docs/index_report.md.
--
-- Run:  python -m sql.run_sql sql/indexes.sql
--
-- SQLite indexes PRIMARY KEY and UNIQUE columns automatically, but NOT foreign
-- keys, so every join from rentals to items / customers had no index.
--
-- What the measurements taught (3 rounds, docs/index_report.md):
--   * A plain index on rentals(sku) made Q5, Q6, Q9 and Q10 SLOWER. The index
--     only holds sku, so for each of ~100,000 matching rows SQLite jumped back
--     into the table for the other columns: slower than reading the table once.
--   * An index helps only if it is COVERING: it holds every column the query
--     reads, so the table itself is never touched.

-- ONE covering index for every query that starts from "rentals of this item":
--   Q5  never rented          reads sku, rental_id
--   Q4  top 3 items           reads sku
--   Q9  categories/customer   reads sku, customer_id
--   Q10 average length        reads sku, return_date, issue_date
--   Q11 + rent() availability (sku = ? AND return_date IS NULL): uses the
--       (sku, return_date) prefix, so open rentals of an item are adjacent.
-- Column order: sku first (every lookup is by sku), return_date second
-- (so "open rentals of this item" is a prefix range), then the columns read.
CREATE INDEX IF NOT EXISTS idx_rentals_sku_covering
    ON rentals (sku, return_date, issue_date, customer_id, rental_id);

-- Tried and REMOVED (measured, see the report):
--   rentals (sku)                     non-covering: slower for Q5/Q9/Q10
--   rentals (customer_id, issue_date) for Q6: made Q9 3x slower, no stable Q6 gain
--   rentals (sku) WHERE return_date IS NULL   (partial): covered by the prefix above
--
-- Not created on purpose: fines (paid). Only 2 distinct values (0/1), and Q8
-- reads every fine anyway, so an index adds write cost and saves nothing.
-- Q12 (the slowest) gets no index of its own: its cost is building and
-- grouping millions of item pairs, which the answer requires.
