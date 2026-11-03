"""Request bodies. Only the SHAPE is checked here (fields and types).

Deliberately no pattern on `sku`: "123" must reach GearShare, so the answer is
the engine's InvalidSKUError with the console's message (spec sample), not a
generic validation error. The rules live in the engine only.
"""

from pydantic import BaseModel


class RentalRequest(BaseModel):
    customer_id: str
    sku: str


class WaitingListRequest(BaseModel):
    customer_id: str
    sku: str


class NewItem(BaseModel):
    sku: str
    name: str
    category: str
    parent_category: str | None = None
    item_type: str = "Equipment"
    tags: list[str] = []
    weight_g: int
    price: int
    total_units: int
