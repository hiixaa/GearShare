import { describe, expect, it } from "vitest";
import { basketReducer, fullMessage, initialBasket, isBasketFull } from "./basketReducer";
import { EMPTY_ITEM, toRequestBody, validateItem } from "./validateItem";

const ananya = { customer_id: "C001", name: "Ananya Nair", membership_type: "Basic", max_items: 2 };
const sony = { sku: "1000000002", name: "Sony 50mm Lens" };
const tripod = { sku: "1000000004", name: "Manfrotto Tripod" };
const card = { sku: "1000000007", name: "SD Card 128GB" };

describe("basketReducer (Task 4.6)", () => {
  it("adds up to the tier limit, then blocks with the spec's message", () => {
    let s = basketReducer(initialBasket, { type: "ADD", item: sony, customer: ananya });
    s = basketReducer(s, { type: "ADD", item: tripod, customer: ananya });
    expect(s.items).toHaveLength(2);
    expect(isBasketFull(s, ananya)).toBe(true);
    s = basketReducer(s, { type: "ADD", item: card, customer: ananya });
    expect(s.items).toHaveLength(2);
    expect(s.message).toBe("Basket full: Basic members can rent 2 items.");
    expect(fullMessage(ananya)).toBe(s.message);
  });

  it("refuses the same item twice (R8 in the basket)", () => {
    let s = basketReducer(initialBasket, { type: "ADD", item: sony, customer: ananya });
    s = basketReducer(s, { type: "ADD", item: sony, customer: ananya });
    expect(s.items).toHaveLength(1);
    expect(s.message).toBe("'Sony 50mm Lens' is already in your basket.");
  });

  it("removes and clears", () => {
    let s = basketReducer(initialBasket, { type: "ADD", item: sony, customer: ananya });
    s = basketReducer(s, { type: "ADD", item: tripod, customer: ananya });
    s = basketReducer(s, { type: "REMOVE", sku: sony.sku });
    expect(s.items).toEqual([tripod]);
    expect(basketReducer(s, { type: "CLEAR" })).toEqual(initialBasket);
  });

  it("rejects unknown actions", () => {
    expect(() => basketReducer(initialBasket, { type: "PAY" })).toThrow();
  });
});

describe("validateItem (Task 4.4)", () => {
  const valid = { ...EMPTY_ITEM, sku: "1000000010", name: "Godox Light", category: "Lighting",
                  weight_g: "900", price: "7000", total_units: "2" };

  it("accepts a valid item", () => {
    expect(validateItem(valid)).toEqual({});
  });

  it("gives the spec's SKU message", () => {
    expect(validateItem({ ...valid, sku: "123" }).sku).toBe("SKU must be exactly 10 digits.");
  });

  it("requires a name and at least 1 unit", () => {
    const errors = validateItem({ ...valid, name: "  ", total_units: "0" });
    expect(errors.name).toBe("Name is required.");
    expect(errors.total_units).toBe("Units must be at least 1.");
  });

  it("builds the POST /gear body", () => {
    expect(toRequestBody({ ...valid, tags: "Light, Studio ,", parent_category: "" })).toEqual({
      sku: "1000000010", name: "Godox Light", category: "Lighting", parent_category: null,
      item_type: "Equipment", tags: ["light", "studio"], weight_g: 900, price: 7000, total_units: 2,
    });
  });
});
