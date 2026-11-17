"use client";

import { useEffect, useState } from "react";

import { API_BASE_URL } from "@/lib/config";
import { NetworkError } from "@/services/api-client";
import { fetchDatabaseHealth, fetchHealth } from "@/services/health";

type Check =
  | { state: "checking" }
  | { state: "ok"; detail: string }
  | { state: "failed"; detail: string };

interface Checks {
  api: Check;
  database: Check;
}

const CHECKING: Checks = {
  api: { state: "checking" },
  database: { state: "checking" },
};

function describeError(error: unknown): string {
  if (error instanceof NetworkError) {
    return `No response from ${API_BASE_URL}. Is the backend running?`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Something unexpected went wrong.";
}

async function checkApi(signal: AbortSignal): Promise<Check> {
  try {
    const health = await fetchHealth(signal);
    return { state: "ok", detail: `${health.service} v${health.version}` };
  } catch (error) {
    return { state: "failed", detail: describeError(error) };
  }
}

async function checkDatabase(signal: AbortSignal): Promise<Check> {
  try {
    const health = await fetchDatabaseHealth(signal);
    return health.database === "connected"
      ? { state: "ok", detail: "PostgreSQL is connected" }
      : { state: "failed", detail: "The API cannot reach PostgreSQL." };
  } catch (error) {
    return { state: "failed", detail: describeError(error) };
  }
}

const DOT_STYLES: Record<Check["state"], string> = {
  checking: "bg-border-strong animate-pulse",
  ok: "bg-success",
  failed: "bg-danger",
};

const STATE_LABELS: Record<Check["state"], string> = {
  checking: "Checking…",
  ok: "Connected",
  failed: "Unavailable",
};

function StatusRow({
  name,
  check,
  testId,
}: {
  name: string;
  check: Check;
  testId: string;
}) {
  return (
    <li
      className="flex items-start gap-3 px-4 py-3.5"
      data-testid={testId}
      data-state={check.state}
    >
      <span
        aria-hidden="true"
        className={`mt-1.5 size-2.5 shrink-0 rounded-full ${DOT_STYLES[check.state]}`}
      />
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-3">
          <span className="font-medium text-foreground">{name}</span>
          <span className="text-sm text-muted">
            {STATE_LABELS[check.state]}
          </span>
        </div>
        {check.state !== "checking" && (
          <p className="mt-0.5 text-sm break-words text-subtle">
            {check.detail}
          </p>
        )}
      </div>
    </li>
  );
}

/**
 * Calls the backend from the browser and shows whether the API and the
 * database are reachable. This is a developer aid for Phase 0, not a
 * user-facing feature.
 */
export function SystemStatus() {
  const [checks, setChecks] = useState<Checks>(CHECKING);
  // Increasing this number re-runs the effect below ("Check again").
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    async function runChecks() {
      const [api, database] = await Promise.all([
        checkApi(controller.signal),
        checkDatabase(controller.signal),
      ]);
      // Ignore results that arrive after the component was removed or a
      // newer check was started.
      if (!controller.signal.aborted) {
        setChecks({ api, database });
      }
    }

    void runChecks();
    return () => controller.abort();
  }, [attempt]);

  const isChecking =
    checks.api.state === "checking" || checks.database.state === "checking";

  function handleCheckAgain() {
    setChecks(CHECKING);
    setAttempt((current) => current + 1);
  }

  return (
    <section
      aria-labelledby="system-status-heading"
      className="rounded-card border border-border bg-surface"
    >
      <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
        <h2
          id="system-status-heading"
          className="text-sm font-semibold text-foreground"
        >
          System status
        </h2>
        <button
          type="button"
          onClick={handleCheckAgain}
          disabled={isChecking}
          className="rounded-md px-2.5 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-surface-muted disabled:cursor-not-allowed disabled:opacity-50"
        >
          Check again
        </button>
      </div>
      <ul className="divide-y divide-border" aria-live="polite">
        <StatusRow name="API" check={checks.api} testId="status-api" />
        <StatusRow
          name="Database"
          check={checks.database}
          testId="status-database"
        />
      </ul>
    </section>
  );
}
