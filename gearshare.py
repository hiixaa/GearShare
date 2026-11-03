"""GearShare: the service class that enforces the Rental Rulebook.

Every date-dependent method receives `today` as a parameter instead of
calling date.today(), so tests can choose the date.
"""

import csv
import functools
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from customers import TIER_CLASSES
from errors import (
    CustomerNotFoundError,
    DuplicateRentalError,
    ExtensionNotAllowedError,
    ItemNotAvailableError,
    ItemNotFoundError,
    ItemNotRentableError,
    RentalLimitExceededError,
    RentalNotFoundError,
    UnpaidFinesError,
    WaitingListError,
)
from items import item_from_row, validate_sku
from rentals import Fine, Rental, parse_date

FINE_LIMIT = 500  # R4: renting is blocked only when unpaid fines are ABOVE this


def rupees(amount):
    """Money is written like ₹100 with no decimals."""
    return f"₹{amount}"


def audit(method):
    """Decorator: after a successful rent / return_item / extend, append
    time, action, customer and item to the service's audit_log.

    If the method raises, nothing is logged: the exception passes straight
    through, because the append line is never reached.
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        result = method(self, *args, **kwargs)
        rental = getattr(result, "rental", result)  # ReturnReceipt or Rental
        self.audit_log.append({
            "time": datetime.now().isoformat(timespec="seconds"),
            "action": method.__name__,
            "customer": rental.customer.customer_id,
            "item": rental.item.sku,
            "rental_id": rental.rental_id,
        })
        return result
    return wrapper


@dataclass
class ReturnReceipt:
    """What return_item() hands back to the caller."""
    rental: Rental
    days_late: int
    fee: int
    next_customer: object = None  # Customer notified from the waiting list, or None


class GearShare:
    def __init__(self):
        # dict by SKU / customer ID: O(1) lookup for every rent/return/search.
        self.items = {}
        self.customers = {}
        # list: rentals are only ever appended and read in order (RN001, RN002, ...).
        self.rentals = []
        self.fines = []
        # Indexes (Phase 2, see D9): extra dicts pointing at the same objects,
        # so the hot paths do not have to scan the whole history.
        self.open_rentals = {}           # rental ID -> open Rental (insertion order kept)
        self.rentals_by_customer = {}    # customer ID -> [Rental, ...]
        self.fines_by_rental = {}        # rental ID -> [Fine, ...]
        # customer ID -> set of SKUs they hold right now.
        # set: R8 is an O(1) "sku in held" test, and len(held) is the R3 count.
        self.held_skus = {}
        # SKU -> customer IDs waiting, first come first served (R7).
        self.waiting_lists = {}
        # SKU -> customer IDs who were notified a unit is free and may rent it.
        self.reservations = {}
        self.audit_log = []

    # ------------------------------------------------------------------ loading

    def load_data(self, folder="data"):
        """Read the four CSV files and rebuild availability from open rentals."""
        folder = Path(folder)
        self._load_items(folder / "gear.csv")
        self._load_customers(folder / "customers.csv")
        self._load_rentals(folder / "rentals.csv")
        self._load_fines(folder / "fines.csv")
        Rental.reset_counter(r.rental_id for r in self.rentals)
        return {
            "items": len(self.items),
            "customers": len(self.customers),
            "rentals": len(self.rentals),
            "fines": len(self.fines),
        }

    @staticmethod
    def _read_csv(path):
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def _load_items(self, path):
        for line_no, row in enumerate(self._read_csv(path), start=2):
            try:
                self.add_item(item_from_row(row))
            except ValueError as e:
                raise ValueError(f"{path.name} line {line_no}: {e}") from None

    def _load_customers(self, path):
        for row in self._read_csv(path):
            customer_class = TIER_CLASSES[row["membership_type"]]
            customer = customer_class(row["customer_id"], row["name"], row["email"])
            self.customers[customer.customer_id] = customer
            self.held_skus[customer.customer_id] = set()
            self.rentals_by_customer[customer.customer_id] = []

    def _load_rentals(self, path):
        for row in self._read_csv(path):
            self._add_rental(Rental(
                rental_id=row["rental_id"],
                customer=self.customers[row["customer_id"]],
                item=self.items[row["sku"]],
                issue_date=parse_date(row["issue_date"]),
                due_date=parse_date(row["due_date"]),
                return_date=parse_date(row["return_date"]),
            ))

    def _load_fines(self, path):
        for row in self._read_csv(path):
            paid = row["paid"].strip().lower() == "yes"
            self._add_fine(Fine(row["rental_id"], row["amount"], paid))

    # ------------------------------------------------------------------ bookkeeping
    # Every item, rental and fine goes through these methods, so the
    # collections and the indexes can never disagree.

    def add_item(self, item):
        """Add a new item to the catalogue. R9: a SKU identifies one item."""
        if item.sku in self.items:
            raise ValueError(f"duplicate SKU {item.sku} "
                             f"(already used by '{self.items[item.sku].name}').")
        self.items[item.sku] = item

    def _add_rental(self, rental):
        self.rentals.append(rental)
        self.rentals_by_customer[rental.customer.customer_id].append(rental)
        if rental.is_open():  # rebuild availability from unreturned rentals
            self.open_rentals[rental.rental_id] = rental
            rental.item.check_out_unit()
            self.held_skus[rental.customer.customer_id].add(rental.item.sku)

    def _add_fine(self, fine):
        self.fines.append(fine)
        self.fines_by_rental.setdefault(fine.rental_id, []).append(fine)

    # ------------------------------------------------------------------ lookups

    def get_customer(self, customer_id):
        customer_id = str(customer_id).strip().upper()
        try:
            return self.customers[customer_id]
        except KeyError:
            raise CustomerNotFoundError(f"No customer with ID {customer_id}.") from None

    def get_item(self, sku):
        sku = validate_sku(sku)  # raises InvalidSKUError (R9)
        try:
            return self.items[sku]
        except KeyError:
            raise ItemNotFoundError(f"No item with SKU {sku}.") from None

    def get_open_rental(self, rental_id):
        rental_id = str(rental_id).strip().upper()
        try:
            return self.open_rentals[rental_id]
        except KeyError:
            raise RentalNotFoundError(f"No open rental with ID {rental_id}.") from None

    def unpaid_fines(self, customer_id):
        """O(k), k = this customer's rentals, instead of scanning the whole shop."""
        return sum(fine.amount
                   for rental in self.rentals_by_customer[customer_id]
                   for fine in self.fines_by_rental.get(rental.rental_id, [])
                   if not fine.paid)

    def active_count(self, customer_id):
        return len(self.held_skus[customer_id])

    def waiting_for(self, sku):
        """Customers still waiting, plus those notified but not yet served."""
        return self.reservations.get(sku, []) + self.waiting_lists.get(sku, [])

    # ------------------------------------------------------------------ catalogue

    def list_items(self):
        return list(self.items.values())

    def search(self, text):
        """Case-insensitive match on name or any tag."""
        text = text.strip().lower()
        return [item for item in self.items.values()
                if text in item.name.lower()
                or any(text in tag.lower() for tag in item.tags)]

    # ------------------------------------------------------------------ rent

    @audit
    def rent(self, customer_id, sku, today):
        """Rent one unit. Checks run in the Rulebook's fixed order; the first
        broken rule is the one reported."""
        # 1. the customer exists
        customer = self.get_customer(customer_id)
        # 2. the SKU has 10 digits and exists
        item = self.get_item(sku)
        # 3. R1: not a display item
        if not item.is_rentable():
            raise ItemNotRentableError(
                f"'{item.name}' is a display item and cannot be rented.")
        # 4. R4: unpaid fines not above the limit
        owed = self.unpaid_fines(customer.customer_id)
        if owed > FINE_LIMIT:
            raise UnpaidFinesError(
                f"{customer.name} has unpaid fines of {rupees(owed)} "
                f"(limit {rupees(FINE_LIMIT)}).")
        # 5. R3: below the tier's item limit
        held = self.held_skus[customer.customer_id]
        if len(held) >= customer.max_items():
            raise RentalLimitExceededError(
                f"{customer.name} already has {len(held)} of "
                f"{customer.max_items()} items on rental.")
        # 6. R8: not already holding a unit of this item
        if item.sku in held:
            raise DuplicateRentalError(
                f"{customer.name} already has a unit of '{item.name}'.")
        # 7. availability (R7): units promised to notified customers are not free
        reserved = self.reservations.get(item.sku, [])
        has_reservation = customer.customer_id in reserved
        if not has_reservation and item.available_units <= len(reserved):
            raise ItemNotAvailableError(f"No units of '{item.name}' are available.")

        if has_reservation:
            reserved.remove(customer.customer_id)
        rental = Rental(
            rental_id=Rental.next_id(),
            customer=customer,
            item=item,
            issue_date=today,
            due_date=today + timedelta(days=item.rental_days(customer)),
        )
        self._add_rental(rental)  # also takes the unit and records it as held
        return rental

    # ------------------------------------------------------------------ return

    @audit
    def return_item(self, rental_id, today):
        rental = self.get_open_rental(rental_id)
        days_late = rental.days_late(today)
        fee = rental.late_fee(today)

        rental.close(today)
        del self.open_rentals[rental.rental_id]
        rental.item.check_in_unit()
        self.held_skus[rental.customer.customer_id].discard(rental.item.sku)
        if fee > 0:
            self._add_fine(Fine(rental.rental_id, fee, paid=False))

        # R7: the first person waiting is served first.
        next_customer = None
        queue = self.waiting_lists.get(rental.item.sku)
        if queue:
            next_id = queue.pop(0)
            self.reservations.setdefault(rental.item.sku, []).append(next_id)
            next_customer = self.customers[next_id]
        return ReturnReceipt(rental, days_late, fee, next_customer)

    # ------------------------------------------------------------------ extend

    @audit
    def extend(self, rental_id, today):
        rental = self.get_open_rental(rental_id)
        item = rental.item
        if not item.can_extend():
            raise ExtensionNotAllowedError("Accessories cannot be extended.", rule="R2")
        if rental.extensions >= Rental.MAX_EXTENSIONS:
            raise ExtensionNotAllowedError(
                f"'{item.name}' has already been extended "
                f"{Rental.MAX_EXTENSIONS} times.")
        if self.waiting_for(item.sku):
            raise ExtensionNotAllowedError(
                f"'{item.name}' cannot be extended because another customer is waiting.")
        rental.extend()
        return rental

    # ------------------------------------------------------------------ waiting list

    def join_waiting_list(self, customer_id, sku):
        """Add the customer to the end of the item's waiting list (R7).
        Returns their position (1 = next to be served)."""
        customer = self.get_customer(customer_id)
        item = self.get_item(sku)
        if not item.is_rentable():
            raise ItemNotRentableError(
                f"'{item.name}' is a display item and cannot be rented.")
        if item.sku in self.held_skus[customer.customer_id]:
            raise DuplicateRentalError(
                f"{customer.name} already has a unit of '{item.name}'.")
        if customer.customer_id in self.waiting_for(item.sku):
            raise WaitingListError(
                f"{customer.name} is already on the waiting list for '{item.name}'.")
        if item.available_units > len(self.reservations.get(item.sku, [])):
            raise WaitingListError(
                f"'{item.name}' has a unit available. Rent it instead.")
        queue = self.waiting_lists.setdefault(item.sku, [])
        queue.append(customer.customer_id)
        return len(queue)

    # ------------------------------------------------------------------ reports

    def customer_rentals(self, customer_id):
        """The customer's open rentals, oldest first."""
        customer = self.get_customer(customer_id)
        return [r for r in self.rentals_by_customer[customer.customer_id]
                if r.is_open()]

    def iter_overdue(self, today):
        """Generator: yield overdue rentals one at a time, without building
        a list first. Only open rentals can be overdue, so only those are scanned."""
        for rental in self.open_rentals.values():
            if rental.is_overdue(today):
                yield rental

    def overdue_report(self, today):
        """Open rentals past their due date as (rental, days late, fine so far),
        most days late first (ties by rental ID).
        'Fine so far' is not saved: it becomes a real fine only on return."""
        rows = [(r, r.days_late(today), r.late_fee(today))
                for r in self.iter_overdue(today)]
        return sorted(rows, key=lambda row: (-row[1], row[0].rental_id))

    def items_by_category(self):
        """{category: [items sorted by name]}, categories in A-Z order."""
        categories = sorted({item.category for item in self.items.values()})
        return {
            category: sorted(
                (item for item in self.items.values() if item.category == category),
                key=lambda item: item.name)
            for category in categories
        }

    def customers_with_unpaid_fines(self):
        """[(customer, amount owed)], largest amount first, ties by name."""
        owed = map(lambda c: (c, self.unpaid_fines(c.customer_id)),
                   self.customers.values())
        debtors = filter(lambda pair: pair[1] > 0, owed)
        return sorted(debtors, key=lambda pair: (-pair[1], pair[0].name))

