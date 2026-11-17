/**
 * Frontend configuration, read from environment variables.
 *
 * Next.js replaces `process.env.NEXT_PUBLIC_*` with the real value when it
 * builds the app, so the variable must be written out in full here (it cannot
 * be looked up by a computed name).
 */

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

if (!apiBaseUrl) {
  throw new Error(
    "NEXT_PUBLIC_API_BASE_URL is not set. Copy frontend/.env.example to " +
      "frontend/.env.local and restart the dev server.",
  );
}

/** Backend address without a trailing slash, e.g. "http://localhost:8000". */
export const API_BASE_URL = apiBaseUrl.replace(/\/+$/, "");

/** Base address for version 1 of the API. */
export const API_V1_URL = `${API_BASE_URL}/api/v1`;
