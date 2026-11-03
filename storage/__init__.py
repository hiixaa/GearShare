"""Phase 3: the storage layer. The ONLY place in the engine that talks SQL.

    from storage import Storage
    store = Storage("data/gearshare.db")
    with store.transaction():
        store.rentals.add(rental)

GearShare uses store.items, store.customers and store.rentals (one class per
table group) and never sees sqlite3 or a line of SQL. Every query here uses
? parameters: values are never pasted into SQL text (see Task 3.8).
"""

from storage.database import Database, Storage
from storage.null import NullStorage

__all__ = ["Database", "Storage", "NullStorage"]
