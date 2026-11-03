-- GearShare Mini: database schema (SQLite)
--
-- Run:  python -m sql.run_sql sql/schema.sql
--
-- Dates are ISO text 'YYYY-MM-DD' (SQLite has no DATE type). ISO text sorts in
-- date order, and CHECK (date(x) IS x) rejects anything that isn't a real date.
-- Every ON DELETE below is a deliberate choice; see DECISIONS D20.

PRAGMA foreign_keys = ON;   -- SQLite leaves foreign keys OFF unless asked

-- Drop in reverse dependency order so the script can be re-run.
DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS waiting_list;
DROP TABLE IF EXISTS fines;
DROP TABLE IF EXISTS rentals;
DROP TABLE IF EXISTS item_tags;
DROP TABLE IF EXISTS tags;
DROP TABLE IF EXISTS items;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS membership_tiers;


-- The Rulebook's tier table: one row per tier (3NF: tier -> limits).
CREATE TABLE membership_tiers (
    tier             TEXT    PRIMARY KEY,
    max_items        INTEGER NOT NULL CHECK (max_items > 0),          -- R3
    rental_days      INTEGER NOT NULL CHECK (rental_days > 0),
    late_fee_per_day INTEGER NOT NULL CHECK (late_fee_per_day >= 0)   -- R5
);

CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY CHECK (customer_id GLOB 'C[0-9]*'),
    name        TEXT NOT NULL CHECK (length(trim(name)) > 0),
    email       TEXT NOT NULL UNIQUE CHECK (email LIKE '%_@_%'),
    tier        TEXT NOT NULL
                REFERENCES membership_tiers (tier)
                ON UPDATE CASCADE      -- renaming a tier renames it for its customers
                ON DELETE RESTRICT     -- a tier with customers can't vanish
);

-- Self-reference: a category's parent is another category (NULL = top level).
CREATE TABLE categories (
    category_id INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL UNIQUE,
    parent_id   INTEGER
                REFERENCES categories (category_id)
                ON DELETE RESTRICT,    -- can't delete Photography while Cameras is under it
    CHECK (parent_id IS NULL OR parent_id <> category_id)
);

CREATE TABLE items (
    sku         TEXT    PRIMARY KEY                                    -- PK = UNIQUE (R9)
                CHECK (length(sku) = 10 AND sku NOT GLOB '*[^0-9]*'),  -- exactly 10 digits
    name        TEXT    NOT NULL CHECK (length(trim(name)) > 0),
    category_id INTEGER NOT NULL
                REFERENCES categories (category_id)
                ON DELETE RESTRICT,    -- a category with items can't be deleted
    item_type   TEXT    NOT NULL CHECK (item_type IN ('Equipment', 'Accessory', 'Display')),
    weight_g    INTEGER NOT NULL CHECK (weight_g >= 0),
    price       INTEGER NOT NULL CHECK (price >= 0),
    total_units INTEGER NOT NULL CHECK (total_units >= 0)              -- units not negative
);

CREATE TABLE tags (
    tag_id INTEGER PRIMARY KEY,
    name   TEXT    NOT NULL UNIQUE CHECK (length(trim(name)) > 0)
);

-- Junction table: many items <-> many tags.
CREATE TABLE item_tags (
    sku    TEXT    NOT NULL REFERENCES items (sku) ON DELETE CASCADE,  -- tags go with the item
    tag_id INTEGER NOT NULL REFERENCES tags (tag_id) ON DELETE CASCADE, -- and with the tag
    PRIMARY KEY (sku, tag_id)
);

CREATE TABLE rentals (
    rental_id   TEXT    PRIMARY KEY CHECK (rental_id GLOB 'RN[0-9][0-9][0-9]*'),
    customer_id TEXT    NOT NULL
                REFERENCES customers (customer_id)
                ON DELETE RESTRICT,    -- keep the shop's history: see DECISIONS D20
    sku         TEXT    NOT NULL
                REFERENCES items (sku)
                ON DELETE RESTRICT,    -- an item that was ever rented can't be deleted
    -- IS, not =: date('2026-13-03') is NULL, and a CHECK that evaluates to
    -- NULL counts as PASSED. With IS, NULL IS '2026-13-03' is false -> rejected.
    issue_date  TEXT    NOT NULL CHECK (date(issue_date) IS issue_date),
    due_date    TEXT    NOT NULL CHECK (date(due_date) IS due_date),
    return_date TEXT             CHECK (return_date IS NULL OR date(return_date) IS return_date),
    extensions  INTEGER NOT NULL DEFAULT 0 CHECK (extensions BETWEEN 0 AND 2),   -- R6
    CHECK (due_date >= issue_date),                                  -- due not before issue
    CHECK (return_date IS NULL OR return_date >= issue_date)
);

-- At most one fine per rental, so the rental ID is also the fine's key (1 : 0..1).
CREATE TABLE fines (
    rental_id TEXT    PRIMARY KEY
              REFERENCES rentals (rental_id)
              ON DELETE RESTRICT,      -- money owed must not disappear with a rental
    amount    INTEGER NOT NULL CHECK (amount >= 0),                  -- fine not negative
    paid      INTEGER NOT NULL DEFAULT 0 CHECK (paid IN (0, 1))
);

-- R7 queue. entry_id only grows, so ORDER BY entry_id = first come, first served.
-- 'reserved' = notified that a unit is free and held for them (DECISIONS D7).
CREATE TABLE waiting_list (
    entry_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    sku         TEXT    NOT NULL REFERENCES items (sku) ON DELETE CASCADE,
    customer_id TEXT    NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    joined_at   TEXT    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'waiting' CHECK (status IN ('waiting', 'reserved')),
    UNIQUE (sku, customer_id)          -- nobody is in the same queue twice
);

-- History of what happened. Deliberately NO foreign keys: the log must still
-- say "RN011 was rented, then undone" after RN011 itself has been deleted.
CREATE TABLE audit_log (
    log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    logged_at   TEXT    NOT NULL,
    action      TEXT    NOT NULL
                CHECK (action IN ('rent', 'return_item', 'extend', 'undo_rent', 'undo_return')),
    customer_id TEXT    NOT NULL,
    sku         TEXT    NOT NULL,
    rental_id   TEXT    NOT NULL
);
