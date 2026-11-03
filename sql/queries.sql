-- GearShare Mini: the owner's 12 business questions.
--
-- Run:  python -m sql.run_sql sql/queries.sql
--
-- "Today" is 2026-11-03 for every sample, written as a literal here. In the
-- Python engine (Part B) it is passed in as a ? parameter instead.
-- Each query: the business question, then the join used and why.


-- Q1  Items tagged 'photo', with all their tags
-- Question: which items carry the 'photo' tag, and what are ALL their tags (not just 'photo')?
-- Join: INNER JOIN items -> item_tags -> tags, because we only want items that HAVE tags.
--       The subquery picks the photo items first; joining on WHERE tag = 'photo' alone
--       would hide their other tags (dslr, lens).
SELECT i.name, t.name AS tag
FROM items AS i
JOIN item_tags AS it ON it.sku = i.sku
JOIN tags      AS t  ON t.tag_id = it.tag_id
WHERE i.sku IN (SELECT it2.sku
                FROM item_tags AS it2
                JOIN tags AS t2 ON t2.tag_id = it2.tag_id
                WHERE t2.name = 'photo')
ORDER BY i.name, t.name;


-- Q2  Items currently on rental, and who has them
-- Question: what is out of the shop right now, and with whom?
-- Join: INNER JOIN rentals -> customers and -> items. Every rental has exactly one
--       customer and one item (NOT NULL foreign keys), so nothing can be lost.
SELECT r.rental_id, c.name AS customer, i.name AS item
FROM rentals   AS r
JOIN customers AS c ON c.customer_id = r.customer_id
JOIN items     AS i ON i.sku = r.sku
WHERE r.return_date IS NULL
ORDER BY r.rental_id;


-- Q3  Overdue rentals with days overdue
-- Question: who should the staff call today, and how late are they?
-- Join: INNER JOIN, same reason as Q2: we only want rentals, with their customer and item.
--       R10: due today is not late, so the filter is due_date < today, not <=.
SELECT c.name AS customer, i.name AS item, r.due_date,
       CAST(julianday('2026-11-03') - julianday(r.due_date) AS INTEGER) AS days_overdue
FROM rentals   AS r
JOIN customers AS c ON c.customer_id = r.customer_id
JOIN items     AS i ON i.sku = r.sku
WHERE r.return_date IS NULL
  AND r.due_date < '2026-11-03'
ORDER BY days_overdue DESC, r.rental_id;


-- Q4  Top 3 items by number of rentals (ties broken by name)
-- Question: which gear is most popular, so the owner knows what to buy more of?
-- Join: INNER JOIN items -> rentals. Items never rented have a count of 0 and can't
--       be in a top 3 here, so dropping them changes nothing.
SELECT i.name AS item, COUNT(*) AS rentals
FROM items   AS i
JOIN rentals AS r ON r.sku = i.sku
GROUP BY i.sku, i.name
ORDER BY rentals DESC, i.name
LIMIT 3;


-- Q5  Items that have never been rented
-- Question: which stock is just sitting on the shelf?
-- Join: LEFT JOIN items -> rentals, keeping every item even with NO matching rental;
--       those rows have NULL rental columns, and WHERE ... IS NULL keeps only them.
--       An INNER JOIN would throw away exactly the rows we are looking for.
SELECT i.name
FROM items AS i
LEFT JOIN rentals AS r ON r.sku = i.sku
WHERE r.rental_id IS NULL
ORDER BY i.name;


-- Q6  Customers with no rental in the last 90 days (since 2026-08-05)
-- Question: which customers have gone quiet and might need a reminder?
-- Join: LEFT JOIN customers -> rentals, with the 90-day filter INSIDE the ON clause.
--       Putting it in WHERE would turn the LEFT JOIN back into an INNER JOIN and lose
--       Pooja (never rented) entirely. Rows with no recent rental come back as NULL.
SELECT c.name
FROM customers AS c
LEFT JOIN rentals AS r
       ON r.customer_id = c.customer_id
      AND r.issue_date >= date('2026-11-03', '-90 days')
WHERE r.rental_id IS NULL
ORDER BY c.name;


