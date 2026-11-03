import GearCard from "./GearCard";

/**
 * The grid of cards: one column on a phone (360 px), more on wider screens.
 * key = the SKU, which never changes for an item. With the array index as the
 * key, filtering the list would make React reuse the wrong card's state
 * (e.g. a "Join waiting list" message would jump to another item).
 */
export default function GearList({ items }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((item) => (
        <GearCard key={item.sku} item={item} />
      ))}
    </div>
  );
}
