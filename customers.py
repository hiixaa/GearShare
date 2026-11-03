"""Customers: an abstract Customer and one subclass per membership tier.

Each tier answers the same three questions (item limit, rental period,
late fee per day) with its own numbers. There is no `if tier == ...`.
"""

from abc import ABC, abstractmethod


class Customer(ABC):
    """A shop customer. Cannot be created directly: pick a tier."""

    def __init__(self, customer_id, name, email):
        # Instance attributes: each customer has their own id, name, email.
        self.customer_id = customer_id
        self.name = name
        self.email = email

    # --- validated properties --------------------------------------------------

    @property
    def customer_id(self):
        return self._customer_id

    @customer_id.setter
    def customer_id(self, value):
        value = str(value).strip().upper()
        if not value:
            raise ValueError("Customer ID cannot be blank.")
        self._customer_id = value

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        value = str(value).strip()
        if not value:
            raise ValueError("Name cannot be blank.")
        self._name = value

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, value):
        value = str(value).strip()
        if "@" not in value:
            raise ValueError("Email must contain @.")
        self._email = value

    # --- questions every tier must answer --------------------------------------

    @abstractmethod
    def tier_name(self):
        """Basic, Plus or Pro."""

    @abstractmethod
    def max_items(self):
        """R3: how many items this customer may hold at once."""

    @abstractmethod
    def rental_period(self):
        """Days an equipment rental lasts (and each extension adds, R6)."""

    @abstractmethod
    def late_fee_per_day(self):
        """R5: fee in rupees for each day late."""

    # --- display ---------------------------------------------------------------

    def __str__(self):
        return f"{self.name} ({self.tier_name()})"

    def __repr__(self):
        return (f"{type(self).__name__}(customer_id={self.customer_id!r}, "
                f"name={self.name!r}, email={self.email!r})")


class BasicCustomer(Customer):
    def tier_name(self):
        return "Basic"

    def max_items(self):
        return 2

    def rental_period(self):
        return 3

    def late_fee_per_day(self):
        return 50


class PlusCustomer(Customer):
    def tier_name(self):
        return "Plus"

    def max_items(self):
        return 4

    def rental_period(self):
        return 5

    def late_fee_per_day(self):
        return 100


class ProCustomer(Customer):
    def tier_name(self):
        return "Pro"

    def max_items(self):
        return 8

    def rental_period(self):
        return 7

    def late_fee_per_day(self):
        return 150


# Maps the membership_type column of customers.csv to a class.
# A lookup, not an if-chain: adding a tier = one class + one line here.
TIER_CLASSES = {
    "Basic": BasicCustomer,
    "Plus": PlusCustomer,
    "Pro": ProCustomer,
}
