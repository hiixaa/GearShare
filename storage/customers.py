"""Table group: customers, membership_tiers."""

from customers import TIER_CLASSES


class CustomerRepository:
    def __init__(self, db):
        self.db = db

    def all(self):
        """Every customer as the right tier subclass (BasicCustomer, ...), in ID order."""
        rows = self.db.query(
            "SELECT customer_id, name, email, tier FROM customers ORDER BY customer_id")
        return [TIER_CLASSES[r["tier"]](r["customer_id"], r["name"], r["email"])
                for r in rows]
