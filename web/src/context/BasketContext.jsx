import { createContext, useContext, useEffect, useMemo, useReducer } from "react";
import { basketReducer, initialBasket, isBasketFull } from "../lib/basketReducer";
import { useCustomer } from "./CustomerContext";

// Task 4.6: the basket, shared by the navbar ("Basket (2)"), the cards,
// the details page and the basket page. Logic lives in basketReducer.js.
const BasketContext = createContext(null);

export function BasketProvider({ children }) {
  const { customer } = useCustomer();
  const [state, dispatch] = useReducer(basketReducer, initialBasket);
  const customerId = customer?.customer_id;

  // A basket belongs to ONE customer: switching customer empties it.
  useEffect(() => {
    dispatch({ type: "CLEAR" });
  }, [customerId]);

  const value = useMemo(
    () => ({
      items: state.items,
      message: state.message,
      isFull: isBasketFull(state, customer),
      contains: (sku) => state.items.some((i) => i.sku === sku),
      add: (item) => dispatch({ type: "ADD", item, customer }),
      remove: (sku) => dispatch({ type: "REMOVE", sku }),
      clear: () => dispatch({ type: "CLEAR" }),
    }),
    [state, customer],
  );
  return <BasketContext.Provider value={value}>{children}</BasketContext.Provider>;
}

export function useBasket() {
  const ctx = useContext(BasketContext);
  if (!ctx) throw new Error("useBasket must be used inside <BasketProvider>");
  return ctx;
}
