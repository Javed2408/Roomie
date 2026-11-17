import { expect, test } from "@playwright/test";

/*
 * The system status page (built in Phase 0, moved from "/" to "/status").
 * The first test needs the real backend and PostgreSQL to be running.
 */

test("status page confirms the API and database are connected", async ({
  page,
}) => {
  await page.goto("/status");

  await expect(
    page.getByRole("heading", { name: "System status", level: 1 }),
  ).toBeVisible();
  await expect(page.getByTestId("status-api")).toHaveAttribute(
    "data-state",
    "ok",
  );
  await expect(page.getByTestId("status-database")).toHaveAttribute(
    "data-state",
    "ok",
  );
  await expect(page.getByTestId("status-database")).toContainText(
    "PostgreSQL is connected",
  );
});

test("status page explains when the backend cannot be reached", async ({
  page,
}) => {
  // Simulate the backend being offline by failing every call to the API.
  await page.route("**/api/v1/**", (route) => route.abort("connectionrefused"));

  await page.goto("/status");

  await expect(page.getByTestId("status-api")).toHaveAttribute(
    "data-state",
    "failed",
  );
  await expect(page.getByTestId("status-api")).toContainText(
    "Is the backend running?",
  );
});

test("status page reports a database outage separately from the API", async ({
  page,
}) => {
  // The API is up, but it answers 503 because it cannot reach PostgreSQL.
  await page.route("**/api/v1/health/db", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ status: "unavailable", database: "unreachable" }),
    }),
  );
  await page.route("**/api/v1/health", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "ok",
        service: "Roomie API",
        version: "0.1.0",
      }),
    }),
  );

  await page.goto("/status");

  await expect(page.getByTestId("status-api")).toHaveAttribute(
    "data-state",
    "ok",
  );
  await expect(page.getByTestId("status-database")).toHaveAttribute(
    "data-state",
    "failed",
  );
  await expect(page.getByTestId("status-database")).toContainText(
    "The API cannot reach PostgreSQL.",
  );
});
