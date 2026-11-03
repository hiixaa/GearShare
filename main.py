"""GearShare Mini console.

Run (PowerShell):  $env:TODAY="2026-11-03"; python main.py
Run (bash):        TODAY=2026-11-03 python main.py

This file only talks to the user. Every rule lives in GearShare.
"""

import os
import sys
from datetime import date
from pathlib import Path

from errors import GearShareError, ItemNotAvailableError
from gearshare import GearShare, rupees

DATA_DIR = Path(__file__).parent / "data"


class Cancelled(Exception):
    """The user pressed Enter without typing anything at a prompt."""


# ---------------------------------------------------------------- helpers

def plural(n, word):
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def format_table(rows, headers=None, right_align=()):
    """Columns padded to the widest cell, two spaces apart.
    Columns whose index is in `right_align` are right-aligned."""
    all_rows = ([headers] if headers else []) + [[str(c) for c in r] for r in rows]
    widths = [max(len(row[i]) for row in all_rows) for i in range(len(all_rows[0]))]
    lines = []
    for row in all_rows:
        cells = []
        for i, cell in enumerate(row):
            if i in right_align:
                cells.append(cell.rjust(widths[i]))
            elif i == len(row) - 1:
                cells.append(cell)  # no trailing spaces on the last column
            else:
                cells.append(cell.ljust(widths[i]))
        lines.append("  ".join(cells))
    return "\n".join(lines)


def today_from_env(env):
    """TODAY from the environment (YYYY-MM-DD), or the real date."""
    text = env.get("TODAY", "").strip()
    return date.fromisoformat(text) if text else date.today()


# ---------------------------------------------------------------- console

