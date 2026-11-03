/** "1 of 2 available", or the display-item notice (R1). */
export default function AvailabilityBadge({ itemType, available, total }) {
  if (itemType === "Display") {
    return (
      <p className="text-sm font-medium text-slate-600">Display item: view in the shop only</p>
    );
  }
  const colour = available > 0 ? "bg-green-100 text-green-800" : "bg-amber-100 text-amber-900";
  return (
    <p className={`inline-block rounded px-2 py-0.5 text-sm font-medium ${colour}`}>
      {available} of {total} available
    </p>
  );
}
