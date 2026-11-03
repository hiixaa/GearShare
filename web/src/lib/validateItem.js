// Task 4.4: validation for the staff "Add item" form. Pure function: easy to test.
// The same rules run again on the server (InvalidSKUError, ValueError): this
// copy only gives instant feedback next to the field.

export const EMPTY_ITEM = {
  sku: "",
  name: "",
  category: "",
  parent_category: "",
  item_type: "Equipment",
  tags: "",
  weight_g: "",
  price: "",
  total_units: "1",
};

const isWholeNumber = (text) => /^\d+$/.test(String(text).trim());

/** Returns {field: message} for every invalid field; {} means valid. */
export function validateItem(form) {
  const errors = {};
  if (!/^\d{10}$/.test(form.sku.trim())) errors.sku = "SKU must be exactly 10 digits.";
  if (!form.name.trim()) errors.name = "Name is required.";
  if (!form.category.trim()) errors.category = "Category is required.";
  if (!isWholeNumber(form.total_units) || Number(form.total_units) < 1) {
    errors.total_units = "Units must be at least 1.";
  }
  if (!isWholeNumber(form.weight_g)) errors.weight_g = "Weight must be a whole number of grams.";
  if (!isWholeNumber(form.price)) errors.price = "Price must be a whole number of rupees.";
  return errors;
}

/** The JSON body for POST /gear. */
export function toRequestBody(form) {
  return {
    sku: form.sku.trim(),
    name: form.name.trim(),
    category: form.category.trim(),
    parent_category: form.parent_category.trim() || null,
    item_type: form.item_type,
    tags: form.tags.split(",").map((t) => t.trim().toLowerCase()).filter(Boolean),
    weight_g: Number(form.weight_g),
    price: Number(form.price),
    total_units: Number(form.total_units),
  };
}