-- Q7  Total fines per tier per month (month the item was returned)
-- Question: how much fine income does each membership tier bring in, month by month?
-- Join: INNER JOIN fines -> rentals -> customers. Only rentals WITH a fine matter,
--       so starting from fines and joining inward is the natural, smallest set.
--       Note: the tier is the customer's CURRENT tier (tiers are not stored per rental).
SELECT c.tier, strftime('%Y-%m', r.return_date) AS month, SUM(f.amount) AS total_fines
FROM fines     AS f
JOIN rentals   AS r ON r.rental_id = f.rental_id
JOIN customers AS c ON c.customer_id = r.customer_id
GROUP BY c.tier, month
ORDER BY c.tier, month;


-- Q8  Fines paid vs pending
-- Question: how much fine money has come in, and how much is still owed?
-- Join: none needed; one table. CASE turns the 0/1 flag into a readable label.
SELECT CASE f.paid WHEN 1 THEN 'Paid' ELSE 'Pending' END AS status,
       SUM(f.amount) AS total
FROM fines AS f
GROUP BY status
ORDER BY status;


-- Q9  Customers who rented from at least 3 different categories
-- Question: who are our broadest customers (good targets for a Pro upgrade)?
-- Join: INNER JOIN customers -> rentals -> items. A customer with no rentals has
--       0 categories and can't reach 3, so they may safely be dropped.
--       COUNT(DISTINCT ...) so renting the Canon twice still counts Cameras once.
SELECT c.name, COUNT(DISTINCT i.category_id) AS categories
FROM customers AS c
JOIN rentals   AS r ON r.customer_id = c.customer_id
JOIN items     AS i ON i.sku = r.sku
GROUP BY c.customer_id, c.name
HAVING COUNT(DISTINCT i.category_id) >= 3
ORDER BY categories DESC, c.name;


-- Q10 Categories where the average completed rental lasts more than 4 days
-- Question: which kinds of gear do customers keep the longest?
-- Join: INNER JOIN categories -> items -> rentals, completed rentals only
--       (return_date IS NOT NULL): an open rental has no length yet.
--       Length = return_date - issue_date in days.
SELECT cat.name AS category,
       ROUND(AVG(julianday(r.return_date) - julianday(r.issue_date)), 1) AS avg_days
FROM categories AS cat
JOIN items      AS i ON i.category_id = cat.category_id
JOIN rentals    AS r ON r.sku = i.sku
WHERE r.return_date IS NOT NULL
GROUP BY cat.category_id, cat.name
HAVING AVG(julianday(r.return_date) - julianday(r.issue_date)) > 4
ORDER BY avg_days DESC;


-- Q11 Units available right now, per item
-- Question: what can a customer walk out with today?
-- Join: LEFT JOIN items -> OPEN rentals (return_date IS NULL inside ON), so items with
--       no open rental still appear, with COUNT(r.rental_id) = 0 (COUNT of a column
--       skips NULLs; COUNT(*) would wrongly count 1). Availability is CALCULATED (D19).
--       The display item shows 1 = its unit is physically in the shop; whether it can
--       be RENTED is item_type's job (R1), not this count's (DECISIONS D23).
SELECT i.name, i.total_units - COUNT(r.rental_id) AS available
FROM items AS i
LEFT JOIN rentals AS r
       ON r.sku = i.sku
      AND r.return_date IS NULL
GROUP BY i.sku, i.name, i.total_units
ORDER BY i.sku;


-- Q12 The pair of items most often rented by the same customer
-- Question: which two items go together, for bundles or shelf placement?
-- Join: SELF-JOIN of "who rented what" (one row per customer+item, DISTINCT so
--       renting the Canon twice counts once) with itself on the same customer.
--       a.name < b.name keeps each pair once, in a fixed order, and never pairs an item with itself.
WITH customer_items AS (
    SELECT DISTINCT r.customer_id, i.sku, i.name
    FROM rentals AS r
    JOIN items   AS i ON i.sku = r.sku
)
SELECT a.name AS item_a, b.name AS item_b, COUNT(*) AS customers
FROM customer_items AS a
JOIN customer_items AS b
  ON b.customer_id = a.customer_id
 AND a.name < b.name
GROUP BY a.sku, b.sku
ORDER BY customers DESC, item_a, item_b
LIMIT 1;
