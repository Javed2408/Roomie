import { Card } from "@/components/ui/card";
import type { Compatibility } from "@/types/discovery";

/**
 * Every factor behind a score: what it scored, how much it counted, and
 * why. Factors that could not be compared are listed as such, and their
 * share is spread over the others, never counted as a mismatch.
 */
export function CompatibilityBreakdown({
  compatibility,
  name,
}: {
  compatibility: Compatibility;
  /** The other person's first name. */
  name: string;
}) {
  return (
    <Card>
      <h2 className="text-lg font-semibold">How this score was worked out</h2>
      <p className="text-muted mt-1 text-sm leading-relaxed">
        {compatibility.summary}
      </p>

      <ul className="mt-4 space-y-4" aria-label="Compatibility factors">
        {compatibility.factors.map((factor) => (
          <li key={factor.key}>
            <div className="flex items-baseline justify-between gap-3">
              <span className="text-foreground text-sm font-medium">
                {factor.label}
              </span>
              <span className="text-muted text-xs">
                {factor.available
                  ? `${factor.score} / 100 · counts ${formatShare(factor.effectiveWeight)}`
                  : "Not compared"}
              </span>
            </div>
            <div
              aria-hidden="true"
              className="bg-surface-muted mt-1.5 h-1.5 overflow-hidden rounded-full"
            >
              {factor.available && (
                <div
                  className="bg-primary h-full rounded-full"
                  style={{ width: `${factor.score ?? 0}%` }}
                />
              )}
            </div>
            <p className="text-muted mt-1.5 text-sm leading-relaxed">
              {factor.explanation}
            </p>
          </li>
        ))}
      </ul>

      <p className="text-subtle mt-5 text-xs leading-relaxed">
        The score compares what you and {name} said about budget, societies,
        habits, move-in date, room type and food. It is a guide to help you
        decide, not a guarantee that you will get along. Talk before you commit
        to living together.
      </p>
    </Card>
  );
}

function formatShare(percent: number): string {
  return `${Number.isInteger(percent) ? percent : percent.toFixed(1)}%`;
}
