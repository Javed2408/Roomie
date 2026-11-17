import { CircleDashed, Clock, ShieldCheck } from "lucide-react";

import { cn } from "@/lib/cn";
import {
  VERIFICATION_KIND_LABELS,
  type VerificationKind,
  type VerificationState,
} from "@/types/verification";

interface VerificationStatusProps {
  kind: VerificationKind;
  state: VerificationState;
  className?: string;
}

/**
 * States one specific check and its result, e.g. "Identity: not verified".
 *
 * Rules this component enforces by design:
 * - The kind of check is always written out. There is no bare "Verified"
 *   tick that could be read as covering something it does not.
 * - Only a real VERIFIED state gets the green shield.
 * - A rejected check is shown to other people as "not verified"; the reason
 *   is private to the person and to administrators.
 */
export function VerificationStatus({
  kind,
  state,
  className,
}: VerificationStatusProps) {
  const label = VERIFICATION_KIND_LABELS[kind];

  if (state === "VERIFIED") {
    return (
      <span
        className={cn(
          "text-success inline-flex items-center gap-1.5 text-sm font-medium",
          className,
        )}
      >
        <ShieldCheck aria-hidden="true" className="size-4 shrink-0" />
        {label} verified
      </span>
    );
  }

  if (state === "PENDING") {
    return (
      <span
        className={cn(
          "text-warning inline-flex items-center gap-1.5 text-sm",
          className,
        )}
      >
        <Clock aria-hidden="true" className="size-4 shrink-0" />
        {label}: review pending
      </span>
    );
  }

  return (
    <span
      className={cn(
        "text-muted inline-flex items-center gap-1.5 text-sm",
        className,
      )}
    >
      <CircleDashed aria-hidden="true" className="size-4 shrink-0" />
      {label}: not verified
    </span>
  );
}
