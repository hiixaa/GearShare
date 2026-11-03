"""Task 2.2 tests: searches (with the spec's edge cases) and sorts."""

import random

import pytest

from dsa.search import binary_search, linear_search
from dsa.sorting import (bubble_sort, catalogue_sort, format_catalogue,
                         insertion_sort, selection_sort)

SKUS = [f"100000000{i}" for i in range(1, 8)]
NAMES = ["Sony 50mm Lens", "Canon EOS 200D", "DJI Mini Drone"]


# --- linear search ------------------------------------------------------------

@pytest.mark.parametrize("seq, target, expected", [
    ([], "x", -1),                                   # empty list
    (["only"], "only", 0),                           # one element, found
    (["only"], "x", -1),                             # one element, missing
    (NAMES, "Sony 50mm Lens", 0),                    # first element
    (NAMES, "DJI Mini Drone", 2),                    # last element
    (NAMES, "Leica", -1),                            # not found
])
def test_linear_search_edge_cases(seq, target, expected):
    assert linear_search(seq, target) == expected


def test_linear_search_with_key(shop):
    items = shop.list_items()
    assert linear_search(items, "Manfrotto Tripod", key=lambda i: i.name) == 3


# --- binary search --------------------------------------------------------------

@pytest.mark.parametrize("seq, target, expected", [
    (SKUS, "1000000006", (5, 2)),                    # spec sample
    (SKUS, "1000000008", (-1, 3)),                   # spec sample: not found
    ([], "1000000001", (-1, 0)),                     # spec sample: empty list
    (["1000000001"], "1000000001", (0, 1)),          # one element
    (SKUS, "1000000001", (0, 3)),                    # first element
    (SKUS, "1000000007", (6, 3)),                    # last element
])
def test_binary_search_edge_cases(seq, target, expected):
    assert binary_search(seq, target) == expected


def test_binary_search_agrees_with_linear_search():
    data = sorted(random.Random(1).sample(range(10_000), 500))
    for target in data[::7] + [-1, 10_001]:
        assert binary_search(data, target)[0] == linear_search(data, target)


# --- hand sorts ---------------------------------------------------------------------

HAND_SORTS = [bubble_sort, insertion_sort, selection_sort]


@pytest.mark.parametrize("sort", HAND_SORTS)
@pytest.mark.parametrize("values", [[], [1], [6, 3, 5, 2], [1, 2, 3], [3, 2, 1],
                                    [2, 2, 1], NAMES])
def test_hand_sorts_match_sorted(sort, values):
    original = list(values)
    assert sort(values) == sorted(values)
    assert values == original            # the caller's list is not changed


def test_hand_sorts_print_passes_like_the_sample(capsys):
    for sort in HAND_SORTS:
        sort([6, 3, 5, 2], show=True)
    assert capsys.readouterr().out.splitlines() == [
        "bubble_sort([6, 3, 5, 2])",
        "  after pass 1: [3, 5, 2, 6]",
        "  after pass 2: [3, 2, 5, 6]",
        "  after pass 3: [2, 3, 5, 6]",
        "insertion_sort([6, 3, 5, 2])",
        "  after inserting index 1: [3, 6, 5, 2]",
        "  after inserting index 2: [3, 5, 6, 2]",
        "  after inserting index 3: [2, 3, 5, 6]",
        "selection_sort([6, 3, 5, 2])",
        "  after pass 1 (min=2): [2, 3, 5, 6]",
        "  after pass 2 (min=3): [2, 3, 5, 6]",
        "  after pass 3 (min=5): [2, 3, 5, 6]",
    ]


def test_bubble_sort_stops_early_when_sorted(capsys):
    bubble_sort([1, 2, 3, 4], show=True)
    assert capsys.readouterr().out.count("after pass") == 1


# --- catalogue sort ---------------------------------------------------------------

def test_catalogue_sort_matches_the_sample(shop):
    assert format_catalogue(catalogue_sort(shop.list_items())) == [
        "Accessories  SD Card 128GB              2",
        "Audio        Rode Wireless Mic        120",
        "Drones       DJI Mini Drone           249",
        "Photography  Canon EOS 200D           450",
        "Photography  Sony 50mm Lens           280",
        "Showcase     Vintage Leica (Showcase) 600",
        "Tripods      Manfrotto Tripod        1200",
    ]
