import { Link, useLocation } from "react-router-dom";
import AvailabilityBadge from "./AvailabilityBadge";
import GearActions from "./GearActions";

/** One catalogue card. Everything it shows comes in through the `item` prop. */
export default function GearCard({ item }) {
  const location = useLocation();
  return (
    <article className="flex flex-col gap-2 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-lg font-semibold">
        {/* state.from = the current search, so "Back to results" can restore it */}
        <Link to={`/gear/${item.sku}`} state={{ from: location.search }}
              className="hover:underline focus:outline-2 focus:outline-slate-900">
          {item.name}
        </Link>
      </h2>
      <p className="text-sm text-slate-600">{item.tags.join(", ")}</p>
      <p className="text-sm">{item.category}</p>
      <AvailabilityBadge itemType={item.item_type} available={item.available} total={item.total} />
      <div className="mt-auto pt-2">
        <GearActions item={item} />
      </div>
    </article>
  );
}
