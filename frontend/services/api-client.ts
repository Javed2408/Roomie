/**
 * The single place where the frontend talks to the backend over HTTP.
 *
 * Feature services (services/auth.ts, services/account.ts, ...) call these
 * helpers instead of using `fetch` directly, so cookies, the anti-forgery
 * token and error handling work the same way everywhere.
 */

import { API_V1_URL } from "@/lib/config";

/** The backend answered, but with an error status (4xx or 5xx). */
export class ApiError extends Error {
  readonly status: number;
  /** A stable identifier from the backend, e.g. "not_authenticated". */
  readonly code: string;
  /** Extras from the backend, e.g. a list of what is still missing. */
  readonly details: unknown;
  /** The whole parsed response body, if the backend sent one. */
  readonly body: unknown;

  constructor(status: number, body: unknown) {
    const error = isRecord(body) && isRecord(body.error) ? body.error : null;
    super(
      typeof error?.message === "string"
        ? error.message
        : `The API responded with status ${status}.`,
    );
    this.name = "ApiError";
    this.status = status;
    this.code = typeof error?.code === "string" ? error.code : "unknown";
    this.details = error?.details ?? null;
    this.body = body;
  }
}

/** The request never reached the backend (it is offline, or blocked). */
export class NetworkError extends Error {
  constructor(cause: unknown) {
    super("Could not reach Roomie. Check your connection and try again.", {
      cause,
    });
    this.name = "NetworkError";
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

/*
 * The anti-forgery (CSRF) token for the current session.
 *
 * The backend hands it over when you sign in or when the session is
 * checked, and requires it back on every change. It is kept only in
 * memory: not in a cookie and not in localStorage, where other scripts
 * could read it. After a page reload it is fetched again.
 */
let csrfToken: string | null = null;

export function setCsrfToken(token: string | null): void {
  csrfToken = token;
}

interface RequestOptions {
  /** Lets the caller cancel the request, e.g. when a component unmounts. */
  signal?: AbortSignal;
}

async function parseBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return null;
  }
  return response.json();
}

async function request(
  method: "GET" | "POST" | "PUT" | "DELETE",
  path: string,
  body: unknown,
  options: RequestOptions,
): Promise<unknown> {
  const headers: Record<string, string> = { Accept: "application/json" };
  let payload: BodyInit | undefined;

  if (body instanceof FormData) {
    // The browser sets the multipart content type (with its boundary).
    payload = body;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  if (method !== "GET" && csrfToken) {
    headers["X-CSRF-Token"] = csrfToken;
  }

  let response: Response;
  try {
    response = await fetch(`${API_V1_URL}${path}`, {
      method,
      headers,
      body: payload,
      // Send and accept the session cookie, even though the API is on a
      // different port from the website.
      credentials: "include",
      signal: options.signal,
    });
  } catch (error) {
    // A cancelled request is not a network failure; let the caller see it.
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    throw new NetworkError(error);
  }

  const parsed = await parseBody(response);
  if (!response.ok) {
    throw new ApiError(response.status, parsed);
  }
  return parsed;
}

/*
 * Each helper returns the parsed JSON as `unknown` on purpose: the caller
 * must check its shape before using it, because data from the network
 * cannot be trusted to match our TypeScript types.
 */

export function apiGet(
  path: string,
  options: RequestOptions = {},
): Promise<unknown> {
  return request("GET", path, undefined, options);
}

export function apiPost(
  path: string,
  body?: unknown,
  options: RequestOptions = {},
): Promise<unknown> {
  return request("POST", path, body, options);
}

export function apiPut(
  path: string,
  body: unknown,
  options: RequestOptions = {},
): Promise<unknown> {
  return request("PUT", path, body, options);
}

export function apiDelete(
  path: string,
  options: RequestOptions = {},
): Promise<unknown> {
  return request("DELETE", path, undefined, options);
}

/** Turn any thrown error into a sentence that is safe to show a person. */
export function describeApiError(error: unknown): string {
  if (error instanceof ApiError || error instanceof NetworkError) {
    return error.message;
  }
  return "Something went wrong. Please try again.";
}
