import { useId, type ComponentProps } from "react";

import { FieldMessage } from "@/components/ui/field-message";
import { cn } from "@/lib/cn";

interface TextAreaFieldProps extends Omit<
  ComponentProps<"textarea">,
  "className" | "value"
> {
  label: string;
  value: string;
  hint?: string;
  error?: string;
  /** Shows a "120 / 500" counter beside the label. */
  maxLength?: number;
  className?: string;
}

/** A labelled multi-line text box with an optional character counter. */
export function TextAreaField({
  label,
  value,
  hint,
  error,
  maxLength,
  className,
  id,
  rows = 4,
  ...textareaProps
}: TextAreaFieldProps) {
  const generatedId = useId();
  const textareaId = id ?? generatedId;
  const messageId = `${textareaId}-message`;

  return (
    <div className={className}>
      <div className="mb-1.5 flex items-baseline justify-between gap-3">
        <label
          htmlFor={textareaId}
          className="text-foreground block text-sm font-medium"
        >
          {label}
        </label>
        {maxLength !== undefined && (
          <span
            className={cn(
              "text-xs tabular-nums",
              value.length > maxLength ? "text-danger" : "text-subtle",
            )}
          >
            {value.length} / {maxLength}
          </span>
        )}
      </div>
      {/*
        maxLength is deliberately not passed to the <textarea>. Silently
        refusing extra characters (for example when pasting) is confusing;
        showing the count in red and an error explains what is wrong.
      */}
      <textarea
        id={textareaId}
        rows={rows}
        value={value}
        aria-invalid={error ? true : undefined}
        aria-describedby={error || hint ? messageId : undefined}
        className={cn(
          "rounded-control bg-surface text-foreground placeholder:text-subtle block w-full resize-y border px-3.5 py-2.5 text-base leading-relaxed transition-colors duration-150",
          error
            ? "border-danger"
            : "border-border-strong hover:border-foreground",
        )}
        {...textareaProps}
      />
      <FieldMessage id={messageId} hint={hint} error={error} />
    </div>
  );
}
