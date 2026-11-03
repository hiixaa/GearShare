"""Tests for the model classes: validation, polymorphism, date maths."""

from datetime import date, timedelta

import pytest

from customers import BasicCustomer, Customer, PlusCustomer, ProCustomer
from errors import InvalidSKUError
from items import Accessory, DisplayItem, Equipment, GearItem
from rentals import Rental


def make_equipment(price=45000, sku="1000000001"):
    return Equipment(sku, "Test Camera", ["photo"], "Cameras", "Photography",
                     450, price, 2)


def make_accessory(price=600):
    return Accessory("1000000007", "SD Card", ["storage"], "Accessories", "",
                     2, price, 3)


TIERS = {"Basic": BasicCustomer, "Plus": PlusCustomer, "Pro": ProCustomer}


def make_customer(tier):
    return TIERS[tier]("C100", "Test Person", "test@example.com")


# --- worked example 1: due dates (R2 + tier periods) ---------------------------

@pytest.mark.parametrize("tier, item_factory, expected_due", [
    ("Basic", make_equipment, date(2026, 11, 6)),
    ("Plus", make_equipment, date(2026, 11, 8)),
    ("Pro", make_equipment, date(2026, 11, 10)),
    ("Pro", make_accessory, date(2026, 11, 5)),   # R2: 2 days whatever the tier
])
def test_due_dates_worked_example(tier, item_factory, expected_due):
    issue = date(2026, 11, 3)
    days = item_factory().rental_days(make_customer(tier))
    assert issue + timedelta(days=days) == expected_due


# --- worked example 2: late fees (R5, R10) -------------------------------------

@pytest.mark.parametrize("tier, item_factory, price, due, returned, days_late, fee", [
    ("Basic", make_equipment, 45000, date(2026, 10, 31), date(2026, 10, 31), 0, 0),
    ("Basic", make_equipment, 45000, date(2026, 10, 31), date(2026, 11, 1), 1, 50),
    ("Plus", make_equipment, 38000, date(2026, 10, 29), date(2026, 11, 3), 5, 500),
    ("Pro", make_equipment, 22000, date(2026, 9, 30), date(2026, 10, 30), 30, 4500),
    ("Basic", make_accessory, 600, date(2026, 8, 3), date(2026, 8, 23), 20, 600),
])
def test_late_fees_worked_example(tier, item_factory, price, due, returned,
                                  days_late, fee):
    rental = Rental("RN900", make_customer(tier), item_factory(price=price),
                    issue_date=due - timedelta(days=3), due_date=due)
    assert rental.days_late(returned) == days_late
    assert rental.late_fee(returned) == fee


def test_r10_return_on_due_date_is_not_late():
    rental = Rental("RN900", make_customer("Basic"), make_equipment(),
                    date(2026, 11, 1), date(2026, 11, 4))
    assert rental.days_late(date(2026, 11, 4)) == 0
    assert rental.days_late(date(2026, 11, 5)) == 1


def test_r5_fee_never_more_than_replacement_price():
    rental = Rental("RN900", make_customer("Pro"), make_accessory(price=600),
                    date(2026, 1, 1), date(2026, 1, 3))
    assert rental.late_fee(date(2026, 12, 31)) == 600


# --- polymorphism ----------------------------------------------------------------

@pytest.mark.parametrize("tier, max_items, period, fee", [
    ("Basic", 2, 3, 50),
    ("Plus", 4, 5, 100),
    ("Pro", 8, 7, 150),
])
def test_tier_answers(tier, max_items, period, fee):
    customer = make_customer(tier)
    assert (customer.max_items(), customer.rental_period(),
            customer.late_fee_per_day()) == (max_items, period, fee)


def test_r1_r2_item_types_answer_differently():
    display = DisplayItem("1000000006", "Leica", ["display"], "Showcase", "",
                          600, 150000, 1)
    assert make_equipment().is_rentable() and make_equipment().can_extend()
    assert make_accessory().is_rentable() and not make_accessory().can_extend()
    assert not display.is_rentable()
    assert display.availability_text() == "not rentable"


def test_abstract_classes_cannot_be_created():
    with pytest.raises(TypeError):
        GearItem("1000000001", "X", [], "C", "", 1, 1, 1)
    with pytest.raises(TypeError):
        Customer("C100", "X", "x@example.com")


# --- validation: invalid objects can never exist -------------------------------

@pytest.mark.parametrize("bad_sku", ["123", "12345678901", "10000000a1", "", "１０００００００01"])
def test_r9_sku_must_be_exactly_10_digits(bad_sku):
    with pytest.raises(InvalidSKUError, match="SKU must be exactly 10 digits."):
        make_equipment(sku=bad_sku)


def test_validation_rejects_bad_values():
    with pytest.raises(ValueError, match="blank"):
        Equipment("1000000001", "   ", [], "C", "", 1, 1, 1)
    with pytest.raises(ValueError, match="negative"):
        Equipment("1000000001", "X", [], "C", "", 1, 1, -1)
    with pytest.raises(ValueError, match="@"):
        BasicCustomer("C100", "X", "no-at-sign")
    with pytest.raises(ValueError, match="before issue date"):
        Rental("RN900", make_customer("Basic"), make_equipment(),
               date(2026, 11, 5), date(2026, 11, 4))


def test_str_and_repr():
    item, customer = make_equipment(), make_customer("Plus")
    assert str(item) == "1000000001 Test Camera (Equipment)"
    assert repr(customer).startswith("PlusCustomer(customer_id='C100'")
