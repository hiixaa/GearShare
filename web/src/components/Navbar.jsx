import { NavLink } from "react-router-dom";
import { useBasket } from "../context/BasketContext";
import { useCustomer } from "../context/CustomerContext";

const linkClass = ({ isActive }) =>
  `rounded px-2 py-1 hover:bg-slate-700 focus:outline-2 focus:outline-white ${
    isActive ? "bg-slate-700 font-semibold" : ""
  }`;

export default function Navbar() {
  const { customers, customer, setCustomerId, status } = useCustomer();
  const { items } = useBasket();

  return (
    <header className="bg-slate-900 text-white">
      <nav className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-3 gap-y-2 px-4 py-3">
        <NavLink to="/" className="mr-2 text-lg font-bold">
          GearShare Mini
        </NavLink>
        <NavLink to="/" end className={linkClass}>Catalogue</NavLink>
        <NavLink to="/me" className={linkClass}>My rentals</NavLink>
        <NavLink to="/basket" className={linkClass}>Basket ({items.length})</NavLink>
        <NavLink to="/admin/add" className={linkClass}>Add item</NavLink>

        <label className="ml-auto flex items-center gap-2 text-sm">
          <span>Customer</span>
          <select
            className="rounded bg-white px-2 py-1 text-slate-900"
            value={customer?.customer_id ?? ""}
            onChange={(e) => setCustomerId(e.target.value)}
            disabled={status !== "success"}
          >
            {status !== "success" && <option value="">(unavailable)</option>}
            {customers.map((c) => (
              <option key={c.customer_id} value={c.customer_id}>
                {c.name} ({c.membership_type})
              </option>
            ))}
          </select>
        </label>
      </nav>
    </header>
  );
}
