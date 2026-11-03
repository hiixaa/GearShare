"""Task 4.0: the HTTP API. Every request/response sample from the spec, exactly."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from api.main import create_app


@pytest.fixture
def client(db_path):
    app = create_app(db_path=db_path, today=date(2026, 11, 3))
    with TestClient(app) as c:          # `with` runs the lifespan (opens the DB)
        yield c


# --- the spec's samples ---------------------------------------------------------------

def test_search_drone(client):
    r = client.get("/gear", params={"q": "drone", "sort": "name"})
    assert r.status_code == 200
    assert r.json() == [{
        "sku": "1000000003", "name": "DJI Mini Drone",
        "tags": ["video", "aerial"], "category": "Drones",
        "item_type": "Equipment", "available": 0, "total": 1, "weight_g": 249}]


def test_search_nothing(client):
    r = client.get("/gear", params={"q": "zzz"})
    assert (r.status_code, r.json()) == (200, [])


def test_unknown_item(client):
    r = client.get("/gear/1000000999")
    assert r.status_code == 404
    assert r.json() == {"error": "ItemNotFoundError", "message": "No item with SKU 1000000999."}


def test_rent_then_duplicate(client):
    body = {"customer_id": "C001", "sku": "1000000002"}
    r = client.post("/rentals", json=body)
    assert (r.status_code, r.json()) == (201, {"rental_id": "RN011", "due_date": "2026-11-06"})
    r = client.post("/rentals", json=body)
    assert r.status_code == 409
    assert r.json() == {"error": "R8",
                        "message": "Ananya Nair already has a unit of 'Sony 50mm Lens'."}


@pytest.mark.parametrize("body, status, expected", [
    ({"customer_id": "C004", "sku": "1000000004"}, 409,
     {"error": "R4", "message": "Rohan Das has unpaid fines of ₹600 (limit ₹500)."}),
    ({"customer_id": "C003", "sku": "1000000006"}, 409,
     {"error": "R1", "message": "'Vintage Leica (Showcase)' is a display item and cannot be rented."}),
    ({"customer_id": "C009", "sku": "1000000002"}, 404,
     {"error": "CustomerNotFoundError", "message": "No customer with ID C009."}),
    ({"customer_id": "C001", "sku": "123"}, 422,
     {"error": "InvalidSKUError", "message": "SKU must be exactly 10 digits."}),
])
def test_rent_errors(client, body, status, expected):
    r = client.post("/rentals", json=body)
    assert (r.status_code, r.json()) == (status, expected)


def test_return_with_waiting_list(client):
    client.post("/waiting-list", json={"customer_id": "C003", "sku": "1000000003"})
    r = client.post("/rentals/RN001/return")
    assert r.status_code == 200
    assert r.json() == {"rental_id": "RN001", "days_late": 5, "fine": 500,
                        "next_in_waiting_list": "Meera Joshi"}


def test_return_nobody_waiting_gives_null(client):
    r = client.post("/rentals/RN003/return")
    assert r.json() == {"rental_id": "RN003", "days_late": 0, "fine": 0,
                        "next_in_waiting_list": None}


def test_customer_rentals(client):
    r = client.get("/customers/C002/rentals")
    assert r.status_code == 200
    assert r.json() == {"customer": "Vikram Shah", "membership_type": "Plus",
                        "max_items": 4, "unpaid_fines": 0,
                        "active": [{"rental_id": "RN001", "item": "DJI Mini Drone",
                                    "due_date": "2026-10-29", "days_overdue": 5}]}


# --- endpoints the website needs ----------------------------------------------------------

def test_catalogue_lists_all_7_and_filters(client):
    assert len(client.get("/gear").json()) == 7
    photo = client.get("/gear", params={"category": "Photography"}).json()
    assert [i["name"] for i in photo] == ["Canon EOS 200D", "Sony 50mm Lens"]
    assert client.get("/gear", params={"sort": "price"}).status_code == 422


def test_catalogue_sort(client):
    names = [i["name"] for i in client.get("/gear", params={"sort": "catalogue"}).json()]
    assert names[:4] == ["SD Card 128GB", "Rode Wireless Mic", "DJI Mini Drone", "Canon EOS 200D"]


def test_item_details_and_categories(client):
    sony = client.get("/gear/1000000002").json()
    assert (sony["available"], sony["total"], sony["price"]) == (1, 1, 18000)
    assert "Photography" in client.get("/categories").json()


def test_customers_for_the_picker(client):
    customers = client.get("/customers").json()
    assert customers[0] == {"customer_id": "C001", "name": "Ananya Nair",
                            "membership_type": "Basic", "max_items": 2}
    assert len(customers) == 5


def test_waiting_list_join(client):
    r = client.post("/waiting-list", json={"customer_id": "C003", "sku": "1000000003"})
    assert r.status_code == 201
    assert r.json()["message"] == "Meera Joshi is #1 on the waiting list for 'DJI Mini Drone'."
    r = client.post("/waiting-list", json={"customer_id": "C001", "sku": "1000000002"})
    assert (r.status_code, r.json()["error"]) == (409, "R7")


def test_add_item(client):
    body = {"sku": "1000000010", "name": "Godox Light", "category": "Lighting",
            "parent_category": "Photography", "tags": ["light"],
            "weight_g": 900, "price": 7000, "total_units": 2}
    r = client.post("/gear", json=body)
    assert r.status_code == 201 and r.json()["name"] == "Godox Light"
    assert client.get("/gear", params={"q": "godox"}).json()[0]["available"] == 2
    r = client.post("/gear", json=body)                                      # same SKU
    assert r.status_code == 409 and r.json()["error"] == "R9"
    r = client.post("/gear", json={**body, "sku": "123"})
    assert (r.status_code, r.json()["error"]) == (422, "InvalidSKUError")
    r = client.post("/gear", json={**body, "sku": "1000000011", "name": " "})
    assert (r.status_code, r.json()) == (422, {"error": "ValidationError",
                                               "message": "Name cannot be blank."})


def test_missing_field_has_the_same_error_shape(client):
    r = client.post("/rentals", json={"customer_id": "C001"})
    assert r.status_code == 422
    assert r.json()["error"] == "ValidationError" and "sku" in r.json()["message"]


def test_rental_is_saved_in_the_database(client, db_path):
    client.post("/rentals", json={"customer_id": "C001", "sku": "1000000002"})
    with TestClient(create_app(db_path=db_path, today=date(2026, 11, 3))) as fresh:
        sony = fresh.get("/gear/1000000002").json()
    assert sony["available"] == 0


def test_cors_allows_only_the_react_dev_server(client):
    ok = client.options("/gear", headers={"Origin": "http://localhost:5173",
                                          "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    bad = client.options("/gear", headers={"Origin": "http://evil.example",
                                           "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in bad.headers
