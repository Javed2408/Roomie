/**
 * Response shapes of the backend health endpoints.
 * These mirror backend/app/schemas/health.py — keep the two in sync.
 */

export interface HealthResponse {
  status: "ok";
  service: string;
  version: string;
}

export interface DatabaseHealthResponse {
  status: "ok" | "unavailable";
  database: "connected" | "unreachable";
}
