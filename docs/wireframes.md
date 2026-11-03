# Phase 4: Wireframes (the five screens)

I sketched these before building the website. They're drawn in text here so
they live in the repository. Every screen has the same navbar at the top:

```
+----------------------------------------------------------------------+
| GearShare Mini  Catalogue  My rentals  Basket (2)  Add item  Customer [Ananya Nair (Basic) v] |
+----------------------------------------------------------------------+
| [ amber notice, only when full: Basket full: Basic members can rent 2 items. ] |
```

## 1. Catalogue `/` (`?q=&category=&sort=` in the URL)
```
| Catalogue                                                            |
| Search [drone_____]  Category [All v]  Sort [Name v]                 |
| 1 result                                                             |
| +----------------------+                                             |
| | DJI Mini Drone       |   <- link to /gear/1000000003               |
| | video, aerial        |                                             |
| | Drones               |                                             |
| | [0 of 1 available]   |                                             |
| | [Join waiting list]  |   (or [Add to basket], or nothing: Display) |
| +----------------------+                                             |
States: "Loading catalogue..." spinner | "Can't reach the rental server." [Retry]
        | "No items match 'zzz'. Try a different word."
```

## 2. Item details `/gear/:sku`
```
| <- Back to results            (restores the previous ?q=... search)  |
| Sony 50mm Lens                                                       |
| SKU 1000000002 · Category Lenses (Photography) · Tags photo, lens    |
| Type Equipment · Weight 280 g · Replacement price ₹18000             |
| [1 of 1 available]   [Add to basket]                                 |
| Display item: "Display item: view in the shop only", no button       |
```

## 3. My rentals `/me`
```
| My rentals                                                           |
| Vikram Shah (Plus): 1 of 4 items on rental. Unpaid fines: ₹0         |
| Rental | Item           | Due        | Status                        |
| RN001  | DJI Mini Drone | 2026-10-29 | OVERDUE (5 days)              |
States: loading | error + Retry | "You have no items on rental."
```

## 4. Rental basket `/basket`
```
| Rental basket                                                        |
| Ananya Nair (Basic): up to 2 items.                                  |
| Sony 50mm Lens                                   [Remove]            |
| [Rent] -> "Renting..."   [Clear]                                     |
|                     toast: Rented Sony 50mm Lens. Due 2026-11-06.     |
|                     red:   Rohan Das has unpaid fines of ₹600 (limit ₹500). |
```

## 5. Add item (staff) `/admin/add`
```
| SKU (10 digits) [123_______]                                         |
|   SKU must be exactly 10 digits.        <- red, under the field      |
| Name [_____]  Category [_____]  Parent category [_____]              |
| Type [Equipment v]  Tags [_____]  Weight [__] Price [__] Units [1]   |
| [Add item]  (disabled until every field is valid)                    |
| Success: "Added 'Godox Light' to the catalogue. View it" + form clears |
```
