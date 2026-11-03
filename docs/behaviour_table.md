# Phase 4: Behaviour Table Checklist

How to check: `python -m sql.setup_db`, start the API
(`$env:TODAY="2026-11-03"; python -m uvicorn api.main:app --port 8000`) and
the website (`cd web; npm run dev`), then open **http://localhost:5173**.
Reset the database between runs with `python -m sql.setup_db`.

- **Code** = how the code implements the row.
- **Auto** = covered by an automated test.
- **Browser** = tick ✅ after checking it by hand in the browser.

| Action | Expected result | Code / auto test | Browser |
|---|---|---|---|
| Open `/` | Spinner `Loading catalogue...` then 7 cards | `CataloguePage` + `Loading`; API `test_catalogue_lists_all_7_and_filters` | ☐ |
| Type `drone` | Only DJI Mini Drone. Text: `1 result` | `q` in the URL → debounced `GET /gear?q=drone`; API `test_search_drone` | ☐ |
| Type `zzz` | `No items match 'zzz'. Try a different word.` | `Empty` in `CataloguePage`; API `test_search_nothing` | ☐ |
| Click the Sony 50mm Lens card | URL `/gear/1000000002`, shows `1 of 1 available` | `GearCard` link + `GearDetailsPage`; API `test_item_details_and_categories` | ☐ |
| Open DJI Mini Drone | `0 of 1 available`, button `Join waiting list` | `GearActions` (available = 0) | ☐ |
| Open Vintage Leica (Showcase) | `Display item: view in the shop only`, no rent button | `AvailabilityBadge` + `GearActions` return no button for Display | ☐ |
| Pick Ananya (Basic), add 2 items, try a 3rd | `Basket full: Basic members can rent 2 items.`, 3rd button disabled | `Layout` notice + `isBasketFull`; web `logic.test.js` | ☐ |
| Click Rent with a valid basket | `Renting...` then toast `Rented Sony 50mm Lens. Due 2026-11-06.` | `BasketPage.checkout`; API `test_rent_then_duplicate` | ☐ |
| Back on the catalogue after renting | Sony 50mm Lens shows `0 of 1 available` | The catalogue fetches fresh data on every visit | ☐ |
| Pick Rohan, try to rent Manfrotto Tripod | Red: `Rohan Das has unpaid fines of ₹600 (limit ₹500).` | The server's message shown as-is; API `test_rent_errors` | ☐ |
| Pick Vikram, open My rentals | Row: DJI Mini Drone, due 2026-10-29, `OVERDUE (5 days)` | `MyRentalsPage`; API `test_customer_rentals` | ☐ |
| Stop the API server, reload | `Can't reach the rental server.` with a Retry button | `api.js` network error → `ErrorState` | ☐ |
| Open `/nothing` | 404 page with a link back to the catalogue | `NotFoundPage` (route `*`) | ☐ |
| Add item: SKU `123` | Under the field: `SKU must be exactly 10 digits.`, submit disabled | `validateItem`; web `logic.test.js` | ☐ |
| Add item: all fields valid | Success message, the form clears, the item appears in the catalogue | `AddItemPage.submit`; API `test_add_item` | ☐ |
| Resize to 360 px wide | One column of cards, nothing cut off, no sideways scrolling | `grid-cols-1` below 640 px, wrapping navbar, `overflow-x: hidden`; table in `overflow-x-auto` | ☐ |

## Notes
- Use `http://localhost:5173`, not `http://127.0.0.1:5173`. CORS allows only the `localhost` origin (D30).
- Don't run the console (`main.py`) at the same time as the API (D26).
- Race condition (Task 4.3): with DevTools → Network → "Slow 3G", type `d`, `dr`, `drone` quickly. Only the last request completes; the earlier ones show as **(canceled)**, so an old response can't overwrite a newer one.
