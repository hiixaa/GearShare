import { useCallback, useEffect, useState } from "react";
import { api } from "../api";

/**
 * Fetch `path` and track {status: "loading" | "success" | "error", data, error}.
 *
 * Race-condition safety (Task 4.3): every time `path` changes, the cleanup
 * function ABORTS the previous request, so an old, slow response can never
 * overwrite a newer one. The aborted request's AbortError is ignored.
 * `retry()` re-runs the same request (the "Retry" button).
 */
export function useApi(path) {
  const [state, setState] = useState({ status: "loading", data: null, error: null });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (path == null) return undefined;
    const controller = new AbortController();
    setState({ status: "loading", data: null, error: null });
    api(path, { signal: controller.signal })
      .then((data) => setState({ status: "success", data, error: null }))
      .catch((error) => {
        if (error.name !== "AbortError") setState({ status: "error", data: null, error });
      });
    return () => controller.abort();
  }, [path, attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  return { ...state, retry };
}
