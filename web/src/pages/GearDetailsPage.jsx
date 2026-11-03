import { Link, useLocation, useParams } from "react-router-dom";
import AvailabilityBadge from "../components/AvailabilityBadge";
import GearActions from "../components/GearActions";
import { ErrorState, Loading } from "../components/StatusViews";
import { useApi } from "../hooks/useApi";

const rupees = (n) => `₹${n}`;

export default function GearDetailsPage() {
  const { sku } = useParams();
  const location = useLocation();
  const backTo = `/${location.state?.from ?? ""}`;   // the search we came from
  const item = useApi(`/gear/${encodeURIComponent(sku)}`);

  return (
    <section className="space-y-4">
      <Link to={backTo} className="text-sm text-slate-700 underline focus:outline-2 focus:outline-slate-900">
        ← Back to results
      </Link>

      {item.status === "loading" && <Loading text="Loading item..." />}
      {item.status === "error" && (
        <ErrorState error={item.error} onRetry={item.error.status ? null : item.retry} />
      )}
      {item.status === "success" && (
        <article className="space-y-3 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h1 className="text-2xl font-bold">{item.data.name}</h1>
          <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
            <dt className="font-medium">SKU</dt><dd>{item.data.sku}</dd>
            <dt className="font-medium">Category</dt>
            <dd>{item.data.category}{item.data.top_category !== item.data.category && ` (${item.data.top_category})`}</dd>
            <dt className="font-medium">Tags</dt><dd>{item.data.tags.join(", ")}</dd>
            <dt className="font-medium">Type</dt><dd>{item.data.item_type}</dd>
            <dt className="font-medium">Weight</dt><dd>{item.data.weight_g} g</dd>
            <dt className="font-medium">Replacement price</dt><dd>{rupees(item.data.price)}</dd>
          </dl>
          <AvailabilityBadge itemType={item.data.item_type}
                             available={item.data.available} total={item.data.total} />
          <GearActions item={item.data} />
        </article>
      )}
    </section>
  );
}
