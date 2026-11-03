import { useSearchParams } from "react-router-dom";
import GearList from "../components/GearList";
import { Empty, ErrorState, Loading } from "../components/StatusViews";
import { useApi } from "../hooks/useApi";
import { useDebounce } from "../hooks/useDebounce";

const SORTS = [
  { value: "name", label: "Name" },
  { value: "catalogue", label: "Category, heaviest first" },
  { value: "weight", label: "Weight (heaviest first)" },
];

const field = "rounded border border-slate-300 bg-white px-2 py-1.5";

export default function CataloguePage() {
  // The search lives in the URL (?q=drone&category=&sort=name), not in useState:
  // it survives opening an item and coming back ("Back to results", Task 4.5),
  // a page reload, and a shared link. See DECISIONS D32.
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const category = params.get("category") ?? "";
  const sort = params.get("sort") ?? "name";

  const update = (key, value) =>
    setParams((prev) => {
      const next = new URLSearchParams(prev);
      if (value) next.set(key, value);
      else next.delete(key);
      return next;
    }, { replace: true });   // typing must not add a history entry per letter

  const debouncedQ = useDebounce(q, 300);
  const query = new URLSearchParams({ q: debouncedQ.trim(), category, sort }).toString();
  const gear = useApi(`/gear?${query}`);
  const categories = useApi("/categories");

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-bold">Catalogue</h1>

      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col text-sm">
          Search
          <input type="search" className={field} value={q} placeholder="name or tag"
                 onChange={(e) => update("q", e.target.value)} />
        </label>
        <label className="flex flex-col text-sm">
          Category
          <select className={field} value={category} onChange={(e) => update("category", e.target.value)}>
            <option value="">All</option>
            {(categories.data ?? []).map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        <label className="flex flex-col text-sm">
          Sort
          <select className={field} value={sort} onChange={(e) => update("sort", e.target.value)}>
            {SORTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </label>
      </div>

      {gear.status === "loading" && <Loading text="Loading catalogue..." />}
      {gear.status === "error" && <ErrorState error={gear.error} onRetry={gear.retry} />}
      {gear.status === "success" && gear.data.length === 0 && (
        <Empty>No items match '{debouncedQ.trim()}'. Try a different word.</Empty>
      )}
      {gear.status === "success" && gear.data.length > 0 && (
        <>
          <p className="text-sm text-slate-600" aria-live="polite">
            {gear.data.length} {gear.data.length === 1 ? "result" : "results"}
          </p>
          <GearList items={gear.data} />
        </>
      )}
    </section>
  );
}
