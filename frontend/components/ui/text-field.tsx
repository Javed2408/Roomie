import { CircleAlert } from "lucide-react";
import { useId, type ComponentProps, type ReactNode } from "react";

import { cn } from "@/lib/cn";

interface TextFieldProps extends Omit<ComponentProps<"input">, "className"> {
  /** Always visible. A placeholder is never used in place of a label. */
  label: string;
  /** Extra guidance shown under the field. */
  hint?: string;
  /** When set, the field is marked invalid and this replaces the hint. */
  error?: string;
  /** A control placed inside the right edge, e.g. "show password". */
  trailing?: ReactNode;
  /** Shown at the right end of the label row, e.g. a "Forgot?" link. */
  labelAside?: ReactNode;
  className?: string;
}

export function TextField({
  label,
  hint,
  error,
  trailing,
  labelAside,
  className,
  id,
  ...inputProps
}: TextFieldProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const messageId = `${inputId}-message`;

  return (
    <div className={className}>
      <div className="mb-1.5 flex items-baseline justify-between gap-3">
        <label
          htmlFor={inputId}
          className="text-foreground block text-sm font-medium"
        >
          {label}
        </label>
        {labelAside}
      </div>
      <div className="relative">
        <input
          id={inputId}
          aria-invalid={error ? true : undefined}
          // Screen readers read this text out when the field receives focus.
          aria-describedby={error || hint ? messageId : undefined}
          className={cn(
            "rounded-control bg-surface text-foreground placeholder:text-subtle h-11 w-full border px-3.5 text-base transition-colors duration-150",
            error
              ? "border-danger"
              : "border-border-strong hover:border-foreground",
            trailing ? "pr-12" : undefined,
          )}
          {...inputProps}
        />
        {trailing && (
          <div className="absolute inset-y-0 right-0 flex items-center pr-1">
            {trailing}
          </div>
        )}
      </div>
      {/*
        This line is always present, even when empty (min-h-5 reserves its
        height). If it only appeared together with an error, the rest of the
        form would jump down the moment someone left a field, and a click
        aimed at the submit button could miss it.
      */}
      <p
        id={messageId}
        className={cn(
          "mt-1.5 min-h-5 text-sm",
          error ? "text-danger flex items-start gap-1.5" : "text-muted",
        )}
      >
        {error ? (
          <>
            <CircleAlert
              aria-hidden="true"
              className="mt-0.5 size-4 shrink-0"
            />
            <span>{error}</span>
          </>
        ) : (
          hint
        )}
      </p>
    </div>
  );
}
