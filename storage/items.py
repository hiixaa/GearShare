"""Table group: items, categories, tags, item_tags."""

from items import ITEM_TYPES


class ItemRepository:
    def __init__(self, db):
        self.db = db

    def all(self):
        """Every item as the right GearItem subclass, in SKU order, with its tags."""
        tags = {}
        # rowid = the order the tags were added, so 'video;aerial' stays video first.
        for row in self.db.query("""
                SELECT it.sku, t.name
                FROM item_tags AS it
                JOIN tags AS t ON t.tag_id = it.tag_id
                ORDER BY it.rowid"""):
            tags.setdefault(row["sku"], []).append(row["name"])

        rows = self.db.query("""
            SELECT i.sku, i.name, i.item_type, i.weight_g, i.price, i.total_units,
                   c.name AS category, p.name AS parent_category
            FROM items AS i
            JOIN categories AS c ON c.category_id = i.category_id
            LEFT JOIN categories AS p ON p.category_id = c.parent_id
            ORDER BY i.sku""")
        return [ITEM_TYPES[r["item_type"]](
                    sku=r["sku"], name=r["name"], tags=tags.get(r["sku"], []),
                    category=r["category"], parent_category=r["parent_category"],
                    weight_g=r["weight_g"], price=r["price"], total_units=r["total_units"])
                for r in rows]

    def add(self, item):
        """Insert a new item, creating its category / parent / tags if they are new."""
        category_id = self._category_id(item.category, item.parent_category)
        self.db.execute(
            "INSERT INTO items (sku, name, category_id, item_type, weight_g, price, total_units)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (item.sku, item.name, category_id, item.type_name(),
             item.weight_g, item.price, item.total_units))
        for tag in item.tags:
            self.db.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
            self.db.execute(
                "INSERT INTO item_tags (sku, tag_id)"
                " SELECT ?, tag_id FROM tags WHERE name = ?", (item.sku, tag))

    def _category_id(self, name, parent_name):
        row = self.db.query("SELECT category_id FROM categories WHERE name = ?", (name,))
        if row:
            return row[0]["category_id"]
        parent_id = self._category_id(parent_name, None) if parent_name else None
        return self.db.execute(
            "INSERT INTO categories (name, parent_id) VALUES (?, ?)",
            (name, parent_id)).lastrowid
