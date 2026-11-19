/**
 * STAND-IN for backend calls that do not exist yet.
 *
 * Each function waits a moment and then succeeds, so screens can show their
 * loading and success states. Nothing is stored anywhere: refresh the page
 * and the change is gone. Each one is replaced by a real API call in the
 * roadmap phase named beside it.
 */

const SIMULATED_DELAY_MS = 600;

export type MockResult = { ok: true } | { ok: false; message: string };

function succeedAfterDelay(): Promise<MockResult> {
  return new Promise((resolve) =>
    setTimeout(() => resolve({ ok: true }), SIMULATED_DELAY_MS),
  );
}

/** Phase 8: record a report for moderators. */
export const submitReport = succeedAfterDelay;
