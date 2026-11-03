"""Exception hierarchy for GearShare Mini.

Every error has a ``code``:
- rule violations use the rule number, e.g. ``R3``
- all other errors use their class name, e.g. ``CustomerNotFoundError``

The console prints ``ERROR [<code>]: <message>`` and the Phase 4 API returns
``{"error": <code>, "message": <message>}``, so both share one source of truth.
"""


class GearShareError(Exception):
    """Parent of every GearShare error."""

    rule = None  # subclasses that enforce a Rulebook rule set this

    def __init__(self, message, rule=None):
        super().__init__(message)
        self.message = message
        if rule is not None:
            self.rule = rule

    @property
    def code(self):
        return self.rule or type(self).__name__

    def __repr__(self):
        return f"{type(self).__name__}({self.message!r}, code={self.code!r})"


# --- Input / lookup errors (reported by class name) -------------------------

class InvalidSKUError(GearShareError):
    """R9: a SKU must be exactly 10 digits."""


class ItemNotFoundError(GearShareError):
    """No item has this SKU."""


class CustomerNotFoundError(GearShareError):
    """No customer has this ID."""


class RentalNotFoundError(GearShareError):
    """No rental has this ID (used by return / extend)."""


# --- Rule violations (reported by rule number) ------------------------------

class ItemNotRentableError(GearShareError):
    rule = "R1"


class UnpaidFinesError(GearShareError):
    rule = "R4"


class RentalLimitExceededError(GearShareError):
    rule = "R3"


class DuplicateRentalError(GearShareError):
    rule = "R8"


class ItemNotAvailableError(GearShareError):
    rule = "R7"


class WaitingListError(GearShareError):
    """R7: joining is pointless (a unit is free) or the customer is already in the list."""

    rule = "R7"


class ExtensionNotAllowedError(GearShareError):
    """Raised for R2 (accessory) or R6 (limit reached / someone waiting)."""

    rule = "R6"
