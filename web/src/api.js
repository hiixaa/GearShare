// The ONLY place that talks to the HTTP API. Components never call fetch().
const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export const OFFLINE_MESSAGE = "Can't reach the rental server.";

/** An error answer from the API: {error, message}, plus the HTTP status. */
export class ApiError extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

/**
 * Call the API and return the JSON body.
 * - The server's own message is kept exactly (the server has the last word).
 * - A network failure (server down) becomes ApiError(0, "NetworkError", OFFLINE_MESSAGE).
 * - An aborted request rethrows the AbortError, so callers can ignore it.
 */
export async function api(path, { method = "GET", body, signal } = {}) {
  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      signal,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (err) {
    if (err.name === "AbortError") throw err;
    throw new ApiError(0, "NetworkError", OFFLINE_MESSAGE);
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(
      response.status,
      data?.error ?? "HTTPError",
      data?.message ?? `Request failed (${response.status}).`,
    );
  }
  return data;
}
