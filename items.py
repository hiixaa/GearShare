"""Gear items: an abstract GearItem and its three concrete types.

Each type answers the same questions (R1, R2) in its own way, so the
service never has to ask "what type are you?".
"""

import re
from abc import ABC, abstractmethod

from errors import InvalidSKUError

SKU_PATTERN = re.compile(r"[0-9]{10}")
ACCESSORY_RENTAL_DAYS = 2  # R2


def validate_sku(sku):
    """Return the SKU as a clean string, or raise InvalidSKUError (R9)."""
    sku = str(sku).strip()
    if not SKU_PATTERN.fullmatch(sku):
        raise InvalidSKUError("SKU must be exactly 10 digits.")
    return sku


class GearItem(ABC):
    """Anything in the shop. Cannot be created directly."""

    def __init__(self, sku, name, tags, category, parent_category,
                 weight_g, price, total_units):
        # Instance attributes: every item has its own SKU, name, stock, ...
        self.sku = sku
        self.name = name
        self.tags = list(tags)
        self.category = category
        self.parent_category = parent_category or None
        self.weight_g = weight_g
        self.price = price
        self.total_units = total_units
        self.available_units = total_units

    # --- validated properties ------------------------------------------------

    @property
    def sku(self):
        return self._sku

    @sku.setter
    def sku(self, value):
        self._sku = validate_sku(value)

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
    def weight_g(self):
        return self._weight_g

    @weight_g.setter
    def weight_g(self, value):
        value = int(value)
        if value < 0:
            raise ValueError("Weight cannot be negative.")
        self._weight_g = value

    @property
    def price(self):
        return self._price

    @price.setter
    def price(self, value):
        value = int(value)
        if value < 0:
            raise ValueError("Price cannot be negative.")
        self._price = value

    @property
    def total_units(self):
        return self._total_units

    @total_units.setter
    def total_units(self, value):
        value = int(value)
        if value < 0:
            raise ValueError("Units cannot be negative.")
        self._total_units = value

    @property
    def available_units(self):
        return self._available_units

    @available_units.setter
    def available_units(self, value):
        value = int(value)
        if not 0 <= value <= self.total_units:
            raise ValueError(
                f"Available units must be between 0 and {self.total_units}.")
        self._available_units = value

    @property
    def top_category(self):
        """Top-level category: Cameras and Lenses both count as Photography."""
        return self.parent_category or self.category

    # --- stock -----------------------------------------------------------------

    def is_available(self):
        return self.available_units > 0

    def check_out_unit(self):
        self.available_units -= 1

    def check_in_unit(self):
        self.available_units += 1

    def availability_text(self):
        return f"{self.available_units} of {self.total_units}"

    # --- questions every subclass must answer ----------------------------------

    @abstractmethod
    def type_name(self):
        """Label shown in the catalogue: Equipment, Accessory or Display."""

    @abstractmethod
    def is_rentable(self):
        """R1: can this item ever be rented?"""

    @abstractmethod
    def rental_days(self, customer):
        """How many days a rental of this item lasts for this customer."""

    @abstractmethod
    def can_extend(self):
        """R2: can a rental of this item be extended?"""

    # --- display ---------------------------------------------------------------

    def __str__(self):
        return f"{self.sku} {self.name} ({self.type_name()})"

    def __repr__(self):
        return (f"{type(self).__name__}(sku={self.sku!r}, name={self.name!r}, "
                f"available={self.available_units}/{self.total_units})")


class Equipment(GearItem):
    """Cameras, lenses, drones, ...: rental period comes from the tier."""

    def type_name(self):
        return "Equipment"

    def is_rentable(self):
        return True

    def rental_days(self, customer):
        return customer.rental_period()

    def can_extend(self):
        return True


class Accessory(GearItem):
    """Memory cards, batteries: always 2 days, never extended (R2)."""

    def type_name(self):
        return "Accessory"

    def is_rentable(self):
        return True

    def rental_days(self, customer):
        return ACCESSORY_RENTAL_DAYS

    def can_extend(self):
        return False


class DisplayItem(GearItem):
    """Showcase pieces: can be viewed, never rented (R1)."""

    def type_name(self):
        return "Display"

    def is_rentable(self):
        return False

    def rental_days(self, customer):
        return 0

    def can_extend(self):
        return False

    def availability_text(self):
        return "not rentable"


# Maps the item_type column of gear.csv to a class. A lookup, not an if-chain.
ITEM_TYPES = {
    "Equipment": Equipment,
    "Accessory": Accessory,
    "Display": DisplayItem,
}
