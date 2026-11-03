"""Table group: rentals, fines, waiting_list, audit_log (everything that happens)."""

from rentals import parse_date


def _iso(day):
    return day.isoformat() if day else None


class RentalRepository:
    def __init__(self, db):
        self.db = db

    # --- rentals -------------------------------------------------------------------

    def all(self):
        """Rental rows as dicts with real dates, oldest ID first (RN9 before RN10)."""
        rows = self.db.query("""
            SELECT rental_id, customer_id, sku, issue_date, due_date, return_date, extensions
            FROM rentals
            ORDER BY CAST(substr(rental_id, 3) AS INTEGER)""")
        return [{**dict(r),
                 "issue_date": parse_date(r["issue_date"]),
                 "due_date": parse_date(r["due_date"]),
                 "return_date": parse_date(r["return_date"])} for r in rows]

    def add(self, rental):
        self.db.execute(
            "INSERT INTO rentals (rental_id, customer_id, sku, issue_date, due_date,"
            " return_date, extensions) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (rental.rental_id, rental.customer.customer_id, rental.item.sku,
             _iso(rental.issue_date), _iso(rental.due_date), _iso(rental.return_date),
             rental.extensions))

    def update(self, rental):
        """Save the parts of a rental that change: due date, return date, extensions."""
        self.db.execute(
            "UPDATE rentals SET due_date = ?, return_date = ?, extensions = ?"
            " WHERE rental_id = ?",
            (_iso(rental.due_date), _iso(rental.return_date), rental.extensions,
             rental.rental_id))

    def delete(self, rental_id):
        self.db.execute("DELETE FROM rentals WHERE rental_id = ?", (rental_id,))

    # --- fines -----------------------------------------------------------------------

    def all_fines(self):
        return [dict(r) for r in self.db.query(
            "SELECT rental_id, amount, paid FROM fines ORDER BY rental_id")]

    def add_fine(self, fine):
        self.db.execute("INSERT INTO fines (rental_id, amount, paid) VALUES (?, ?, ?)",
                        (fine.rental_id, fine.amount, int(fine.paid)))

    def delete_fine(self, rental_id):
        self.db.execute("DELETE FROM fines WHERE rental_id = ?", (rental_id,))

    # --- waiting list (R7) -------------------------------------------------------------

    def all_waiting(self):
        """Queue entries in arrival order: entry_id only ever grows."""
        return [dict(r) for r in self.db.query(
            "SELECT sku, customer_id, status FROM waiting_list ORDER BY entry_id")]

    def add_waiting(self, sku, customer_id, joined_at, status="waiting"):
        self.db.execute(
            "INSERT INTO waiting_list (sku, customer_id, joined_at, status) VALUES (?, ?, ?, ?)",
            (sku, customer_id, joined_at, status))

    def set_waiting_status(self, sku, customer_id, status):
        """'waiting' -> 'reserved' when a unit is held for them. The entry_id
        (their place in the queue) does not change, so undo restores the place."""
        self.db.execute(
            "UPDATE waiting_list SET status = ? WHERE sku = ? AND customer_id = ?",
            (status, sku, customer_id))

    def remove_waiting(self, sku, customer_id):
        self.db.execute("DELETE FROM waiting_list WHERE sku = ? AND customer_id = ?",
                        (sku, customer_id))

    # --- audit log -------------------------------------------------------------------

    def all_audit(self):
        return [{"time": r["logged_at"], "action": r["action"], "customer": r["customer_id"],
                 "item": r["sku"], "rental_id": r["rental_id"]}
                for r in self.db.query(
                    "SELECT logged_at, action, customer_id, sku, rental_id"
                    " FROM audit_log ORDER BY log_id")]

    def add_audit(self, entry):
        self.db.execute(
            "INSERT INTO audit_log (logged_at, action, customer_id, sku, rental_id)"
            " VALUES (?, ?, ?, ?, ?)",
            (entry["time"], entry["action"], entry["customer"], entry["item"],
             entry["rental_id"]))
