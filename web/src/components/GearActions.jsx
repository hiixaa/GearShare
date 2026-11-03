import { useState } from "react";
import { api } from "../api";
import { useBasket } from "../context/BasketContext";
import { useCustomer } from "../context/CustomerContext";

const button =
  "rounded px-3 py-1.5 text-sm font-semibold focus:outline-2 focus:outline-offset-2 " +
  "focus:outline-slate-900 disabled:cursor-not-allowed disabled:opacity-50";

/**
 * The action under an item (card or details page):
 *  - display item          -> no button (R1)
 *  - nothing available      -> "Join waiting list" (R7)
 *  - otherwise              -> "Add to basket" (disabled when the basket is full)
 */
export default function GearActions({ item }) {
  const { customer } = useCustomer();
  const basket = useBasket();
  const [result, setResult] = useState(null);   // {ok, text} after joining the list
  const [busy, setBusy] = useState(false);

  if (item.item_type === "Display") return null;

  if (item.available === 0) {
    const join = async () => {
      setBusy(true);
      try {
        const body = await api("/waiting-list", {
          method: "POST",
          body: { customer_id: customer.customer_id, sku: item.sku },
        });
        setResult({ ok: true, text: body.message });
      } catch (err) {
        setResult({ ok: false, text: err.message });   // the server's message, exactly
      } finally {
        setBusy(false);
      }
    };
    return (
      <div className="space-y-1">
        <button type="button" className={`${button} bg-amber-500 text-slate-900`}
                onClick={join} disabled={!customer || busy}>
          Join waiting list
        </button>
        {result && (
          <p role="status" className={`text-sm ${result.ok ? "text-green-700" : "text-red-700"}`}>
            {result.text}
          </p>
        )}
      </div>
    );
  }

  const inBasket = basket.contains(item.sku);
  return (
    <button type="button" className={`${button} bg-slate-900 text-white`}
            onClick={() => basket.add(item)}
            disabled={!customer || inBasket || basket.isFull}>
      {inBasket ? "In basket" : "Add to basket"}
    </button>
  );
}
