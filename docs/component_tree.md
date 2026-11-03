# Phase 4: Component Tree and Where State Lives

```
main.jsx
└─ App                                   routes (Task 4.5)
   └─ BrowserRouter
      └─ CustomerProvider                STATE: customers[], customerId (saved in localStorage), status
         └─ BasketProvider               STATE: useReducer(basketReducer) -> {items[], message}
            └─ Layout (children)         reads: customer, basket.isFull / message
               ├─ Navbar                 reads: customers, customer, basket.items.length
               └─ Routes
                  ├─ "/"          CataloguePage     STATE: URL search params q / category / sort
                  │                                 derived: debouncedQ (useDebounce)
                  │                                 fetch state: useApi("/gear?..."), useApi("/categories")
                  │   └─ GearList   props: items
                  │       └─ GearCard (key = sku)   props: item
                  │           ├─ AvailabilityBadge  props: itemType, available, total
                  │           └─ GearActions        props: item; STATE: result, busy
                  ├─ "/gear/:sku"  GearDetailsPage  URL param sku; location.state.from (search to go back to)
                  │                                 fetch state: useApi("/gear/:sku")
                  │   ├─ AvailabilityBadge, GearActions (same as on the card)
                  ├─ "/me"         MyRentalsPage    fetch state: useApi("/customers/:id/rentals")
                  ├─ "/basket"     BasketPage       STATE: renting (bool), results[] (toasts)
                  ├─ "/admin/add"  AddItemPage      STATE: form (controlled inputs), touched, saving, result
                  │                                 derived: errors = validateItem(form)
                  │   └─ Field ×8   props: name, label, form, errors, touched, onChange, onBlur
                  └─ "*"           NotFoundPage
```

Shared by several screens: `StatusViews` (`Loading`, `ErrorState` with Retry, `Empty`).

## Who owns each piece of state, and why there

| State | Owner | Why there |
|---|---|---|
| Which customer am I | `CustomerProvider` (context) | Needed by the navbar, every add button, the basket and My rentals. Passing it as props would drill it through Layout → page → GearList → GearCard → GearActions. |
| Basket items + message | `BasketProvider` (`useReducer`) | Needed by the navbar count, the cards, the details page and the basket page. A reducer keeps the ADD / REMOVE / CLEAR rules in one testable pure function. |
| Search text, category, sort | **The URL** (`useSearchParams`) | Survives going to `/gear/:sku` and back ("Back to results"), a reload, and a shared link (D32). |
| Debounced search text | `CataloguePage` (`useDebounce`) | Derived from the URL; only used to decide when to fetch. |
| Loading / success / error + data for each fetch | The page, via `useApi(path)` | Each screen has its own request; `useApi` aborts the previous one when `path` changes. |
| Form fields, touched fields | `AddItemPage` | Only that form uses them. The errors are **derived** with `validateItem(form)`, not stored, so they can't get out of date. |
| Renting… / toasts | `BasketPage` | Only checkout uses them. |
| "Joined the waiting list" message | `GearActions` | Belongs to one item's button. This is why the list's `key` must be the SKU. |

Components receive data **only through props** (`GearList`, `GearCard`,
`AvailabilityBadge` know nothing about fetch or the API). Only `api.js` calls
`fetch()`.
