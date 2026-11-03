"""Task 2.4: a customer's rental history as a singly linked list.

    python -m dsa.history     # prints the spec's rental-history sample

Each Node holds one rental ID and a pointer to the next (older) node.
Inserting at the head is O(1), so the newest rental is always first.
"""

from pathlib import Path


class Node:
    def __init__(self, rental_id, next_node=None):
        self.rental_id = rental_id
        self.next = next_node

    def __repr__(self):
        return f"Node({self.rental_id!r})"


class RentalHistory:
    def __init__(self):
        self.head = None
        self._size = 0

    def insert_at_head(self, rental_id):
        """O(1): the new node points at the old head and becomes the head."""
        self.head = Node(rental_id, self.head)
        self._size += 1

    def __iter__(self):
        """Traversal: follow the next pointers from the head until None. O(n)."""
        node = self.head
        while node is not None:
            yield node.rental_id
            node = node.next

    def __len__(self):
        return self._size

    def __str__(self):
        return " -> ".join([*self, "None"])

    def __repr__(self):
        return f"RentalHistory({list(self)})"

    # --- stretch ---------------------------------------------------------------

    def delete(self, rental_id):
        """Unlink the first node with this rental ID. True if found. O(n)."""
        previous, node = None, self.head
        while node is not None:
            if node.rental_id == rental_id:
                if previous is None:
                    self.head = node.next          # deleting the head
                else:
                    previous.next = node.next      # skip over the node
                self._size -= 1
                return True
            previous, node = node, node.next
        return False

    def reverse(self):
        """Reverse in place by turning every pointer around. O(n) time, O(1) space."""
        previous, node = None, self.head
        while node is not None:
            node.next, previous, node = previous, node, node.next
        self.head = previous

    def second_from_end(self):
        """Rental ID of the 2nd node from the end, or None. One pass, two pointers:
        `lead` starts 2 nodes ahead, so when it falls off the end, `trail` is there."""
        lead = trail = self.head
        for _ in range(2):
            if lead is None:
                return None                    # fewer than 2 nodes
            lead = lead.next
        while lead is not None:
            lead, trail = lead.next, trail.next
        return trail.rental_id


def history_for(shop, customer_id):
    """Build a customer's history, inserting oldest first so the newest ends up at the head."""
    history = RentalHistory()
    rentals = sorted(shop.rentals_by_customer[customer_id],
                     key=lambda r: (r.issue_date, r.rental_id))
    for rental in rentals:
        history.insert_at_head(rental.rental_id)
    return history


def _demo():
    from gearshare import GearShare

    shop = GearShare()
    shop.load_data(Path(__file__).resolve().parent.parent / "data")
    for customer_id in ("C002", "C003"):
        print(f"Rental history, {shop.customers[customer_id].name} (newest first):")
        print(history_for(shop, customer_id))


if __name__ == "__main__":
    _demo()
