import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../api";

// Task 4.6: "who am I", shared by the navbar picker, the basket, My rentals
// and every "Add to basket" button. Without a context, the customer would be
// passed down through Layout -> pages -> lists -> cards (prop drilling).
const CustomerContext = createContext(null);

const STORAGE_KEY = "gearshare.customerId";

function readSavedId() {
  try {
    return localStorage.getItem(STORAGE_KEY) ?? "C001";
  } catch {
    return "C001";
  }
}

export function CustomerProvider({ children }) {
  const [customers, setCustomers] = useState([]);
  const [status, setStatus] = useState("loading");
  const [customerId, setCustomerId] = useState(readSavedId);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setStatus("loading");
    api("/customers", { signal: controller.signal })
      .then((list) => {
        setCustomers(list);
        setStatus("success");
      })
      .catch((err) => {
        if (err.name !== "AbortError") setStatus("error");
      });
    return () => controller.abort();
  }, [attempt]);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, customerId);
    } catch {
      /* private window: the choice just isn't remembered */
    }
  }, [customerId]);

  const value = useMemo(
    () => ({
      customers,
      status,
      customer: customers.find((c) => c.customer_id === customerId) ?? null,
      setCustomerId,
      reload: () => setAttempt((n) => n + 1),
    }),
    [customers, status, customerId],
  );
  return <CustomerContext.Provider value={value}>{children}</CustomerContext.Provider>;
}

export function useCustomer() {
  const ctx = useContext(CustomerContext);
  if (!ctx) throw new Error("useCustomer must be used inside <CustomerProvider>");
  return ctx;
}
