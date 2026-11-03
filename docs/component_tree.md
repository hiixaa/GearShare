# Phase 4: Component Tree and Where State Lives

This is the React app's component tree. Next to each component I've noted the
state it owns and the props it receives.

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

`StatusViews` (`Loading`, `ErrorState` with a Retry button, and `Empty`) is
shared by every screen that loads data.

## Who owns each piece of state, and why

| State | Owner | Why there |
|---|---|---|
| Who the current customer is | `CustomerProvider` (context) | The navbar, every add button, the basket and My rentals all need it. As props, it would have to be passed down through Layout → page → GearList → GearCard → GearActions. |
| Basket items and message | `BasketProvider` (`useReducer`) | The navbar count, the cards, the details page and the basket page all need it. A reducer keeps the ADD / REMOVE / CLEAR rules in one pure function that's easy to test. |
| Search text, category, sort | the URL (`useSearchParams`) | It survives opening an item and coming back ("Back to results"), a reload, and a shared link (D32). |
| Debounced search text | `CataloguePage` (`useDebounce`) | Worked out from the URL, and only used to decide when to fetch. |
| Loading / success / error, and the data, for each request | each page, through `useApi(path)` | Every screen makes its own request, and `useApi` cancels the old one when the path changes. |
| Form fields and which ones were touched | `AddItemPage` | Only this form uses them. The error messages are worked out from the fields with `validateItem(form)` rather than stored, so they can never be out of date. |
| "Renting..." and the toasts | `BasketPage` | Only checkout uses them. |
| The "joined the waiting list" message | `GearActions` | It belongs to one item's button, which is why the list's `key` has to be the SKU and not the array index. |

Components get their data only through props: `GearList`, `GearCard` and
`AvailabilityBadge` don't know anything about the API or where the data came
from. `api.js` is the only file that calls `fetch()`.
