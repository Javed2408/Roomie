import { CircleAlert } from "lucide-react";

import { cn } from "@/lib/cn";

interface FieldMessageProps {
  id: string;
  hint?: string;
  error?: string;
}

/**
 * The line under a form control that shows its hint or its error.
 *
 * It is always rendered, even when empty (min-h-5 reserves its height), so
 * the rest of the form does not jump when an error appears.
 */
export function FieldMessage({ id, hint, error }: FieldMessageProps) {
  return (
    <p
      id={id}
      className={cn(
        "mt-1.5 min-h-5 text-sm",
        error ? "text-danger flex items-start gap-1.5" : "text-muted",
      )}
    >
      {error ? (
        <>
          <CircleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          <span>{error}</span>
        </>
      ) : (
        hint
      )}
    </p>
  );
}
