// Task 4.4: the same loading / error / empty look on every screen that fetches.

export function Loading({ text }) {
  return (
    <div role="status" className="flex items-center gap-3 py-8 text-slate-600">
      <span aria-hidden="true"
            className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-slate-900" />
      {text}
    </div>
  );
}

/** The error message (e.g. "Can't reach the rental server.") with a Retry button. */
export function ErrorState({ error, onRetry }) {
  return (
    <div role="alert" className="space-y-3 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
      <p>{error?.message ?? "Something went wrong."}</p>
      {onRetry && (
        <button type="button" onClick={onRetry}
                className="rounded bg-red-700 px-3 py-1.5 text-sm font-semibold text-white focus:outline-2 focus:outline-offset-2 focus:outline-red-900">
          Retry
        </button>
      )}
    </div>
  );
}

export function Empty({ children }) {
  return <p className="py-8 text-slate-600">{children}</p>;
}