class Console:
    def __init__(self, shop, today, read=input):
        self.shop = shop
        self.today = today
        self.read = read  # injectable, so tests can type for the user
        # option -> (label, handler). Built once; the menu is printed from it.
        self.options = {
            "1": ("List catalogue", self.list_catalogue),
            "2": ("Search by name or tag", self.search),
            "3": ("Rent", self.rent),
            "4": ("Return", self.return_item),
            "5": ("Extend", self.extend),
            "6": ("Join waiting list", self.join_waiting_list),
            "7": ("Customer rentals", self.customer_rentals),
            "8": ("Overdue report", self.overdue_report),
        }

    def ask(self, prompt):
        text = self.read(prompt).strip()
        if not text:
            raise Cancelled
        return text

    # --- menu loop -----------------------------------------------------------

    def print_menu(self):
        print("=== GearShare Mini ===")
        for key, (label, _) in self.options.items():
            print(f"{key}. {label}")
        print("0. Exit")

    def run(self):
        self.print_menu()
        last = max(self.options, key=int)
        while True:
            choice = self.read("> ").strip()
            if choice == "0":
                return
            if choice not in self.options:
                print(f"Please enter a number from 0 to {last}.")
                continue
            _, handler = self.options[choice]
            try:
                handler()
            except GearShareError as e:
                print(f"ERROR [{e.code}]: {e.message}")
            except Cancelled:
                print("Nothing entered.")

    # --- 1 / 2: catalogue -------------------------------------------------------

    def list_catalogue(self):
        rows = [[i.sku, i.name, i.type_name(), i.availability_text()]
                for i in self.shop.list_items()]
        print(format_table(rows, headers=["SKU", "NAME", "TYPE", "AVAILABLE"]))

    def search(self):
        text = self.ask("Search: ")
        found = self.shop.search(text)
        if not found:
            print(f"No items match '{text}'.")
            return
        print(f"{plural(len(found), 'result')}:")
        rows = [[i.sku, i.name, f"({', '.join(i.tags)})", i.availability_text()]
                for i in found]
        print(format_table(rows))

    # --- 3-6: actions -----------------------------------------------------------

    def rent(self):
        customer = self.shop.get_customer(self.ask("Customer ID: "))
        sku = self.ask("SKU: ")
        try:
            rental = self.shop.rent(customer.customer_id, sku, self.today)
        except ItemNotAvailableError as e:
            answer = self.read(f"{e.message} Join the waiting list? (y/n): ")
            if answer.strip().lower() == "y":
                self._join(customer.customer_id, sku)
            return
        print(f"OK: {customer.name} rented '{rental.item.name}'. "
              f"Due {rental.due_date}.")

    def return_item(self):
        receipt = self.shop.return_item(self.ask("Rental ID: "), self.today)
        rental = receipt.rental
        timing = (f"Late by {plural(receipt.days_late, 'day')}."
                  if receipt.days_late else "Returned on time.")
        print(f"OK: {rental.customer.name} returned '{rental.item.name}'. "
              f"{timing} Fee: {rupees(receipt.fee)}.")
        if receipt.next_customer:
            print(f"Next on waiting list: {receipt.next_customer.name}.")

    def extend(self):
        rental = self.shop.extend(self.ask("Rental ID: "), self.today)
        print(f"OK: Extended '{rental.item.name}' (extension {rental.extensions} "
              f"of {rental.MAX_EXTENSIONS}). New due date {rental.due_date}.")

    def join_waiting_list(self):
        customer = self.shop.get_customer(self.ask("Customer ID: "))
        self._join(customer.customer_id, self.ask("SKU: "))

    def _join(self, customer_id, sku):
        position = self.shop.join_waiting_list(customer_id, sku)
        customer = self.shop.get_customer(customer_id)
        item = self.shop.get_item(sku)
        print(f"OK: {customer.name} is #{position} on the waiting list "
              f"for '{item.name}'.")

    # --- 7 / 8: reports -----------------------------------------------------------

    def customer_rentals(self):
        customer = self.shop.get_customer(self.ask("Customer ID: "))
        rentals = self.shop.customer_rentals(customer.customer_id)
        print(f"Rentals for {customer.name} ({customer.tier_name()}: "
              f"{customer.max_items()} items, {customer.rental_period()} days, "
              f"{rupees(customer.late_fee_per_day())}/day)")
        if rentals:
            rows = [[r.rental_id, r.item.name, r.issue_date, r.due_date,
                     self._status(r)] for r in rentals]
            print(format_table(
                rows, headers=["RENTAL", "ITEM", "ISSUED", "DUE", "STATUS"]))
        else:
            print("No active rentals.")
        print(f"Active rentals: {len(rentals)} of {customer.max_items()}")
        print(f"Unpaid fines: {rupees(self.shop.unpaid_fines(customer.customer_id))}")

    def _status(self, rental):
        if rental.is_overdue(self.today):
            return f"OVERDUE ({plural(rental.days_late(self.today), 'day')})"
        return "On rental"

    def overdue_report(self):
        report = self.shop.overdue_report(self.today)
        print(f"Overdue rentals as of {self.today}")
        rows = [[r.rental_id, r.customer.name, r.item.name, r.due_date,
                 days, rupees(fine)] for r, days, fine in report]
        print(format_table(
            rows,
            headers=["RENTAL", "CUSTOMER", "ITEM", "DUE", "DAYS", "FINE SO FAR"],
            right_align={4}))
        total = sum(fine for _, _, fine in report)
        print(f"Total overdue: {len(report)}   Fines so far: {rupees(total)}")


# ---------------------------------------------------------------- start-up

def main(read=input, env=os.environ, data_dir=DATA_DIR):
    try:
        today = today_from_env(env)
    except ValueError:
        print(f"TODAY must be a date like 2026-11-03, not '{env.get('TODAY')}'.")
        return 1

    shop = GearShare()
    try:
        counts = shop.load_data(data_dir)
    except (OSError, ValueError, KeyError) as e:
        print(f"Could not load data from {data_dir}: {e}")
        return 1

    print(f"Loaded {counts['items']} items, {counts['customers']} customers, "
          f"{counts['rentals']} rentals, {counts['fines']} fines.")
    print(f"Today is {today}.")

    try:
        Console(shop, today, read).run()
    except (EOFError, KeyboardInterrupt):
        print()  # Ctrl+Z / Ctrl+C: leave on a clean line instead of a traceback
    finally:
        # Runs on every exit path. Phase 3 closes the database connection here.
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # so ₹ prints on any Windows console
    sys.exit(main())
