import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Empty } from "../components/StatusViews";
import { useBasket } from "../context/BasketContext";
import { useCustomer } from "../context/CustomerContext";

export default function BasketPage() {
  const { customer } = useCustomer();
  const basket = useBasket();
  const [renting, setRenting] = useState(false);
  const [results, setResults] = useState([]);   // [{ok, text}] from the last checkout

  // Task 4.6: one POST /rentals per item. The SERVER has the last word: its
  // message is shown exactly, and only the items it accepted leave the basket.
  const checkout = async () => {
    setRenting(true);
    const outcome = [];
    for (const item of basket.items) {
      try {
        const rental = await api("/rentals", {
          method: "POST",
          body: { customer_id: customer.customer_id, sku: item.sku },
        });
        outcome.push({ ok: true, text: `Rented ${item.name}. Due ${rental.due_date}.` });
        basket.remove(item.sku);
      } catch (err) {
        outcome.push({ ok: false, text: err.message });
      }
    }
    setResults(outcome);
    setRenting(false);
  };

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-bold">Rental basket</h1>
      {customer && (
        <p className="text-sm text-slate-700">
          {customer.name} ({customer.membership_type}): up to {customer.max_items} items.
        </p>
      )}

      {basket.items.length === 0 ? (
        <Empty>Your basket is empty. <Link to="/" className="underline">Browse the catalogue</Link>.</Empty>
      ) : (
        <>
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {basket.items.map((item) => (
              <li key={item.sku} className="flex items-center justify-between gap-3 p-3">
                <span>{item.name}</span>
                <button type="button" onClick={() => basket.remove(item.sku)} disabled={renting}
                        aria-label={`Remove ${item.name} from the basket`}
                        className="rounded border border-slate-300 px-2 py-1 text-sm focus:outline-2 focus:outline-slate-900">
                  Remove
                </button>
              </li>
            ))}
          </ul>
          <div className="flex gap-3">
            <button type="button" onClick={checkout} disabled={renting || !customer}
                    className="rounded bg-slate-900 px-4 py-2 font-semibold text-white focus:outline-2 focus:outline-offset-2 focus:outline-slate-900 disabled:opacity-60">
              {renting ? "Renting..." : "Rent"}
            </button>
            <button type="button" onClick={basket.clear} disabled={renting}
                    className="rounded border border-slate-300 px-4 py-2 focus:outline-2 focus:outline-slate-900">
              Clear
            </button>
          </div>
        </>
      )}

      {/* Toasts: green for each rental the server made, red for each it refused. */}
      <div aria-live="polite" className="fixed inset-x-4 bottom-4 z-10 mx-auto max-w-md space-y-2">
        {results.map((r, i) => (
          <p key={i} role={r.ok ? "status" : "alert"}
             className={`rounded-lg p-3 shadow-lg ${r.ok ? "bg-green-700 text-white" : "bg-red-700 text-white"}`}>
            {r.text}
          </p>
        ))}
        {results.length > 0 && (
          <button type="button" onClick={() => setResults([])}
                  className="rounded bg-white px-3 py-1 text-sm shadow focus:outline-2 focus:outline-slate-900">
            Dismiss
          </button>
        )}
      </div>
    </section>
  );
}
