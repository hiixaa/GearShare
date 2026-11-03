"""Task 2.2: three sorts by hand, plus the catalogue sort.

    python -m dsa.sorting     # prints the spec's samples

Each hand sort works on a COPY (the caller's list is never changed), returns
the sorted copy, and with show=True prints the list after every pass.
"""

from pathlib import Path


def _identity(value):
    return value


def bubble_sort(values, key=None, show=False):
    """Swap neighbours that are out of order; each pass bubbles the largest
    remaining value to the end. O(n^2) time, O(1) extra space, stable.
    Stops early when a pass makes no swaps (already sorted: O(n))."""
    key = key or _identity
    data = list(values)
    if show:
        print(f"bubble_sort({values})")
    for end in range(len(data) - 1, 0, -1):     # data[end+1:] is already final
        swapped = False
        for i in range(end):
            if key(data[i]) > key(data[i + 1]):
                data[i], data[i + 1] = data[i + 1], data[i]
                swapped = True
        if show:
            print(f"  after pass {len(data) - end}: {data}")
        if not swapped:
            break
    return data


def insertion_sort(values, key=None, show=False):
    """Take each element and slide it left into place among the already
    sorted front part. O(n^2) time (O(n) if nearly sorted), O(1) extra, stable."""
    key = key or _identity
    data = list(values)
    if show:
        print(f"insertion_sort({values})")
    for i in range(1, len(data)):
        current = data[i]
        j = i - 1
        while j >= 0 and key(data[j]) > key(current):
            data[j + 1] = data[j]   # shift the bigger element one step right
            j -= 1
        data[j + 1] = current
        if show:
            print(f"  after inserting index {i}: {data}")
    return data


def selection_sort(values, key=None, show=False):
    """Find the minimum of the unsorted part and swap it to the front.
    Always O(n^2) comparisons, but at most n-1 swaps. O(1) extra, NOT stable."""
    key = key or _identity
    data = list(values)
    if show:
        print(f"selection_sort({values})")
    for start in range(len(data) - 1):
        smallest = start
        for i in range(start + 1, len(data)):
            if key(data[i]) < key(data[smallest]):
                smallest = i
        data[start], data[smallest] = data[smallest], data[start]
        if show:
            print(f"  after pass {start + 1} (min={data[start]}): {data}")
    return data


def catalogue_sort(items):
    """Top-level category A-Z, then weight heaviest first, then name A-Z.

    One sorted() call with a tuple key: negating the weight turns "descending"
    into "ascending", so all three parts can sort in the same direction.
    """
    return sorted(items, key=lambda item: (item.top_category, -item.weight_g, item.name))


def format_catalogue(items):
    """Lines like 'Photography  Canon EOS 200D           450'."""
    cat_w = max(len(i.top_category) for i in items)
    name_w = max(len(i.name) for i in items)
    weight_w = max(len(str(i.weight_g)) for i in items)
    return [f"{i.top_category:<{cat_w}}  {i.name:<{name_w}}{i.weight_g:>{weight_w}}"
            for i in items]


def _demo():
    from gearshare import GearShare

    for sort in (bubble_sort, insertion_sort, selection_sort):
        sort([6, 3, 5, 2], show=True)

    shop = GearShare()
    shop.load_data(Path(__file__).resolve().parent.parent / "data")
    print()
    print("\n".join(format_catalogue(catalogue_sort(shop.list_items()))))


if __name__ == "__main__":
    _demo()
