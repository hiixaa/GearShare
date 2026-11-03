"""Rentals and fines.

A Rental links one customer to one item for a period. It owns the date
maths: days late (R10), late fee capped at the item price (R5) and the
extension counter (R6).
"""

from datetime import date, timedelta


class Rental:
    # Class attribute: ONE counter shared by every Rental, because rental IDs
    # must be unique across the whole shop, not per object.
    _next_number = 1

    MAX_EXTENSIONS = 2  # R6, the same for every rental -> class attribute

    def __init__(self, rental_id, customer, item, issue_date, due_date,
                 return_date=None, extensions=0):
        # Instance attributes: each rental has its own dates and counter.
        if due_date < issue_date:
            raise ValueError("Due date cannot be before issue date.")
        if return_date is not None and return_date < issue_date:
            raise ValueError("Return date cannot be before issue date.")
        self.rental_id = rental_id
        self.customer = customer
        self.item = item
        self.issue_date = issue_date
        self.due_date = due_date
        self.return_date = return_date
        self.extensions = extensions

    # --- rental ID counter -----------------------------------------------------

    @classmethod
    def next_id(cls):
        """Hand out the next rental ID: RN011, RN012, ..."""
        rental_id = f"RN{cls._next_number:03d}"
        cls._next_number += 1
        return rental_id

    @classmethod
    def reset_counter(cls, existing_ids):
        """After loading, continue numbering after the highest existing ID."""
        numbers = [int(rid[2:]) for rid in existing_ids]
        cls._next_number = max(numbers, default=0) + 1

    # --- state -----------------------------------------------------------------

    def is_open(self):
        return self.return_date is None

    def days_late(self, on):
        """R10: returning on the due date is not late; the day after is 1."""
        return max(0, (on - self.due_date).days)

    def is_overdue(self, today):
        return self.is_open() and self.days_late(today) > 0

    def late_fee(self, on):
        """R5: days late x tier rate, never more than the item's price."""
        fee = self.days_late(on) * self.customer.late_fee_per_day()
        return min(fee, self.item.price)

    def extend(self):
        """R6: push the due date by the customer's rental period.

        The rule checks (R2, R6) are done by GearShare before calling this.
        """
        self.due_date += timedelta(days=self.customer.rental_period())
        self.extensions += 1

    def close(self, on):
        self.return_date = on

    # --- display ---------------------------------------------------------------

    def __str__(self):
        return (f"{self.rental_id}: {self.customer.name} - {self.item.name} "
                f"(due {self.due_date})")

    def __repr__(self):
        return (f"Rental(rental_id={self.rental_id!r}, "
                f"customer={self.customer.customer_id!r}, sku={self.item.sku!r}, "
                f"issue_date={self.issue_date}, due_date={self.due_date}, "
                f"return_date={self.return_date}, extensions={self.extensions})")


class Fine:
    """A late fee charged for one rental."""

    def __init__(self, rental_id, amount, paid=False):
        self.rental_id = rental_id
        self.amount = amount
        self.paid = paid

    @property
    def amount(self):
        return self._amount

    @amount.setter
    def amount(self, value):
        value = int(value)
        if value < 0:
            raise ValueError("Fine cannot be negative.")
        self._amount = value

    def __str__(self):
        status = "paid" if self.paid else "unpaid"
        return f"Fine for {self.rental_id}: {self.amount} ({status})"

    def __repr__(self):
        return (f"Fine(rental_id={self.rental_id!r}, amount={self.amount}, "
                f"paid={self.paid})")


def parse_date(text):
    """'2026-11-03' -> date(2026, 11, 3); empty text -> None."""
    text = (text or "").strip()
    return date.fromisoformat(text) if text else None
