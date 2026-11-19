import { defineConfig, devices } from "@playwright/test";

import {
  ADMIN_PASSWORD,
  API_URL,
  BACKEND_PORT,
  BACKEND_URL,
  DATABASE_NAME,
  FRONTEND_PORT,
  FRONTEND_URL,
  OUTBOX_DIR,
  PHOTO_STORAGE_DIR,
  STORAGE_DIR,
} from "./e2e/settings";

/**
 * End-to-end tests drive a real browser through the real application.
 *
 * Playwright starts everything it needs itself: a backend and a frontend
 * on their own ports, using their own database. The only thing that must
 * already be running is PostgreSQL (`docker compose up -d --wait`).
 * Your own development servers and data are left alone.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  // More parallel browsers than this overloads a typical laptop running
  // the backend, the frontend and PostgreSQL too, and tests time out.
  workers: 4,
  // Fail CI if a test.only was left in by accident.
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  reporter: "list",
  use: {
    baseURL: FRONTEND_URL,
    trace: "on-first-retry",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
  webServer: [
    {
      command: "node e2e/start-backend.mjs",
      url: `${API_URL}/health`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        E2E_BACKEND_PORT: String(BACKEND_PORT),
        // A database of its own, so test accounts never mix with yours.
        POSTGRES_DB: DATABASE_NAME,
        CORS_ALLOWED_ORIGINS: FRONTEND_URL,
        FRONTEND_URL,
        // Emails are written here; the tests read them to follow links.
        EMAIL_BACKEND: "console",
        EMAIL_OUTBOX_DIR: OUTBOX_DIR,
        STORAGE_DIR,
        PHOTO_STORAGE_DIR,
        // Lets the tests sign in as the fixture administrator to approve
        // listings. Only ever applied to the throwaway test database.
        E2E_ADMIN_PASSWORD: ADMIN_PASSWORD,
        // The tests create many accounts from one machine in seconds,
        // which the real limits would (rightly) stop.
        RATE_LIMITS_ENABLED: "false",
      },
    },
    {
      // Tests run against a production build, as the Next.js docs recommend.
      // The development server compiles each page the first time it is
      // visited; with many tests arriving at once that caused random failures.
      command: `npm run build && npm run start -- --port ${FRONTEND_PORT}`,
      url: FRONTEND_URL,
      reuseExistingServer: false,
      timeout: 240_000,
      env: {
        NEXT_PUBLIC_API_BASE_URL: BACKEND_URL,
        NEXT_DIST_DIR: ".next-e2e",
      },
    },
  ],
});
