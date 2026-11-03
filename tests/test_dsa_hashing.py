"""Task 2.3 tests: duplicates, grouping, frequency, two-sum, word index."""

from pathlib import Path

import pytest

from dsa.hashing import (WordIndex, group_by_tag, import_gear, most_rented,
                         packing_challenge)
from gearshare import GearShare
from import_gear import main as import_main

DATA_DIR = Path(__file__).parent.parent / "data"


# --- duplicates ------------------------------------------------------------------

def test_import_skips_duplicate_sku_with_line_number():
    shop = GearShare()
    rows, added, duplicates = import_gear(DATA_DIR / "gear_with_duplicate.csv", shop)
    assert (rows, added) == (8, 7)
    assert duplicates == [(9, "1000000004", "Manfrotto Tripod")]
    assert shop.items["1000000004"].name == "Manfrotto Tripod"   # first one kept


def test_import_gear_script_output(capsys):
    assert import_main(["import_gear.py", "gear_with_duplicate.csv"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "Line 9: duplicate SKU 1000000004 (already used by 'Manfrotto Tripod'), skipped.",
        "Imported 8 rows: 7 added, 1 duplicate skipped.",
    ]


def test_add_item_rejects_duplicate_sku(shop):
    with pytest.raises(ValueError, match="duplicate SKU 1000000004"):
        shop.add_item(shop.items["1000000004"])


# --- grouping and frequency --------------------------------------------------------

def test_group_by_tag(shop):
    groups = group_by_tag(shop.list_items())
    assert len(groups) == 10
    assert groups["photo"] == ["Canon EOS 200D", "Sony 50mm Lens"]
    assert groups["aerial"] == ["DJI Mini Drone"]


def test_most_rented_ties_broken_alphabetically(shop):
    assert most_rented(shop.rentals, 3) == [
        ("Canon EOS 200D", 3), ("DJI Mini Drone", 2), ("Rode Wireless Mic", 2)]


def test_most_rented_empty():
    assert most_rented([], 3) == []


# --- packing challenge (two-sum) ------------------------------------------------------

@pytest.mark.parametrize("target, expected", [
    (730, ("Canon EOS 200D", "Sony 50mm Lens")),
    (1320, ("Manfrotto Tripod", "Rode Wireless Mic")),
    (1000, None),
    (1200, None),        # 600 + 600 would need the display item twice: excluded
    (452, ("Canon EOS 200D", "SD Card 128GB")),   # accessories are rentable
])
def test_packing_challenge(shop, target, expected):
    pair = packing_challenge(shop.list_items(), target)
    assert (pair and (pair[0].name, pair[1].name)) == expected


def test_packing_challenge_excludes_display_items(shop):
    # Leica (600, display) + Canon (450) = 1050 must NOT be found.
    assert packing_challenge(shop.list_items(), 1050) is None


# --- stretch: word index ----------------------------------------------------------------

def test_word_index_multi_word_search(shop):
    index = WordIndex(shop.list_items())
    assert index.search("drone") == ["1000000003"]
    assert index.search("PHOTO") == ["1000000001", "1000000002"]
    assert index.search("photo lens") == ["1000000002"]   # both words must match
    assert index.search("photo drone") == []
    assert index.search("") == []
