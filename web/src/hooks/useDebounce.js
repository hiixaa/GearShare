import { useEffect, useState } from "react";

/** The value, but only after it has stopped changing for `delay` ms (Task 4.3). */
export function useDebounce(value, delay = 300) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);   // typing again cancels the pending update
  }, [value, delay]);
  return debounced;
}
