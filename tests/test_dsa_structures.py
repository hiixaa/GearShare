"""Task 2.4 tests: undo stack, waiting-list queue, rental-history linked list."""

from collections import deque

import pytest

from dsa.history import RentalHistory, history_for
from errors import ItemNotAvailableError, UndoNotPossibleError
from main import format_waiting_list

SONY, DRONE, TRIPOD = "1000000002", "1000000003", "1000000004"


# --- undo stack ---------------------------------------------------------------------

def test_undo_rent_removes_the_rental_completely(shop, today):
    shop.rent("C001", SONY, today)
    action, rental = shop.undo()
    assert (action, rental.rental_id) == ("rent", "RN011")
    assert "RN011" not in shop.open_rentals
    assert len(shop.rentals) == 10
    assert shop.items[SONY].available_units == 1
    assert shop.active_count("C001") == 0
    assert shop.rent("C001", SONY, today).rental_id == "RN011"   # ID handed out again


def test_undo_with_empty_stack_returns_none(shop):
    assert shop.undo() is None


def test_undo_return_reopens_rental_and_deletes_fine(shop, today):
    shop.return_item("RN001", today)                 # ₹500 fine
    action, rental = shop.undo()
    assert (action, rental.rental_id) == ("return", "RN001")
    assert rental.is_open() and rental.return_date is None
    assert shop.items[DRONE].available_units == 0
    assert shop.unpaid_fines("C002") == 0
    assert len(shop.fines) == 4


def test_undo_return_puts_served_customer_back_at_the_front(shop, today):
    shop.join_waiting_list("C003", DRONE)
    shop.join_waiting_list("C005", DRONE)
    shop.return_item("RN001", today)                 # Meera moves to a reservation
    shop.undo()
    assert [c.name for c in shop.waiting_list(DRONE)] == ["Meera Joshi", "Pooja Menon"]
    assert shop.reservations[DRONE] == []


def test_undo_steps_back_in_reverse_order(shop, today):
    shop.rent("C001", SONY, today)
    shop.return_item("RN011", today)
    assert shop.undo()[0] == "return"
    assert shop.undo()[0] == "rent"
    assert shop.undo() is None


def test_undo_return_refused_when_unit_rented_again(shop, today):
    shop.return_item("RN003", today)                 # 2nd tripod comes back
    shop.rent("C001", TRIPOD, today)                 # ...and goes straight out
    shop.rent("C005", TRIPOD, today)
    shop.undo_stack.pop()                            # skip the two rents
    shop.undo_stack.pop()
    with pytest.raises(UndoNotPossibleError, match="rented again"):
        shop.undo()


def test_undo_stack_keeps_only_the_latest_actions(shop, today):
    for _ in range(25):
        rental = shop.rent("C003", SONY, today)
        shop.return_item(rental.rental_id, today)
    assert len(shop.undo_stack) == 20


def test_undo_is_logged(shop, today):
    shop.rent("C001", SONY, today)
    shop.undo()
    assert [e["action"] for e in shop.audit_log] == ["rent", "undo_rent"]


# --- waiting list (queue) ---------------------------------------------------------------

def test_waiting_list_is_a_deque_served_first_come_first_served(shop, today):
    shop.join_waiting_list("C003", DRONE)
    shop.join_waiting_list("C005", DRONE)
    assert isinstance(shop.waiting_lists[DRONE], deque)
    assert format_waiting_list(shop, DRONE) == (
        "Waiting list for 'DJI Mini Drone': Meera Joshi, Pooja Menon")

    receipt = shop.return_item("RN001", today)
    assert receipt.next_customer.name == "Meera Joshi"
    assert format_waiting_list(shop, DRONE) == "Waiting list for 'DJI Mini Drone': Pooja Menon"
    with pytest.raises(ItemNotAvailableError):        # Pooja can't jump ahead of Meera
        shop.rent("C005", DRONE, today)


# --- rental history (linked list) ----------------------------------------------------------

@pytest.mark.parametrize("customer_id, expected", [
    ("C002", "RN001 -> RN007 -> RN008 -> None"),
    ("C003", "RN003 -> RN006 -> None"),
    ("C005", "None"),                                 # never rented
])
def test_history_newest_first(shop, customer_id, expected):
    assert str(history_for(shop, customer_id)) == expected


def make_history(*ids):
    history = RentalHistory()
    for rental_id in reversed(ids):
        history.insert_at_head(rental_id)
    return history


def test_history_delete():
    history = make_history("RN3", "RN2", "RN1")
    assert history.delete("RN2") and list(history) == ["RN3", "RN1"]
    assert history.delete("RN3") and list(history) == ["RN1"]      # the head
    assert not history.delete("RN9")
    assert history.delete("RN1") and str(history) == "None" and len(history) == 0


def test_history_reverse():
    history = make_history("RN3", "RN2", "RN1")
    history.reverse()
    assert list(history) == ["RN1", "RN2", "RN3"]
    empty = RentalHistory()
    empty.reverse()
    assert str(empty) == "None"


@pytest.mark.parametrize("ids, expected", [
    (("RN3", "RN2", "RN1"), "RN2"),
    (("RN2", "RN1"), "RN2"),
    (("RN1",), None),
    ((), None),
])
def test_history_second_from_end(ids, expected):
    assert make_history(*ids).second_from_end() == expected
