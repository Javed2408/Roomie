/** Calls to the backend health endpoints. */

import { ApiError, apiGet } from "@/services/api-client";
import type { DatabaseHealthResponse, HealthResponse } from "@/types/health";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isHealthResponse(value: unknown): value is HealthResponse {
  return (
    isRecord(value) &&
    value.status === "ok" &&
    typeof value.service === "string" &&
    typeof value.version === "string"
  );
}

function isDatabaseHealthResponse(
  value: unknown,
): value is DatabaseHealthResponse {
  return (
    isRecord(value) &&
    (value.status === "ok" || value.status === "unavailable") &&
    (value.database === "connected" || value.database === "unreachable")
  );
}

/** Ask the backend whether its own process is running. */
export async function fetchHealth(
  signal?: AbortSignal,
): Promise<HealthResponse> {
  const body = await apiGet("/health", { signal });
  if (!isHealthResponse(body)) {
    throw new Error("The API returned an unexpected response for /health.");
  }
  return body;
}

/**
 * Ask the backend whether it can reach PostgreSQL.
 *
 * The backend answers 503 when the database is down. That is still a valid,
 * meaningful answer, so it is returned as data rather than thrown.
 */
export async function fetchDatabaseHealth(
  signal?: AbortSignal,
): Promise<DatabaseHealthResponse> {
  let body: unknown;
  try {
    body = await apiGet("/health/db", { signal });
  } catch (error) {
    if (
      error instanceof ApiError &&
      error.status === 503 &&
      isDatabaseHealthResponse(error.body)
    ) {
      return error.body;
    }
    throw error;
  }

  if (!isDatabaseHealthResponse(body)) {
    throw new Error("The API returned an unexpected response for /health/db.");
  }
  return body;
}
