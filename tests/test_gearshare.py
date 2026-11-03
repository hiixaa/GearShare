"""Tests for the GearShare service: every rule, every exception, the reports."""

import inspect

import pytest

from errors import (
    CustomerNotFoundError,
    DuplicateRentalError,
    ExtensionNotAllowedError,
    GearShareError,
    InvalidSKUError,
    ItemNotAvailableError,
    ItemNotFoundError,
    ItemNotRentableError,
    RentalLimitExceededError,
    RentalNotFoundError,
    UnpaidFinesError,
    WaitingListError,
)

SONY, DRONE, TRIPOD, LEICA, SD_CARD = (
    "1000000002", "1000000003", "1000000004", "1000000006", "1000000007")


# --- loading ---------------------------------------------------------------------

def test_load_counts_and_rebuilds_availability(shop):
    assert (len(shop.items), len(shop.customers), len(shop.rentals),
            len(shop.fines)) == (7, 5, 10, 4)
    # RN001, RN002, RN003 have no return date, so those units are out.
    assert shop.items["1000000001"].available_units == 1
    assert shop.items[DRONE].available_units == 0
    assert shop.items[TRIPOD].available_units == 1


# --- rent: happy path and each rule in the order of checks -------------------------

def test_rent_success_gets_next_id_and_due_date(shop, today):
    rental = shop.rent("C001", SONY, today)
    assert rental.rental_id == "RN011"
    assert str(rental.due_date) == "2026-11-06"
    assert shop.items[SONY].available_units == 0


def test_customer_not_found(shop, today):
    with pytest.raises(CustomerNotFoundError, match="No customer with ID C009."):
        shop.rent("C009", SONY, today)


def test_invalid_sku(shop, today):
    with pytest.raises(InvalidSKUError, match="SKU must be exactly 10 digits."):
        shop.rent("C001", "123", today)


def test_item_not_found(shop, today):
    with pytest.raises(ItemNotFoundError, match="No item with SKU 1000000999."):
        shop.rent("C001", "1000000999", today)


def test_r1_display_item_cannot_be_rented(shop, today):
    with pytest.raises(ItemNotRentableError) as err:
        shop.rent("C003", LEICA, today)
    assert err.value.code == "R1"
    assert err.value.message == (
        "'Vintage Leica (Showcase)' is a display item and cannot be rented.")


def test_r4_unpaid_fines_above_500_block_renting(shop, today):
    with pytest.raises(UnpaidFinesError) as err:
        shop.rent("C004", TRIPOD, today)
    assert err.value.code == "R4"
    assert err.value.message == "Rohan Das has unpaid fines of ₹600 (limit ₹500)."


def test_r4_fines_of_exactly_500_still_allowed(shop, today):
    shop.return_item("RN001", today)          # Vikram gets a ₹500 fine
    assert shop.unpaid_fines("C002") == 500
    assert shop.rent("C002", TRIPOD, today).rental_id == "RN011"


def test_r3_item_limit(shop, today):
    shop.rent("C001", SONY, today)
    shop.rent("C001", SD_CARD, today)
    with pytest.raises(RentalLimitExceededError) as err:
        shop.rent("C001", TRIPOD, today)
    assert err.value.code == "R3"
    assert err.value.message == "Ananya Nair already has 2 of 2 items on rental."


def test_r8_no_two_units_of_same_item(shop, today):
    shop.rent("C001", SONY, today)
    with pytest.raises(DuplicateRentalError) as err:
        shop.rent("C001", SONY, today)
    assert err.value.code == "R8"
    assert err.value.message == "Ananya Nair already has a unit of 'Sony 50mm Lens'."


def test_r7_no_unit_free(shop, today):
    with pytest.raises(ItemNotAvailableError) as err:
        shop.rent("C003", DRONE, today)
    assert err.value.code == "R7"
    assert err.value.message == "No units of 'DJI Mini Drone' are available."


def test_order_of_checks_r1_reported_before_r4(shop, today):
    # Rohan breaks R4 too, but R1 comes first in the order of checks.
    with pytest.raises(ItemNotRentableError):
        shop.rent("C004", LEICA, today)


def test_failed_rent_changes_nothing(shop, today):
    with pytest.raises(GearShareError):
        shop.rent("C004", TRIPOD, today)
    assert len(shop.rentals) == 10
    assert shop.audit_log == []


# --- return -------------------------------------------------------------------------

