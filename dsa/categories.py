"""Task 2.5: recursion, from warm-ups to the category tree.

    python -m dsa.categories      # prints the spec's recursion sample

Every recursive function answers two questions BEFORE the code:
  Base case: when can I answer without calling myself?
  Smaller:   how does each call move closer to the base case?
"""

from pathlib import Path

ROOT_NAME = "Gear Hub"


# ============================================================ warm-ups

def factorial(n):
    """n! = n x (n-1) x ... x 1

    Base case: n <= 1 -> 1  (0! = 1! = 1)
    Smaller:   n! = n x (n-1)!   -> n drops by 1 each call; depth n.
    """
    if n < 0:
        raise ValueError("factorial is not defined for negative numbers")
    if n <= 1:
        return 1
    return n * factorial(n - 1)


def fibonacci(n):
    """0, 1, 1, 2, 3, 5, 8, 13, 21, ...

    Base case: fibonacci(0) = 0, fibonacci(1) = 1
    Smaller:   fib(n) = fib(n-1) + fib(n-2)  -> n drops by 1 and by 2.
    Warning:   TWO calls per call, so ~2^n calls in total: fibonacci(35)
               makes ~30 million calls. The same values are recomputed again
               and again; see fibonacci_iterative() for the O(n) version.
    """
    if n < 0:
        raise ValueError("fibonacci is not defined for negative numbers")
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


def sum_of_digits(n):
    """5078 -> 5 + 0 + 7 + 8 = 20

    Base case: n < 10 -> n itself (a single digit)
    Smaller:   last digit (n % 10) + sum_of_digits(n // 10)
               -> one digit shorter each call; depth = number of digits.
    """
    n = abs(n)
    if n < 10:
        return n
    return n % 10 + sum_of_digits(n // 10)


def fibonacci_iterative(n):
    """The same sequence with a loop: O(n) time, O(1) space, no recursion depth."""
    if n < 0:
        raise ValueError("fibonacci is not defined for negative numbers")
    previous, current = 0, 1
    for _ in range(n):
        previous, current = current, previous + current
    return previous


# ============================================================ category tree

class CategoryNode:
    """One category. `items` are the items filed directly here; `children`
    are its sub-categories (Photography -> Cameras, Lenses)."""

    def __init__(self, name):
        self.name = name
        self.children = []
        self.items = []

    def child(self, name):
        """The sub-category with this name, created if it doesn't exist yet."""
        for node in self.children:
            if node.name == name:
                return node
        node = CategoryNode(name)
        self.children.append(node)
        self.children.sort(key=lambda c: c.name)
        return node

    def __repr__(self):
        return f"CategoryNode({self.name!r}, children={len(self.children)})"


def build_tree(items):
    """Gear Hub at the root; a category with a parent hangs under that parent."""
    root = CategoryNode(ROOT_NAME)
    for item in items:
        parent = root.child(item.parent_category) if item.parent_category else root
        parent.child(item.category).items.append(item)
    return root


def total_items(node):
    """Items in this category and every category below it.

    Base case: a leaf (no children) -> just its own items
    Smaller:   own items + total_items(child) for each child
               -> each call goes one level down; depth = tree height.
    """
    return len(node.items) + sum(total_items(child) for child in node.children)


def tree_lines(node, depth=0):
    """'Gear Hub (7)', then each child indented 2 spaces per level.

    Base case: a leaf -> one line, the loop below does nothing
    Smaller:   this node's line, then tree_lines(child, depth + 1) for each child.
    """
    lines = [f"{'  ' * depth}{node.name} ({total_items(node)})"]
    for child in node.children:
        lines.extend(tree_lines(child, depth + 1))
    return lines


def print_tree(root):
    print("\n".join(tree_lines(root)))


def find(node, name):
    """The node called `name` in this subtree, or None.

    Base case: this node has the name -> it; no children left -> None
    Smaller:   search each child's (smaller) subtree.
    """
    if node.name == name:
        return node
    for child in node.children:
        found = find(child, name)
        if found is not None:
            return found
    return None


def count_items(root, name):
    """All items under the named category (0 if there is no such category)."""
    node = find(root, name)
    return total_items(node) if node else 0


def path_to(node, name):
    """['Gear Hub', 'Photography', 'Lenses'] for 'Lenses', or None if missing.

    Base case: this node is the target -> [its name]; a leaf that isn't -> None
    Smaller:   ask each child for the path; if one finds it, put this
               node's name in front of that path.
    """
    if node.name == name:
        return [node.name]
    for child in node.children:
        rest = path_to(child, name)
        if rest is not None:
            return [node.name] + rest
    return None


# ============================================================ iterative versions

def tree_lines_iterative(root):
    """Same output as tree_lines(), with an explicit stack instead of the call stack.

    Children are pushed in REVERSE order so the first child is popped first.
    The only depth limit is memory, not sys.getrecursionlimit().
    """
    lines = []
    stack = [(root, 0)]
    while stack:
        node, depth = stack.pop()
        lines.append(f"{'  ' * depth}{node.name} ({total_items_iterative(node)})")
        for child in reversed(node.children):
            stack.append((child, depth + 1))
    return lines


def total_items_iterative(node):
    total, stack = 0, [node]
    while stack:
        current = stack.pop()
        total += len(current.items)
        stack.extend(current.children)
    return total


def path_to_iterative(root, name):
    """Depth-first search that carries the path to each node on the stack."""
    stack = [(root, [root.name])]
    while stack:
        node, path = stack.pop()
        if node.name == name:
            return path
        for child in reversed(node.children):
            stack.append((child, path + [child.name]))
    return None


# ============================================================ demo

def _demo():
    from gearshare import GearShare

    calls = [("factorial(6)", factorial(6), ""),
             ("fibonacci(8)", fibonacci(8), "# fibonacci(0)=0, fibonacci(1)=1"),
             ("sum_of_digits(5078)", sum_of_digits(5078), "")]
    width = max(len(text) for text, _, _ in calls) + 1
    for text, value, note in calls:
        print(f"{text:<{width}}{f'-> {value}':<13}{note}".rstrip())

    shop = GearShare()
    shop.load_data(Path(__file__).resolve().parent.parent / "data")
    root = build_tree(shop.list_items())
    print("\nprint_tree(root):")
    print_tree(root)

    print()
    queries = [("count_items('Photography')", count_items(root, "Photography")),
               ("path_to('Lenses')", path_to(root, "Lenses")),
               ("path_to('Lighting')", path_to(root, "Lighting"))]
    width = max(len(text) for text, _ in queries) + 3
    for text, value in queries:
        print(f"{text:<{width}}-> {value}")


if __name__ == "__main__":
    _demo()
