// Task 4.6: the rental basket as a reducer. Pure function: easy to test.
//
// state = { items: [gear, ...], message: string | null }
// The limit (2 / 4 / 8) is a convenience for the customer: the server still
// checks R3 on every rental and has the last word (think-about question 1).

export const initialBasket = { items: [], message: null };

/** "Basket full: Basic members can rent 2 items." */
export function fullMessage(customer) {
  return `Basket full: ${customer.membership_type} members can rent ${customer.max_items} items.`;
}

export function basketReducer(state, action) {
  switch (action.type) {
    case "ADD": {
      const { item, customer } = action;
      if (state.items.some((i) => i.sku === item.sku)) {
        return { ...state, message: `'${item.name}' is already in your basket.` };
      }
      if (customer && state.items.length >= customer.max_items) {
        return { ...state, message: fullMessage(customer) };
      }
      return { items: [...state.items, item], message: null };
    }
    case "REMOVE":
      return { items: state.items.filter((i) => i.sku !== action.sku), message: null };
    case "CLEAR":
      return initialBasket;
    default:
      throw new Error(`Unknown basket action: ${action.type}`);
  }
}

/** True when nothing more may be added for this customer. */
export function isBasketFull(state, customer) {
  return Boolean(customer) && state.items.length >= customer.max_items;
}
