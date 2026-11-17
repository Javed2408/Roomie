/*
 * Starts the backend for the browser tests. Playwright runs this file.
 *
 * It uses the Python environment in backend/.venv, rebuilds the test
 * database from empty (named by POSTGRES_DB, set in playwright.config.ts),
 * adds fictional test directory records, then starts the API.
 */

import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const backendDir = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../backend",
);
const python =
  process.platform === "win32"
    ? path.join(backendDir, ".venv", "Scripts", "python.exe")
    : path.join(backendDir, ".venv", "bin", "python");

if (!fs.existsSync(python)) {
  console.error(
    `Could not find ${python}. Set up the backend first (see the README).`,
  );
  process.exit(1);
}

// --reset: every run starts from an empty test database, so accounts made
// by earlier runs never appear in another run's Discover. (Refused for any
// database whose name does not end in _test or _e2e.)
const prepared = spawnSync(
  python,
  ["-m", "app.scripts.prepare_database", "--reset", "--test-fixtures"],
  { cwd: backendDir, stdio: "inherit" },
);
if (prepared.status !== 0) {
  console.error(
    "Could not prepare the test database. Is PostgreSQL running? " +
      "(docker compose up -d --wait)",
  );
  process.exit(prepared.status ?? 1);
}

const port = process.env.E2E_BACKEND_PORT ?? "8010";
const server = spawn(
  python,
  ["-m", "uvicorn", "app.main:app", "--port", port],
  { cwd: backendDir, stdio: "inherit" },
);

// Stop the API when Playwright stops this script.
for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => server.kill());
}
server.on("exit", (code) => process.exit(code ?? 0));
