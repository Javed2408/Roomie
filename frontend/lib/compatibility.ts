/**
 * Turning a compatibility breakdown into the short lists a card shows.
 *
 * The backend does the scoring (backend/app/services/compatibility.py);
 * nothing here calculates a score. This only picks which of the backend's
 * own explanations to show as reasons for and against.
 */

import type { Compatibility } from "@/types/discovery";

/**
 * A factor this good is shown as a reason in favour, and one below WEAK as
 * a difference. The same thresholds as the backend's summary sentence
 * (STRONG and WEAK in backend/app/services/compatibility.py).
 */
export const STRONG_FACTOR = 75;
export const WEAK_FACTOR = 40;

export function reasonsFrom(compatibility: Compatibility): {
  positives: string[];
  cautions: string[];
} {
  const judged = compatibility.factors.filter(
    (factor): factor is typeof factor & { score: number } =>
      factor.score !== null,
  );
  return {
    positives: judged
      .filter((factor) => factor.score >= STRONG_FACTOR)
      .map((factor) => factor.explanation),
    cautions: judged
      .filter((factor) => factor.score < WEAK_FACTOR)
      .map((factor) => factor.explanation),
  };
}

/** "Food and room type" for the factors that could not be compared. */
export function unavailableLabels(compatibility: Compatibility): string[] {
  return compatibility.factors
    .filter((factor) => !factor.available)
    .map((factor) => factor.label);
}
