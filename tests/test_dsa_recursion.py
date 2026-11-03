"""Task 2.5 tests: recursive warm-ups and the category tree."""

import pytest

from dsa.categories import (CategoryNode, build_tree, count_items, factorial,
                            fibonacci, fibonacci_iterative, path_to,
                            path_to_iterative, sum_of_digits, total_items,
                            total_items_iterative, tree_lines,
                            tree_lines_iterative)


@pytest.fixture
def root(shop):
    return build_tree(shop.list_items())


# --- warm-ups --------------------------------------------------------------------

@pytest.mark.parametrize("n, expected", [(0, 1), (1, 1), (6, 720), (10, 3628800)])
def test_factorial(n, expected):
    assert factorial(n) == expected


@pytest.mark.parametrize("n, expected", [(0, 0), (1, 1), (2, 1), (8, 21), (20, 6765)])
def test_fibonacci_recursive_and_iterative_agree(n, expected):
    assert fibonacci(n) == fibonacci_iterative(n) == expected


@pytest.mark.parametrize("n, expected", [(0, 0), (7, 7), (5078, 20), (99999, 45), (-5078, 20)])
def test_sum_of_digits(n, expected):
    assert sum_of_digits(n) == expected


def test_negative_input_rejected():
    with pytest.raises(ValueError):
        factorial(-1)
    with pytest.raises(ValueError):
        fibonacci(-1)


# --- category tree ---------------------------------------------------------------------

EXPECTED_TREE = [
    "Gear Hub (7)",
    "  Accessories (1)",
    "  Audio (1)",
    "  Drones (1)",
    "  Photography (2)",
    "    Cameras (1)",
    "    Lenses (1)",
    "  Showcase (1)",
    "  Tripods (1)",
]


def test_print_tree_matches_the_sample(root):
    assert tree_lines(root) == EXPECTED_TREE


def test_iterative_tree_gives_the_same_lines(root):
    assert tree_lines_iterative(root) == EXPECTED_TREE


@pytest.mark.parametrize("name, expected", [
    ("Photography", 2), ("Gear Hub", 7), ("Lenses", 1), ("Lighting", 0)])
def test_count_items(root, name, expected):
    assert count_items(root, name) == expected


@pytest.mark.parametrize("name, expected", [
    ("Lenses", ["Gear Hub", "Photography", "Lenses"]),
    ("Gear Hub", ["Gear Hub"]),
    ("Tripods", ["Gear Hub", "Tripods"]),
    ("Lighting", None),
])
def test_path_to_recursive_and_iterative(root, name, expected):
    assert path_to(root, name) == path_to_iterative(root, name) == expected


def test_iterative_version_survives_a_very_deep_tree():
    """Depth 10,000: recursion exceeds Python's default limit, the explicit stack doesn't."""
    root = node = CategoryNode("L0")
    for i in range(1, 10_000):
        node.children.append(CategoryNode(f"L{i}"))
        node = node.children[0]
    node.items.append("item")
    with pytest.raises(RecursionError):
        total_items(root)
    assert total_items_iterative(root) == 1
    assert len(path_to_iterative(root, "L9999")) == 10_000
