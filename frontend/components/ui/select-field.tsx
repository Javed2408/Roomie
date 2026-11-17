import { ChevronDown } from "lucide-react";
import { useId, type ComponentProps } from "react";

import { FieldMessage } from "@/components/ui/field-message";
import { cn } from "@/lib/cn";

export interface SelectOption {
  value: string;
  label: string;
}

interface SelectFieldProps extends Omit<
  ComponentProps<"select">,
  "className" | "children"
> {
  label: string;
  options: SelectOption[];
  /** Text of the empty first option, e.g. "Choose a society". */
  placeholder?: string;
  hint?: string;
  error?: string;
  className?: string;
}

/** A labelled drop-down. Uses the device's own picker, which works well on phones. */
export function SelectField({
  label,
  options,
  placeholder,
  hint,
  error,
  className,
  id,
  ...selectProps
}: SelectFieldProps) {
  const generatedId = useId();
  const selectId = id ?? generatedId;
  const messageId = `${selectId}-message`;

  return (
    <div className={className}>
      <label
        htmlFor={selectId}
        className="text-foreground mb-1.5 block text-sm font-medium"
      >
        {label}
      </label>
      <div className="relative">
        <select
          id={selectId}
          aria-invalid={error ? true : undefined}
          aria-describedby={error || hint ? messageId : undefined}
          className={cn(
            "rounded-control bg-surface text-foreground h-11 w-full appearance-none border pr-10 pl-3.5 text-base transition-colors duration-150",
            error
              ? "border-danger"
              : "border-border-strong hover:border-foreground",
          )}
          {...selectProps}
        >
          {placeholder !== undefined && <option value="">{placeholder}</option>}
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <ChevronDown
          aria-hidden="true"
          className="text-muted pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2"
        />
      </div>
      <FieldMessage id={messageId} hint={hint} error={error} />
    </div>
  );
}
