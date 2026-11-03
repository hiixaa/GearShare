"""Task 2.2: linear search and binary search.

    python -m dsa.search      # prints the spec's binary-search sample
"""


def linear_search(seq, target, key=None):
    """Index of the first element whose key equals target, or -1.

    Works on any list, sorted or not. Time O(n), space O(1).
    Edge cases: empty list -> -1 (the loop never runs).
    """
    for index, element in enumerate(seq):
        value = key(element) if key else element
        if value == target:
            return index
    return -1


def binary_search(sorted_seq, target):
    """Return (index, comparisons) for target in an ASCENDING list.

    index is -1 when target is missing. One "comparison" = one middle element
    examined. Time O(log n), space O(1).

    Each step looks at the middle of the remaining range [low, high] and throws
    away the half that cannot contain the target.
    """
    low, high = 0, len(sorted_seq) - 1
    comparisons = 0
    while low <= high:          # empty list: high = -1, loop never runs
        mid = (low + high) // 2
        comparisons += 1
        if sorted_seq[mid] == target:
            return mid, comparisons
        if sorted_seq[mid] < target:
            low = mid + 1       # target can only be in the right half
        else:
            high = mid - 1      # target can only be in the left half
    return -1, comparisons


def _demo():
    skus = [f"100000000{i}" for i in range(1, 8)]
    print("skus = ['1000000001', '1000000002', '1000000003', '1000000004',")
    print("        '1000000005', '1000000006', '1000000007']")
    calls = [
        ("binary_search(skus, '1000000006')", skus, "1000000006"),
        ("binary_search(skus, '1000000008')", skus, "1000000008"),
        ("binary_search([], '1000000001')", [], "1000000001"),
    ]
    width = max(len(text) for text, _, _ in calls) + 1
    for text, seq, target in calls:
        index, comparisons = binary_search(seq, target)
        print(f"{text:<{width}}{'-> ' + str(index):<8}({comparisons} comparisons)")


if __name__ == "__main__":
    _demo()