def test_return_late_creates_unpaid_fine(shop, today):
    receipt = shop.return_item("RN001", today)
    assert (receipt.days_late, receipt.fee) == (5, 500)
    assert receipt.next_customer is None
    assert shop.items[DRONE].available_units == 1
    assert shop.fines[-1].amount == 500 and not shop.fines[-1].paid


def test_return_on_time_has_no_fee(shop, today):
    receipt = shop.return_item("RN003", today)
    assert (receipt.days_late, receipt.fee) == (0, 0)
    assert len(shop.fines) == 4


def test_rental_not_found(shop, today):
    with pytest.raises(RentalNotFoundError, match="No open rental with ID RN004."):
        shop.return_item("RN004", today)    # already returned


# --- waiting list (R7) ---------------------------------------------------------------

def test_r7_first_in_waiting_list_is_served_first(shop, today):
    assert shop.join_waiting_list("C003", DRONE) == 1
    assert shop.join_waiting_list("C005", DRONE) == 2
    receipt = shop.return_item("RN001", today)
    assert receipt.next_customer.name == "Meera Joshi"
    # Pooja (2nd) cannot take the unit that is held for Meera (1st).
    with pytest.raises(ItemNotAvailableError):
        shop.rent("C005", DRONE, today)
    assert shop.rent("C003", DRONE, today).customer.name == "Meera Joshi"


def test_waiting_list_errors(shop):
    shop.join_waiting_list("C003", DRONE)
    with pytest.raises(WaitingListError, match="already on the waiting list"):
        shop.join_waiting_list("C003", DRONE)
    with pytest.raises(WaitingListError, match="has a unit available"):
        shop.join_waiting_list("C001", SONY)


# --- extend (R2, R6) ---------------------------------------------------------------

def test_r6_extend_twice_then_refused(shop, today):
    first = shop.extend("RN003", today)
    assert (first.extensions, str(first.due_date)) == (1, "2026-11-13")
    second = shop.extend("RN003", today)
    assert (second.extensions, str(second.due_date)) == (2, "2026-11-20")
    with pytest.raises(ExtensionNotAllowedError) as err:
        shop.extend("RN003", today)
    assert err.value.code == "R6"
    assert err.value.message == "'Manfrotto Tripod' has already been extended 2 times."


def test_r2_accessories_cannot_be_extended(shop, today):
    rental = shop.rent("C001", SD_CARD, today)
    with pytest.raises(ExtensionNotAllowedError) as err:
        shop.extend(rental.rental_id, today)
    assert err.value.code == "R2"
    assert err.value.message == "Accessories cannot be extended."


def test_r6_no_extension_when_someone_is_waiting(shop, today):
    shop.rent("C001", TRIPOD, today)            # last free tripod
    shop.join_waiting_list("C005", TRIPOD)
    with pytest.raises(ExtensionNotAllowedError) as err:
        shop.extend("RN003", today)
    assert err.value.message == (
        "'Manfrotto Tripod' cannot be extended because another customer is waiting.")


# --- reports, generator, decorator --------------------------------------------------

def test_overdue_report_most_late_first(shop, today):
    rows = [(r.rental_id, days, fine) for r, days, fine in shop.overdue_report(today)]
    assert rows == [("RN001", 5, 500), ("RN002", 3, 150)]


def test_iter_overdue_is_a_generator(shop, today):
    gen = shop.iter_overdue(today)
    assert inspect.isgenerator(gen)
    assert next(gen).rental_id == "RN001"


def test_items_by_category_and_unpaid_fines(shop):
    by_category = shop.items_by_category()
    assert list(by_category)[0] == "Accessories"
    assert [i.name for i in by_category["Cameras"]] == ["Canon EOS 200D"]
    assert [(c.name, amount) for c, amount in shop.customers_with_unpaid_fines()] == [
        ("Rohan Das", 600)]


def test_audit_logs_only_successful_actions(shop, today):
    shop.rent("C001", SONY, today)
    with pytest.raises(DuplicateRentalError):
        shop.rent("C001", SONY, today)
    shop.extend("RN003", today)
    shop.return_item("RN011", today)
    assert [(e["action"], e["customer"], e["item"]) for e in shop.audit_log] == [
        ("rent", "C001", SONY),
        ("extend", "C003", TRIPOD),
        ("return_item", "C001", SONY),
    ]


def test_search_is_case_insensitive_on_name_or_tag(shop):
    assert [i.name for i in shop.search("VIDEO")] == ["DJI Mini Drone"]
    assert [i.name for i in shop.search("drone")] == ["DJI Mini Drone"]
    assert shop.search("zzz") == []
