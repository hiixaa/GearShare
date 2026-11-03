"""GearShare HTTP API (FastAPI).

    python -m uvicorn api.main:app --reload --port 8000

Environment:
    TODAY                 business date, e.g. 2026-11-03 (default: real date)
    GEARSHARE_DB          database file (default: data/gearshare.db)
    GEARSHARE_WEB_ORIGIN  the React dev server allowed by CORS
                          (default: http://localhost:5173)

All endpoints are `async def`, so they all run on the ONE event-loop thread:
SQLite connections may only be used by the thread that opened them, and
GearShare's in-memory shop is not thread-safe (DECISIONS D29).
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import errors
from api.schemas import NewItem, RentalRequest, WaitingListRequest
from dsa.sorting import catalogue_sort
from gearshare import GearShare
from items import ITEM_TYPES
from main import today_from_env
from storage import Storage

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("GEARSHARE_DB", ROOT / "data" / "gearshare.db"))
WEB_ORIGIN = os.environ.get("GEARSHARE_WEB_ORIGIN", "http://localhost:5173")

SORTS = {
    "name": lambda items: sorted(items, key=lambda i: i.name.lower()),
    "catalogue": catalogue_sort,   # top-level category, heaviest first, name (Phase 2)
    "weight": lambda items: sorted(items, key=lambda i: (-i.weight_g, i.name.lower())),
}


# --------------------------------------------------------------- JSON shapes

def fail(status, code, message):
    """An error response in the same shape as every engine error."""
    return JSONResponse(status_code=status, content=errors.error_body(code, message))


def item_json(item):
    """Exactly the fields of the spec's GET /gear sample."""
    return {
        "sku": item.sku,
        "name": item.name,
        "tags": item.tags,
        "category": item.category,
        "item_type": item.type_name(),
        "available": item.available_units,
        "total": item.total_units,
        "weight_g": item.weight_g,
    }


def item_details_json(item):
    """The details page shows a little more than a catalogue card."""
    return {**item_json(item), "price": item.price, "top_category": item.top_category}


def customer_json(customer):
    return {
        "customer_id": customer.customer_id,
        "name": customer.name,
        "membership_type": customer.tier_name(),
        "max_items": customer.max_items(),
    }


# --------------------------------------------------------------- the app

def create_app(db_path=None, today=None, web_origin=None):
    """Build the app. Tests pass their own temporary database and date."""
    db_path = Path(db_path or DB_PATH)

    @asynccontextmanager
    async def lifespan(app):
        storage = Storage(db_path)
        shop = GearShare(storage)
        shop.load_data()
        app.state.shop = shop
        app.state.today = today or today_from_env(os.environ)
        yield
        storage.close()

    app = FastAPI(title="GearShare Mini API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[web_origin or WEB_ORIGIN],   # only the React dev server
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    errors.register(app)

    def shop(request: Request) -> GearShare:
        return request.app.state.shop

    # ---- catalogue ----------------------------------------------------------

    @app.get("/gear")
    async def list_gear(request: Request, q: str = "", category: str = "", sort: str = "name"):
        gs = shop(request)
        found = gs.search(q) if q.strip() else gs.list_items()
        if category:
            found = [i for i in found if category in (i.category, i.top_category)]
        if sort not in SORTS:
            return fail(422, "ValidationError", f"sort must be one of: {', '.join(SORTS)}")
        return [item_json(i) for i in SORTS[sort](found)]

    @app.get("/gear/{sku}")
    async def get_gear(request: Request, sku: str):
        return item_details_json(shop(request).get_item(sku))

    @app.get("/categories")
    async def list_categories(request: Request):
        """Category filter options: every category and parent in use, A-Z."""
        names = set()
        for item in shop(request).list_items():
            names.add(item.category)
            names.add(item.top_category)
        return sorted(names)

    @app.post("/gear", status_code=201)
    async def add_gear(request: Request, body: NewItem):
        if body.item_type not in ITEM_TYPES:
            return fail(422, "ValidationError",
                        f"item_type must be one of: {', '.join(ITEM_TYPES)}")
        try:
            item = ITEM_TYPES[body.item_type](
                sku=body.sku, name=body.name, tags=body.tags, category=body.category,
                parent_category=body.parent_category, weight_g=body.weight_g,
                price=body.price, total_units=body.total_units)
        except ValueError as e:          # blank name, negative units, ...
            return fail(422, "ValidationError", str(e))
        try:
            shop(request).add_item(item)
        except ValueError as e:          # the SKU is already used (R9)
            message = str(e)
            return fail(409, "R9", message[0].upper() + message[1:])
        return item_details_json(item)

    # ---- customers ------------------------------------------------------------

    @app.get("/customers")
    async def list_customers(request: Request):
        return [customer_json(c) for c in shop(request).customers.values()]

    @app.get("/customers/{customer_id}/rentals")
    async def customer_rentals(request: Request, customer_id: str):
        gs, today = shop(request), request.app.state.today
        customer = gs.get_customer(customer_id)
        return {
            "customer": customer.name,
            "membership_type": customer.tier_name(),
            "max_items": customer.max_items(),
            "unpaid_fines": gs.unpaid_fines(customer.customer_id),
            "active": [{
                "rental_id": r.rental_id,
                "item": r.item.name,
                "due_date": r.due_date.isoformat(),
                "days_overdue": r.days_late(today),
            } for r in gs.customer_rentals(customer.customer_id)],
        }

    # ---- rentals ----------------------------------------------------------------

    @app.post("/rentals", status_code=201)
    async def rent(request: Request, body: RentalRequest):
        rental = shop(request).rent(body.customer_id, body.sku, request.app.state.today)
        return {"rental_id": rental.rental_id, "due_date": rental.due_date.isoformat()}

    @app.post("/rentals/{rental_id}/return")
    async def return_item(request: Request, rental_id: str):
        receipt = shop(request).return_item(rental_id, request.app.state.today)
        return {
            "rental_id": receipt.rental.rental_id,
            "days_late": receipt.days_late,
            "fine": receipt.fee,
            "next_in_waiting_list": receipt.next_customer.name if receipt.next_customer else None,
        }

    @app.post("/waiting-list", status_code=201)
    async def join_waiting_list(request: Request, body: WaitingListRequest):
        gs = shop(request)
        position = gs.join_waiting_list(body.customer_id, body.sku)
        customer, item = gs.get_customer(body.customer_id), gs.get_item(body.sku)
        return {"position": position,
                "message": f"{customer.name} is #{position} on the waiting list "
                           f"for '{item.name}'."}

    return app


app = create_app()
