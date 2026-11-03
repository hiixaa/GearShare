"""Task 3.7: the engine on the database. Persistence, one transaction per
operation, rollback, and clean layers."""

import re
from pathlib import Path

import pytest

from errors import StorageError
from gearshare import GearShare
from storage import Storage

ROOT = Path(__file__).parent.parent
SONY, DRONE, TRIPOD = "1000000002", "1000000003", "1000000004"


def reopen(db_path):
    """A brand-new GearShare on the same file, like restarting the program."""
    storage = Storage(db_path)
    shop = GearShare(storage)
    shop.load_data()
    return shop, storage


# --- loading -----------------------------------------------------------------------

def test_loads_the_shop_from_the_database(shop):
    assert (len(shop.items), len(shop.customers), len(shop.rentals),
            len(shop.fines)) == (7, 5, 10, 4)
    assert shop.items[DRONE].tags == ["video", "aerial"]       # tag order kept
    assert shop.items["1000000001"].top_category == "Photography"
    assert type(shop.customers["C003"]).__name__ == "ProCustomer"
    assert shop.items[DRONE].available_units == 0             # rebuilt from open rentals


# --- every operation survives a restart -----------------------------------------------

def test_rent_return_extend_persist(shop, db_path, today):
    shop.rent("C001", SONY, today)
    shop.return_item("RN001", today)          # ₹500 fine
    shop.extend("RN003", today)

    again, storage = reopen(db_path)
    assert again.open_rentals["RN011"].customer.name == "Ananya Nair"
    assert "RN001" not in again.open_rentals
    assert again.unpaid_fines("C002") == 500
    assert str(again.open_rentals["RN003"].due_date) == "2026-11-13"
    assert again.open_rentals["RN003"].extensions == 1
    assert [e["action"] for e in again.audit_log] == ["rent", "return_item", "extend"]
    storage.close()


def test_new_rental_ids_continue_after_restart(shop, db_path, today):
    shop.rent("C001", SONY, today)
    again, storage = reopen(db_path)
    assert again.rent("C003", "1000000007", today).rental_id == "RN012"
    storage.close()


def test_waiting_list_and_reservation_persist(shop, db_path, today):
    shop.join_waiting_list("C003", DRONE)
    shop.join_waiting_list("C005", DRONE)
    shop.return_item("RN001", today)          # Meera: waiting -> reserved
    again, storage = reopen(db_path)
    assert again.reservations[DRONE] == ["C003"]
    assert [c.name for c in again.waiting_list(DRONE)] == ["Pooja Menon"]
    storage.close()


def test_undo_persists(shop, db_path, today):
    shop.rent("C001", SONY, today)
    shop.undo()
    shop.return_item("RN001", today)
    shop.undo()
    again, storage = reopen(db_path)
    assert "RN011" not in {r.rental_id for r in again.rentals}
    assert "RN001" in again.open_rentals and again.unpaid_fines("C002") == 0
    assert [e["action"] for e in again.audit_log] == [
        "rent", "undo_rent", "return_item", "undo_return"]
    storage.close()


def test_added_item_persists(shop, db_path):
    item = type(shop.items[SONY])("1000000099", "Godox Light", ["light", "photo"],
                                  "Lighting", "Photography", 900, 7000, 2)
    shop.add_item(item)
    again, storage = reopen(db_path)
    added = again.items["1000000099"]
    assert (added.name, added.tags, added.top_category) == (
        "Godox Light", ["light", "photo"], "Photography")
    storage.close()


# --- one transaction per operation: all or nothing --------------------------------------

def test_failed_audit_rolls_back_the_whole_rent(shop, db_path, today, monkeypatch):
    def broken_audit(entry):
        raise StorageError("Database error: NOT NULL constraint failed: audit_log.customer_id")
    monkeypatch.setattr(shop.storage.rentals, "add_audit", broken_audit)

    with pytest.raises(StorageError):
        shop.rent("C001", SONY, today)

    # The rental row was inserted, then rolled back with the failed audit row ...
    again, storage = reopen(db_path)
    assert "RN011" not in {r.rental_id for r in again.rentals}
    storage.close()
    # ... and memory was reloaded from the database, so it agrees.
    assert "RN011" not in shop.open_rentals
    assert shop.items[SONY].available_units == 1


def test_database_refusal_is_a_clean_error(shop, today):
    # Someone else's program wrote RN011 to the database behind our back.
    shop.storage.db.execute(
        "INSERT INTO rentals (rental_id, customer_id, sku, issue_date, due_date)"
        " VALUES (?, ?, ?, ?, ?)", ("RN011", "C005", "1000000007", "2026-11-03", "2026-11-05"))
    with pytest.raises(StorageError, match="UNIQUE constraint failed"):
        shop.rent("C001", SONY, today)
    # Memory was reloaded: it now knows about the other program's RN011.
    assert shop.open_rentals["RN011"].customer.name == "Pooja Menon"
    assert shop.rent("C001", SONY, today).rental_id == "RN012"


def test_rule_violation_writes_nothing(shop, db_path, today):
    with pytest.raises(Exception):
        shop.rent("C004", TRIPOD, today)      # R4
    again, storage = reopen(db_path)
    assert len(again.rentals) == 10 and again.audit_log == []
    storage.close()


# --- clean layers (the spec's hint) and safe SQL ----------------------------------------

def test_gearshare_contains_no_sql():
    source = (ROOT / "gearshare.py").read_text(encoding="utf-8")
    assert "sqlite3" not in source
    assert "SELECT" not in source


def test_storage_never_formats_sql():
    """Every execute/query call passes SQL as a plain string literal, never an f-string."""
    for path in (ROOT / "storage").glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert not re.search(r"(execute|query)\(\s*f[\"']", source), path.name
        assert ".format(" not in source, path.name
