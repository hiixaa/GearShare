"""Task 2.3: hashing (sets and dicts).

    python -m dsa.hashing     # prints the spec's grouping / frequency / two-sum samples

Every function here relies on one fact: looking up a key in a set or dict
takes O(1) on average, because the key's hash says where it is stored.
"""

import csv
import re
from pathlib import Path

from items import item_from_row

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


# --- duplicates ----------------------------------------------------------------

def import_gear(path, shop):
    """Read a gear CSV and add every new item to the shop.

    Repeated SKUs are detected with a set (O(1) per check, so the whole file
    is O(n)) and skipped. Returns (rows read, added, [(line, sku, first name)]).
    """
    seen = set()            # SKUs already in the shop or earlier in this file
    seen.update(shop.items)
    duplicates = []
    rows = added = 0
    with open(path, newline="", encoding="utf-8") as f:
        for line_no, row in enumerate(csv.DictReader(f), start=2):  # line 1 = header
            rows += 1
            sku = row["sku"].strip()
            if sku in seen:
                duplicates.append((line_no, sku, shop.items[sku].name))
                continue
            seen.add(sku)
            shop.add_item(item_from_row(row))
            added += 1
    return rows, added, duplicates


# --- grouping ------------------------------------------------------------------

def group_by_tag(items):
    """{tag: [item names]}: one pass over the items, O(total tags)."""
    groups = {}
    for item in items:
        for tag in item.tags:
            groups.setdefault(tag, []).append(item.name)
    return groups


# --- frequency counting --------------------------------------------------------------

def most_rented(rentals, k):
    """The k most-rented items as [(name, count)], most first, ties A-Z."""
    counts = {}
    names = {}
    for rental in rentals:
        sku = rental.item.sku
        counts[sku] = counts.get(sku, 0) + 1
        names[sku] = rental.item.name
    ranked = sorted(counts, key=lambda sku: (-counts[sku], names[sku]))
    return [(names[sku], counts[sku]) for sku in ranked[:k]]


# --- packing challenge (two-sum) ---------------------------------------------------------

def packing_challenge(items, target):
    """Two different rentable items whose weights add up to target, or None.

    One pass: for each item, the weight we still need is target - weight.
    If an earlier item had exactly that weight, we have a pair.
    The dict maps weight -> first item seen with it, so the check is O(1)
    and the whole search is O(n) (instead of O(n^2) trying every pair).
    """
    seen = {}
    for item in items:
        if not item.is_rentable():           # display items are excluded (R1)
            continue
        needed = target - item.weight_g
        if needed in seen:
            return seen[needed], item
        seen.setdefault(item.weight_g, item)
    return None


# --- stretch: word-to-SKU index ------------------------------------------------------------

WORD = re.compile(r"[a-z0-9]+")


def words_of(text):
    return WORD.findall(text.lower())


class WordIndex:
    """Inverted index: word -> set of SKUs whose name or tags contain that word.

    Building it is O(total words), done once. A search for q words then costs
    O(q + matches) instead of scanning every item: each word is one dict lookup,
    and the sets are intersected so every word must match.
    """

    def __init__(self, items):
        self.index = {}
        for item in items:
            for word in words_of(item.name) + [w for t in item.tags for w in words_of(t)]:
                self.index.setdefault(word, set()).add(item.sku)

    def search(self, query):
        """SKUs (sorted) of items matching ALL words of the query."""
        words = words_of(query)
        if not words:
            return []
        sets = [self.index.get(word, set()) for word in words]
        sets.sort(key=len)                   # intersect from the smallest set
        return sorted(sets[0].intersection(*sets[1:]))


# --- demo --------------------------------------------------------------------------------

def _demo():
    from gearshare import GearShare

    shop = GearShare()
    shop.load_data(DATA_DIR)
    items = shop.list_items()

    print("group_by_tag():")
    for tag, names in sorted(group_by_tag(items).items()):
        print(f"{tag}: {', '.join(names)}")

    print("\nmost_rented(3):")
    top = most_rented(shop.rentals, 3)
    width = max(len(name) for name, _ in top) + 3
    for rank, (name, count) in enumerate(top, start=1):
        print(f"{rank}. {name:<{width}}{count}")

    print()
    targets = [730, 1320, 1000]
    call_width = max(len(f"packing_challenge({t})") for t in targets) + 1
    for target in targets:
        pair = packing_challenge(items, target)
        result = ("No pair found." if pair is None else
                  f"{pair[0].name} ({pair[0].weight_g}) + "
                  f"{pair[1].name} ({pair[1].weight_g}) = {target}")
        print(f"{f'packing_challenge({target})':<{call_width}}-> {result}")


if __name__ == "__main__":
    _demo()
