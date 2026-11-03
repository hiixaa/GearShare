"""GearShare: the service class that enforces the Rental Rulebook.

Every date-dependent method receives `today` as a parameter instead of
calling date.today(), so tests can choose the date.

Phase 3: GearShare reads and writes through a storage layer (storage/).
It holds the shop as objects in memory (for polymorphism and the Phase 2
O(1) indexes) and WRITES THROUGH every change to the database, one
transaction per business operation. It contains no SQL (DECISIONS D26).
"""

import csv
import functools
from collections import deque
from contextlib import contextmanager
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
    StorageError,
    UndoNotPossibleError,
    UnpaidFinesError,
    WaitingListError,
)
from items import item_from_row, validate_sku
from rentals import Fine, Rental, parse_date
from storage import NullStorage

FINE_LIMIT = 500  # R4: renting is blocked only when unpaid fines are ABOVE this
UNDO_LIMIT = 20   # how many rent/return actions option 9 can step back through


def rupees(amount):
    """Money is written like ₹100 with no decimals."""
    return f"₹{amount}"


def _now():
    return datetime.now().isoformat(timespec="seconds")


def audit(method):
    """Decorator: run rent / return_item / extend as ONE unit of work, and
    after it succeeds, record time, action, customer and item in the audit log.

    The operation's own writes and its audit row share one database
    transaction (Task 3.6): both are saved, or neither is. If the method
    raises, nothing is logged, because the logging lines are never reached.
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._unit_of_work():
            result = method(self, *args, **kwargs)
            rental = getattr(result, "rental", result)  # ReturnReceipt or Rental
            entry = {
                "time": _now(),
                "action": method.__name__,
                "customer": rental.customer.customer_id,
                "item": rental.item.sku,
                "rental_id": rental.rental_id,
            }
            self.storage.rentals.add_audit(entry)
        self.audit_log.append(entry)
        return result
    return wrapper


@dataclass
class ReturnReceipt:
    """What return_item() hands back to the caller."""
    rental: Rental
    days_late: int
    fee: int
    next_customer: object = None  # Customer notified from the waiting list, or None


@dataclass
class UndoEntry:
    """Everything needed to reverse one rent or return (Phase 2, D14).

    Stores IDs, not the Rental object: undo looks the rental up again and
    checks it can still be reversed, because the shop may have changed since.
    """
    action: str                       # "rent" or "return"
    rental_id: str
    customer_id: str
    used_reservation: bool = False    # rent: the unit was held for this customer (R7)
    fine: object = None               # return: the Fine it created, if any
    served_customer_id: str = None    # return: who moved from the waiting list to a reservation


class GearShare:
    def __init__(self, storage=None):
        # Where data is saved: a real Storage (SQLite) or NullStorage (memory only,
        # used by the Phase 2 benchmarks). GearShare calls the same methods either way.
        self.storage = storage or NullStorage()
        self._clear()

    def _clear(self):
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
        # SKU -> deque of customer IDs waiting, first come first served (R7).
        # deque: popleft() is O(1); list.pop(0) is O(n) (benchmarked in 2.4).
        self.waiting_lists = {}
        # SKU -> customer IDs who were notified a unit is free and may rent it.
        self.reservations = {}
        self.audit_log = []
        # Stack of UndoEntry: append() pushes, pop() takes the latest (LIFO).
        # maxlen keeps only the last UNDO_LIMIT actions; the oldest fall off.
        self.undo_stack = deque(maxlen=UNDO_LIMIT)

    @contextmanager
    def _unit_of_work(self):
        """One business operation = one database transaction.

        If the database refuses anything, the transaction rolls back AND the
        in-memory shop is reloaded from the database, so the two never disagree.
        Rule violations (GearShareError) are raised before anything changes.
        """
        try:
            with self.storage.transaction():
                yield
        except StorageError:
            self.load_data()
            raise

    # ------------------------------------------------------------------ loading

    def load_data(self, folder=None):
        """Load the shop.

        folder=None  -> from the storage layer (the database): the normal case.
        folder=path  -> from the four starter CSV files, in memory only
                        (Phase 1 behaviour; used by the Phase 2 benchmarks).
        Availability is always rebuilt from the rentals with no return date.
        """
        self._clear()
        if folder is None:
            self._load_from_storage()
        else:
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

    def _load_from_storage(self):
        for item in self.storage.items.all():
            self.items[item.sku] = item
        for customer in self.storage.customers.all():
            self._register_customer(customer)
        for row in self.storage.rentals.all():
            self._add_rental(Rental(
                rental_id=row["rental_id"],
                customer=self.customers[row["customer_id"]],
                item=self.items[row["sku"]],
                issue_date=row["issue_date"],
                due_date=row["due_date"],
                return_date=row["return_date"],
                extensions=row["extensions"],
            ))
        for row in self.storage.rentals.all_fines():
            self._add_fine(Fine(row["rental_id"], row["amount"], bool(row["paid"])))
        for row in self.storage.rentals.all_waiting():
            if row["status"] == "reserved":
                self.reservations.setdefault(row["sku"], []).append(row["customer_id"])
            else:
                self.waiting_lists.setdefault(row["sku"], deque()).append(row["customer_id"])
        self.audit_log = self.storage.rentals.all_audit()

    @staticmethod
    def _read_csv(path):
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def _load_items(self, path):
        for line_no, row in enumerate(self._read_csv(path), start=2):
            item = item_from_row(row)
            if item.sku in self.items:
                raise ValueError(f"{path.name} line {line_no}: duplicate SKU {item.sku} "
                                 f"(already used by '{self.items[item.sku].name}').")
            self.items[item.sku] = item

    def _load_customers(self, path):
        for row in self._read_csv(path):
            customer_class = TIER_CLASSES[row["membership_type"]]
            self._register_customer(
                customer_class(row["customer_id"], row["name"], row["email"]))

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
        """Add a new item to the catalogue (and the database). R9: SKUs are unique."""
        if item.sku in self.items:
            raise ValueError(f"duplicate SKU {item.sku} "
                             f"(already used by '{self.items[item.sku].name}').")
        with self._unit_of_work():
            self.storage.items.add(item)
        self.items[item.sku] = item

    def _register_customer(self, customer):
        self.customers[customer.customer_id] = customer
        self.held_skus[customer.customer_id] = set()
        self.rentals_by_customer[customer.customer_id] = []

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
        return [*self.reservations.get(sku, []), *self.waiting_lists.get(sku, [])]

    def waiting_list(self, sku):
        """Customers still in the queue for this item, first in line first."""
        return [self.customers[cid] for cid in self.waiting_lists.get(sku, [])]

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

        rental = Rental(
            rental_id=Rental.next_id(),
            customer=customer,
            item=item,
            issue_date=today,
            due_date=today + timedelta(days=item.rental_days(customer)),
        )
        # Database first: if it refuses, memory has not been touched yet.
        self.storage.rentals.add(rental)
        if has_reservation:
            self.storage.rentals.remove_waiting(item.sku, customer.customer_id)
            reserved.remove(customer.customer_id)
        self._add_rental(rental)  # also takes the unit and records it as held
        self.undo_stack.append(UndoEntry("rent", rental.rental_id, customer.customer_id,
                                         used_reservation=has_reservation))
        return rental

    # ------------------------------------------------------------------ return

    @audit
    def return_item(self, rental_id, today):
        rental = self.get_open_rental(rental_id)
        days_late = rental.days_late(today)
        fee = rental.late_fee(today)

        rental.close(today)
        self.storage.rentals.update(rental)
        del self.open_rentals[rental.rental_id]
        rental.item.check_in_unit()
        self.held_skus[rental.customer.customer_id].discard(rental.item.sku)
        fine = None
        if fee > 0:
            fine = Fine(rental.rental_id, fee, paid=False)
            self.storage.rentals.add_fine(fine)
            self._add_fine(fine)

        # R7: the first person waiting is served first.
        next_customer = None
        queue = self.waiting_lists.get(rental.item.sku)
        if queue:
            next_id = queue.popleft()
            self.storage.rentals.set_waiting_status(rental.item.sku, next_id, "reserved")
            self.reservations.setdefault(rental.item.sku, []).append(next_id)
            next_customer = self.customers[next_id]

        self.undo_stack.append(UndoEntry(
            "return", rental.rental_id, rental.customer.customer_id, fine=fine,
            served_customer_id=next_customer.customer_id if next_customer else None))
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
        self.storage.rentals.update(rental)
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
        with self._unit_of_work():
            self.storage.rentals.add_waiting(item.sku, customer.customer_id, _now())
        queue = self.waiting_lists.setdefault(item.sku, deque())
        queue.append(customer.customer_id)
        return len(queue)

    # ------------------------------------------------------------------ undo

    def undo(self):
        """Reverse the latest rent or return (menu option 9).

        Returns (action, rental), or None when there is nothing to undo.
        Raises UndoNotPossibleError if the shop changed so that it can't be
        reversed any more; that entry is dropped, so the one below it is next.
        """
        if not self.undo_stack:
            return None
        entry = self.undo_stack.pop()
        reverse = {"rent": self._undo_rent, "return": self._undo_return}[entry.action]
        with self._unit_of_work():
            rental = reverse(entry)
            log = {
                "time": _now(),
                "action": f"undo_{entry.action}",
                "customer": entry.customer_id,
                "item": rental.item.sku,
                "rental_id": rental.rental_id,
            }
            self.storage.rentals.add_audit(log)
        self.audit_log.append(log)
        return entry.action, rental

    def _undo_rent(self, entry):
        rental = self.open_rentals.get(entry.rental_id)
        if rental is None:
            raise UndoNotPossibleError(
                f"Cannot undo rental {entry.rental_id}: it has already been returned.")
        sku = rental.item.sku
        self.storage.rentals.delete(rental.rental_id)
        if entry.used_reservation:   # give the held unit back to the same customer
            self.storage.rentals.add_waiting(sku, entry.customer_id, _now(), "reserved")
            self.reservations.setdefault(sku, []).insert(0, entry.customer_id)
        del self.open_rentals[rental.rental_id]
        self.rentals.remove(rental)
        self.rentals_by_customer[entry.customer_id].remove(rental)
        rental.item.check_in_unit()
        self.held_skus[entry.customer_id].discard(sku)
        Rental.release_id(rental.rental_id)
        return rental

    def _undo_return(self, entry):
        rental = next(r for r in self.rentals_by_customer[entry.customer_id]
                      if r.rental_id == entry.rental_id)
        item, customer = rental.item, rental.customer
        reserved = self.reservations.get(item.sku, [])
        served = entry.served_customer_id

        # Check everything first; change nothing until all checks pass.
        if served is not None and served not in reserved:
            raise UndoNotPossibleError(
                f"Cannot undo the return of {rental.rental_id}: "
                f"{self.customers[served].name} has already rented the unit.")
        free = item.available_units - len(reserved) + (1 if served else 0)
        if free < 1:
            raise UndoNotPossibleError(
                f"Cannot undo the return of {rental.rental_id}: "
                f"the unit has been rented again.")
        held = self.held_skus[customer.customer_id]
        if item.sku in held or len(held) >= customer.max_items():
            raise UndoNotPossibleError(
                f"Cannot undo the return of {rental.rental_id}: "
                f"{customer.name} would break R3 or R8.")

        if served is not None:       # back to the FRONT of the queue, not the end
            self.storage.rentals.set_waiting_status(item.sku, served, "waiting")
            reserved.remove(served)
            self.waiting_lists.setdefault(item.sku, deque()).appendleft(served)
        if entry.fine is not None:
            self.storage.rentals.delete_fine(rental.rental_id)
            self.fines.remove(entry.fine)
            self.fines_by_rental[rental.rental_id].remove(entry.fine)
        rental.return_date = None
        self.storage.rentals.update(rental)
        self.open_rentals[rental.rental_id] = rental
        item.check_out_unit()
        held.add(item.sku)
        return rental

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
