import { Check, CircleHelp, Minus } from "lucide-react";

import { joinWords } from "@/lib/format";

const RING_RADIUS = 20;
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;

interface CompatibilityScoreProps {
  /** 0 to 100, or null when there was not enough to compare. */
  score: number | null;
  positives: string[];
  cautions: string[];
  /** Factors that could not be compared, e.g. ["Food", "Room type"]. */
  unavailable?: string[];
}

/**
 * Shows the score together with the reasons behind it. The reasons matter
 * as much as the number: the PRD requires matching to be explainable, and
 * the score is a decision aid rather than a promise.
 */
export function CompatibilityScore({
  score,
  positives,
  cautions,
  unavailable = [],
}: CompatibilityScoreProps) {
  const clamped = score === null ? 0 : Math.min(100, Math.max(0, score));
  const filledLength = (clamped / 100) * RING_CIRCUMFERENCE;

  return (
    <div className="bg-primary-soft rounded-control flex items-start gap-4 p-4">
      <div className="relative size-14 shrink-0">
        <svg
          viewBox="0 0 48 48"
          aria-hidden="true"
          className="size-14 -rotate-90"
        >
          <circle
            cx="24"
            cy="24"
            r={RING_RADIUS}
            fill="none"
            strokeWidth="5"
            className="stroke-surface"
          />
          <circle
            cx="24"
            cy="24"
            r={RING_RADIUS}
            fill="none"
            strokeWidth="5"
            strokeLinecap="round"
            strokeDasharray={`${filledLength} ${RING_CIRCUMFERENCE}`}
            className="stroke-primary"
          />
        </svg>
        <span className="font-display text-primary-strong absolute inset-0 flex items-center justify-center text-base font-semibold">
          {score === null ? "–" : clamped}
        </span>
      </div>

      <div className="min-w-0">
        <p className="text-primary-strong text-sm font-semibold">
          {score === null
            ? "Not enough to compare yet"
            : `${clamped}% compatibility`}
        </p>
        <ul className="mt-1.5 space-y-1 text-sm">
          {positives.map((reason) => (
            <li key={reason} className="text-foreground flex items-start gap-2">
              <Check
                aria-hidden="true"
                className="text-primary mt-0.5 size-4 shrink-0"
              />
              {reason}
            </li>
          ))}
          {cautions.map((reason) => (
            <li key={reason} className="text-muted flex items-start gap-2">
              <Minus aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
              {reason}
            </li>
          ))}
          {unavailable.length > 0 && (
            <li className="text-subtle flex items-start gap-2">
              <CircleHelp
                aria-hidden="true"
                className="mt-0.5 size-4 shrink-0"
              />
              Not compared: {joinWords(unavailable).toLowerCase()}
            </li>
          )}
        </ul>
      </div>
    </div>
  );
}
