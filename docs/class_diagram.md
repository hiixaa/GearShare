# Phase 1 Design: Class Diagram and CRC Cards

## 1. Nouns and verbs from the Rulebook

| Nouns (candidate classes)                | Verbs (candidate methods)                       |
|------------------------------------------|-------------------------------------------------|
| item / equipment / accessory / display   | rent, return, extend                            |
| customer / tier (Basic, Plus, Pro)       | join (waiting list), serve (first in list)      |
| rental, due date, extension              | calculate (late fee), cap (at price)            |
| fine, waiting list, SKU                  | check (limit, fines, duplicate, availability)   |
| shop (the service)                       | list, search, report (overdue)                  |

"Tier", "SKU", "due date" and "waiting list" are **attributes**, not classes:
a tier is fully described by three numbers, so it becomes a `Customer` subclass.

## 2. Class diagram

```mermaid
classDiagram
    direction LR

    class GearItem {
        <<abstract>>
        +sku: str
        +name: str
        +tags: list
        +category: str
        +parent_category: str
        +weight_g: int
        +price: int
        +total_units: int
        +available_units: int
        +type_name()* str
        +is_rentable()* bool
        +rental_days(customer)* int
        +can_extend()* bool
    }
    class Equipment
    class Accessory
    class DisplayItem
    GearItem <|-- Equipment
    GearItem <|-- Accessory
    GearItem <|-- DisplayItem

    class Customer {
        <<abstract>>
        +customer_id: str
        +name: str
        +email: str
        +tier_name()* str
        +max_items()* int
        +rental_period()* int
        +late_fee_per_day()* int
    }
    class BasicCustomer
    class PlusCustomer
    class ProCustomer
    Customer <|-- BasicCustomer
    Customer <|-- PlusCustomer
    Customer <|-- ProCustomer

    class Rental {
        +rental_id: str
        +customer: Customer
        +item: GearItem
        +issue_date: date
        +due_date: date
        +return_date: date
        +extensions: int
        +is_open() bool
        +days_late(on) int
        +late_fee(on) int
    }

    class Fine {
        +rental_id: str
        +amount: int
        +paid: bool
    }

    class GearShare {
        +items: dict~sku, GearItem~
        +customers: dict~id, Customer~
        +rentals: list~Rental~
        +fines: list~Fine~
        +rented_skus: set
        +waiting_lists: dict~sku, list~
        +audit_log: list
        +load_data(folder)
        +list_items()
        +search(text)
        +rent(customer_id, sku, today)
        +return_item(rental_id, today)
        +extend(rental_id, today)
        +join_waiting_list(customer_id, sku)
        +customer_rentals(customer_id)
        +overdue_report(today)
    }

    Rental o-- Customer : has-a
    Rental o-- GearItem : has-a
    GearShare *-- GearItem : owns many
    GearShare *-- Customer : owns many
    GearShare *-- Rental : owns many
    GearShare *-- Fine : owns many
```

## 3. Inheritance or composition? (one sentence each)

| Relationship                          | Kind        | Why                                                                                         |
|---------------------------------------|-------------|---------------------------------------------------------------------------------------------|
| Equipment / Accessory / DisplayItem → GearItem | is-a (inheritance) | Each *is* a piece of gear with the same SKU, name and price, and only differs in how it answers "can I be rented / for how long / can I be extended". |
| Basic / Plus / ProCustomer → Customer | is-a (inheritance) | Each *is* a customer with the same id, name and email, and only the three tier numbers differ. |
| Rental → Customer, Rental → GearItem  | has-a (composition) | A rental is not a kind of customer or item; it *links* one customer to one item for a period. |
| GearShare → items, customers, rentals, fines | has-a (composition) | The shop *holds* the collections and enforces rules across them; it is not itself an item or customer. |
| Fine → Rental (by `rental_id`)        | has-a (reference)  | A fine belongs to exactly one rental, but a rental may have no fine, so it is kept as a separate record. |

## 4. What each abstract class forces its subclasses to answer

**`GearItem`** (abstract) — every item type must answer:

| Question                 | Equipment                  | Accessory        | DisplayItem  |
|--------------------------|----------------------------|------------------|--------------|
| `type_name()`            | `Equipment`                | `Accessory`      | `Display`    |
| `is_rentable()` (R1)     | True                       | True             | **False**    |
| `rental_days(customer)`  | `customer.rental_period()` | **2** (R2)       | 0 (never rented) |
| `can_extend()` (R2)      | True                       | **False**        | False        |

**`Customer`** (abstract) — every tier must answer:

| Question               | Basic | Plus | Pro |
|------------------------|-------|------|-----|
| `max_items()` (R3)     | 2     | 4    | 8   |
| `rental_period()`      | 3     | 5    | 7   |
| `late_fee_per_day()` (R5) | 50 | 100  | 150 |

So "a display item cannot be rented" lives in `DisplayItem`, and "a Basic
customer has a 3-day period" lives in `BasicCustomer`. `GearShare` never asks
*which* tier or type an object is; it only calls these methods. That is why
there is no `if tier == ...` anywhere.

## 5. CRC cards

| **GearItem** (abstract) | |
|---|---|
| **Responsibilities** | Validate its own SKU (R9), name, units; track available units; say whether it is rentable (R1), for how long (R2) and whether it can be extended (R2) |
| **Collaborators** | Customer (asks its rental period) |

| **Customer** (abstract) | |
|---|---|
| **Responsibilities** | Validate its own id, name, email; know its tier's item limit (R3), rental period and daily late fee (R5) |
| **Collaborators** | — |

| **Rental** | |
|---|---|
| **Responsibilities** | Remember who rented what and when; count extensions (R6); compute days late (R10) and the late fee capped at the item price (R5) |
| **Collaborators** | Customer (late fee per day), GearItem (price) |

| **Fine** | |
|---|---|
| **Responsibilities** | Record the amount charged for one rental and whether it is paid (R4) |
| **Collaborators** | Rental (by id) |

| **GearShare** (service) | |
|---|---|
| **Responsibilities** | Load data; run the order of checks for renting (R1, R3, R4, R7, R8, R9); return, extend (R6), waiting list (R7); reports; audit log |
| **Collaborators** | GearItem, Customer, Rental, Fine, errors |
