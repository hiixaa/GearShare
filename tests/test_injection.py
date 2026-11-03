"""Task 3.8: the injection experiment, as evidence that stays true."""

import sqlite3

import pytest

from sql.injection_demo import search_safe, search_unsafe

ATTACK = "' OR '1'='1"


@pytest.fixture
def conn(db_path):
    c = sqlite3.connect(db_path)
    yield c
    c.close()


def test_unsafe_search_leaks_every_item(conn):
    assert len(search_unsafe(conn, "Drone")[1]) == 1
    sql, found = search_unsafe(conn, ATTACK)
    assert len(found) == 7                               # every item leaked
    assert "OR '1'='1" in sql                            # the input became SQL code


def test_safe_search_treats_the_attack_as_plain_text(conn):
    sql, found = search_safe(conn, ATTACK)
    assert found == []
    assert ATTACK not in sql                             # the input never enters the SQL
    assert search_safe(conn, "Drone")[1] == [("DJI Mini Drone",)]


def test_the_engine_search_is_not_fooled(shop):
    """GearShare.search() never builds SQL at all, and returns nothing for the attack."""
    assert shop.search(ATTACK) == []
