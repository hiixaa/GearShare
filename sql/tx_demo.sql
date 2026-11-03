-- GearShare Mini: "rent" as ONE transaction, and a rollback that leaves no trace.
--
-- Run on the seeded database:   python -m sql.setup_db
--                               python -m sql.run_sql sql/tx_demo.sql
--
-- Rent = 1) check the item is available, 2) insert the rental, 3) insert an
-- audit_log row. All three succeed together or none of them happens.

PRAGMA foreign_keys = ON;

-- Reset, so the demo gives the same output every time it is run.
DELETE FROM audit_log;
DELETE FROM rentals WHERE rental_id = 'RN011';


-- before: RN011 rows (expect 0)
SELECT COUNT(*) AS rn011_rows FROM rentals WHERE rental_id = 'RN011';

-- before: audit_log rows (expect 0)
SELECT COUNT(*) AS audit_rows FROM audit_log;

-- before: Sony 50mm Lens units available (expect 1)
SELECT i.total_units - COUNT(r.rental_id) AS sony_available
FROM items AS i
LEFT JOIN rentals AS r ON r.sku = i.sku AND r.return_date IS NULL
WHERE i.sku = '1000000002'
GROUP BY i.sku;


-- ============ attempt 1: the audit insert violates NOT NULL on purpose ============
-- IMMEDIATE takes the write lock now, before reading availability, so a second
-- rent request has to wait instead of reading the same "1 free" (DECISIONS D19).
BEGIN IMMEDIATE;

-- Steps 1 + 2 together: insert the rental ONLY IF a unit is free.
-- (If none were free, this inserts 0 rows instead of breaking the stock count.)
INSERT INTO rentals (rental_id, customer_id, sku, issue_date, due_date)
SELECT 'RN011', 'C001', i.sku, '2026-11-03', '2026-11-06'
FROM items AS i
WHERE i.sku = '1000000002'
  AND i.total_units > (SELECT COUNT(*) FROM rentals AS r
                       WHERE r.sku = i.sku AND r.return_date IS NULL);

-- during attempt 1: RN011 exists INSIDE the open transaction (expect 1)
SELECT COUNT(*) AS rn011_rows FROM rentals WHERE rental_id = 'RN011';

-- Step 3 fails: customer_id is NOT NULL, so this statement prints an ERROR.
INSERT INTO audit_log (logged_at, action, customer_id, sku, rental_id)
VALUES ('2026-11-03T10:00:00', 'rent', NULL, '1000000002', 'RN011');

-- One step failed, so undo every step of this rent.
ROLLBACK;

-- after ROLLBACK: RN011 rows (still 0: no trace)
SELECT COUNT(*) AS rn011_rows FROM rentals WHERE rental_id = 'RN011';

-- after ROLLBACK: audit_log rows (still 0)
SELECT COUNT(*) AS audit_rows FROM audit_log;


-- ============ attempt 2: correct statements ============
BEGIN IMMEDIATE;

INSERT INTO rentals (rental_id, customer_id, sku, issue_date, due_date)
SELECT 'RN011', 'C001', i.sku, '2026-11-03', '2026-11-06'
FROM items AS i
WHERE i.sku = '1000000002'
  AND i.total_units > (SELECT COUNT(*) FROM rentals AS r
                       WHERE r.sku = i.sku AND r.return_date IS NULL);

INSERT INTO audit_log (logged_at, action, customer_id, sku, rental_id)
VALUES ('2026-11-03T10:00:00', 'rent', 'C001', '1000000002', 'RN011');

COMMIT;

-- after COMMIT: RN011 rows (expect 1)
SELECT COUNT(*) AS rn011_rows FROM rentals WHERE rental_id = 'RN011';

-- after COMMIT: audit_log rows (expect 1)
SELECT COUNT(*) AS audit_rows FROM audit_log;

-- after COMMIT: Sony 50mm Lens units available (expect 0)
SELECT i.total_units - COUNT(r.rental_id) AS sony_available
FROM items AS i
LEFT JOIN rentals AS r ON r.sku = i.sku AND r.return_date IS NULL
WHERE i.sku = '1000000002'
GROUP BY i.sku;


-- ============ bonus: the availability check refuses a second unit ============
BEGIN IMMEDIATE;

INSERT INTO rentals (rental_id, customer_id, sku, issue_date, due_date)
SELECT 'RN012', 'C003', i.sku, '2026-11-03', '2026-11-10'
FROM items AS i
WHERE i.sku = '1000000002'
  AND i.total_units > (SELECT COUNT(*) FROM rentals AS r
                       WHERE r.sku = i.sku AND r.return_date IS NULL);

-- no unit was free, so 0 rows were inserted: RN012 rows (expect 0)
SELECT COUNT(*) AS rn012_rows FROM rentals WHERE rental_id = 'RN012';

ROLLBACK;
