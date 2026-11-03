import { Empty, ErrorState, Loading } from "../components/StatusViews";
import { useCustomer } from "../context/CustomerContext";
import { useApi } from "../hooks/useApi";

const status = (days) => (days > 0 ? `OVERDUE (${days} ${days === 1 ? "day" : "days"})` : "On rental");

export default function MyRentalsPage() {
  const { customer } = useCustomer();
  const rentals = useApi(customer ? `/customers/${customer.customer_id}/rentals` : null);

  if (!customer) return <Loading text="Loading customers..." />;

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-bold">My rentals</h1>
      {rentals.status === "loading" && <Loading text="Loading your rentals..." />}
      {rentals.status === "error" && <ErrorState error={rentals.error} onRetry={rentals.retry} />}
      {rentals.status === "success" && (
        <>
          <p className="text-sm text-slate-700">
            {rentals.data.customer} ({rentals.data.membership_type}): {rentals.data.active.length} of{" "}
            {rentals.data.max_items} items on rental. Unpaid fines: ₹{rentals.data.unpaid_fines}
          </p>
          {rentals.data.active.length === 0 ? (
            <Empty>You have no items on rental.</Empty>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse bg-white text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-300">
                    <th scope="col" className="p-2">Rental</th>
                    <th scope="col" className="p-2">Item</th>
                    <th scope="col" className="p-2">Due</th>
                    <th scope="col" className="p-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {rentals.data.active.map((r) => (
                    <tr key={r.rental_id} className="border-b border-slate-200">
                      <td className="p-2">{r.rental_id}</td>
                      <td className="p-2">{r.item}</td>
                      <td className="p-2">{r.due_date}</td>
                      <td className={`p-2 ${r.days_overdue > 0 ? "font-semibold text-red-700" : ""}`}>
                        {status(r.days_overdue)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  );
}
