-- GearShare Mini: starter data (the four starter CSVs), as SQL.
--
-- Run after schema.sql:   python -m sql.run_sql sql/seed.sql
-- Or both at once:         python -m sql.setup_db
--
-- One transaction: either every row loads, or none does.
-- Foreign-key IDs are looked up by NAME (WITH ... JOIN), so there are no
-- magic numbers like category_id = 4 to keep in sync by hand.

PRAGMA foreign_keys = ON;

BEGIN;

-- Re-runnable: empty the tables first, children before parents.
DELETE FROM audit_log;
DELETE FROM waiting_list;
DELETE FROM fines;
DELETE FROM rentals;
DELETE FROM item_tags;
DELETE FROM tags;
DELETE FROM items;
DELETE FROM categories WHERE parent_id IS NOT NULL;  -- children first: ON DELETE RESTRICT
DELETE FROM categories;                              -- protects a parent with children
DELETE FROM customers;
DELETE FROM membership_tiers;

-- The Rulebook's tier table
INSERT INTO membership_tiers (tier, max_items, rental_days, late_fee_per_day) VALUES
    ('Basic', 2, 3,  50),
    ('Plus',  4, 5, 100),
    ('Pro',   8, 7, 150);

-- customers.csv
INSERT INTO customers (customer_id, name, email, tier) VALUES
    ('C001', 'Ananya Nair', 'ananya@example.com', 'Basic'),
    ('C002', 'Vikram Shah', 'vikram@example.com', 'Plus'),
    ('C003', 'Meera Joshi', 'meera@example.com',  'Pro'),
    ('C004', 'Rohan Das',   'rohan@example.com',  'Basic'),
    ('C005', 'Pooja Menon', 'pooja@example.com',  'Plus');

-- 8 categories: the 7 used by items, plus Photography as the parent of two.
-- Parents first, so the children's parent_id lookup finds them.
INSERT INTO categories (name, parent_id) VALUES ('Photography', NULL);

WITH v(name, parent) AS (VALUES
    ('Cameras',     'Photography'),
    ('Lenses',      'Photography'),
    ('Drones',      NULL),
    ('Tripods',     NULL),
    ('Audio',       NULL),
    ('Showcase',    NULL),
    ('Accessories', NULL))
INSERT INTO categories (name, parent_id)
SELECT v.name, p.category_id
FROM v LEFT JOIN categories AS p ON p.name = v.parent;

-- gear.csv (tags go in their own tables below)
WITH v(sku, name, category, item_type, weight_g, price, total_units) AS (VALUES
    ('1000000001', 'Canon EOS 200D',           'Cameras',     'Equipment',  450,  45000, 2),
    ('1000000002', 'Sony 50mm Lens',           'Lenses',      'Equipment',  280,  18000, 1),
    ('1000000003', 'DJI Mini Drone',           'Drones',      'Equipment',  249,  38000, 1),
    ('1000000004', 'Manfrotto Tripod',         'Tripods',     'Equipment', 1200,   6000, 2),
    ('1000000005', 'Rode Wireless Mic',        'Audio',       'Equipment',  120,  22000, 1),
    ('1000000006', 'Vintage Leica (Showcase)', 'Showcase',    'Display',    600, 150000, 1),
    ('1000000007', 'SD Card 128GB',            'Accessories', 'Accessory',    2,    600, 3))
INSERT INTO items (sku, name, category_id, item_type, weight_g, price, total_units)
SELECT v.sku, v.name, c.category_id, v.item_type, v.weight_g, v.price, v.total_units
FROM v JOIN categories AS c ON c.name = v.category;

-- The 'photo;dslr' cells, split: 10 distinct tags ...
INSERT INTO tags (name) VALUES
    ('aerial'), ('audio'), ('display'), ('dslr'), ('interview'),
    ('lens'), ('photo'), ('storage'), ('support'), ('video');

-- ... and 11 item-tag links (photo is shared by the Canon and the lens).
WITH v(sku, tag) AS (VALUES
    ('1000000001', 'photo'),   ('1000000001', 'dslr'),
    ('1000000002', 'photo'),   ('1000000002', 'lens'),
    ('1000000003', 'video'),   ('1000000003', 'aerial'),
    ('1000000004', 'support'),
    ('1000000005', 'audio'),   ('1000000005', 'interview'),
    ('1000000006', 'display'),
    ('1000000007', 'storage'))
INSERT INTO item_tags (sku, tag_id)
SELECT v.sku, t.tag_id
FROM v JOIN tags AS t ON t.name = v.tag;

-- rentals.csv (an empty return_date becomes NULL: still on rental)
INSERT INTO rentals (rental_id, customer_id, sku, issue_date, due_date, return_date) VALUES
    ('RN001', 'C002', '1000000003', '2026-10-24', '2026-10-29', NULL),
    ('RN002', 'C004', '1000000001', '2026-10-28', '2026-10-31', NULL),
    ('RN003', 'C003', '1000000004', '2026-10-30', '2026-11-06', NULL),
    ('RN004', 'C001', '1000000002', '2026-09-10', '2026-09-13', '2026-09-13'),
    ('RN005', 'C001', '1000000007', '2026-08-01', '2026-08-03', '2026-08-23'),
    ('RN006', 'C003', '1000000003', '2026-08-05', '2026-08-12', '2026-08-10'),
    ('RN007', 'C002', '1000000001', '2026-07-10', '2026-07-15', '2026-07-15'),
    ('RN008', 'C002', '1000000005', '2026-06-01', '2026-06-06', '2026-06-09'),
    ('RN009', 'C004', '1000000005', '2026-07-01', '2026-07-04', '2026-07-13'),
    ('RN010', 'C004', '1000000001', '2026-07-20', '2026-07-23', '2026-07-26');

-- fines.csv ('yes' -> 1, 'no' -> 0)
INSERT INTO fines (rental_id, amount, paid) VALUES
    ('RN005', 600, 1),
    ('RN008', 300, 1),
    ('RN009', 450, 0),
    ('RN010', 150, 0);

COMMIT;

-- Check: expected 7 items, 10 tags, 5 customers, 10 rentals, 4 fines, 8 categories, 3 open
SELECT (SELECT COUNT(*) FROM items)                            AS items,
       (SELECT COUNT(*) FROM tags)                             AS tags,
       (SELECT COUNT(*) FROM customers)                        AS customers,
       (SELECT COUNT(*) FROM rentals)                          AS rentals,
       (SELECT COUNT(*) FROM fines)                            AS fines,
       (SELECT COUNT(*) FROM categories)                       AS categories,
       (SELECT COUNT(*) FROM rentals WHERE return_date IS NULL) AS open_rentals;
