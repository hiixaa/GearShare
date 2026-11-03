import { useBasket } from "../context/BasketContext";
import { useCustomer } from "../context/CustomerContext";
import { fullMessage } from "../lib/basketReducer";
import Navbar from "./Navbar";

/** Page frame: the navbar on top, the page itself passed in as `children`. */
export default function Layout({ children }) {
  const { customer } = useCustomer();
  const basket = useBasket();
  // Shown whenever the basket is full, because the add buttons are then disabled
  // and can't trigger the reducer's message themselves.
  const notice = basket.isFull ? fullMessage(customer) : basket.message;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <Navbar />
      <main className="mx-auto max-w-5xl space-y-4 px-4 py-6">
        {notice && (
          <p role="alert" className="rounded border border-amber-300 bg-amber-50 p-3 text-amber-900">
            {notice}
          </p>
        )}
        {children}
      </main>
    </div>
  );
}
