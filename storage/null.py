"""NullStorage: the same interface as Storage, but it stores nothing.

Used when GearShare runs purely in memory: the Phase 2 benchmarks and demos,
which load generated CSV files. GearShare calls the same methods either way,
with no `if storage is None` checks scattered through the rules.
"""

from contextlib import nullcontext


class _NullRepository:
    """Any method call does nothing and returns an empty list."""

    def __getattr__(self, name):
        return lambda *args, **kwargs: []


class NullStorage:
    def __init__(self):
        self.items = self.customers = self.rentals = _NullRepository()

    def transaction(self):
        return nullcontext()

    def close(self):
        pass
