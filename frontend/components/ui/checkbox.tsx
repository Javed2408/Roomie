import { CircleAlert } from "lucide-react";
import { useId, type ComponentProps, type ReactNode } from "react";

interface CheckboxProps extends Omit<
  ComponentProps<"input">,
  "type" | "className" | "children"
> {
  /** The text beside the box. Clicking it also toggles the box. */
  children: ReactNode;
  error?: string;
}

export function Checkbox({
  children,
  error,
  id,
  ...inputProps
}: CheckboxProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const errorId = `${inputId}-error`;

  return (
    <div className="space-y-1.5">
      {/* py-1 makes the whole row a comfortable touch target. */}
      <div className="flex items-start gap-3 py-1">
        <input
          id={inputId}
          type="checkbox"
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          className="accent-primary mt-0.5 size-5 shrink-0 cursor-pointer"
          {...inputProps}
        />
        <label
          htmlFor={inputId}
          className="text-muted cursor-pointer text-sm leading-relaxed"
        >
          {children}
        </label>
      </div>
      {error && (
        <p
          id={errorId}
          className="text-danger flex items-start gap-1.5 text-sm"
        >
          <CircleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          <span>{error}</span>
        </p>
      )}
    </div>
  );
}
