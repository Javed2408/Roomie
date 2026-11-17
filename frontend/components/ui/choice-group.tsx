import { useId } from "react";

import { FieldMessage } from "@/components/ui/field-message";
import type { SelectOption } from "@/components/ui/select-field";

interface ChoiceGroupProps {
  /** The question, e.g. "Sleep schedule". */
  label: string;
  /** Shared by the radio buttons so the browser treats them as one group. */
  name: string;
  options: SelectOption[];
  value: string;
  onChange: (value: string) => void;
  hint?: string;
  error?: string;
}

/**
 * A "pick one" question shown as a row of tappable pills.
 *
 * Underneath, these are ordinary radio buttons, so keyboard arrow keys and
 * screen readers work as people expect. The radio is invisible but stretched
 * over the whole pill, so a tap anywhere on the pill selects it.
 */
export function ChoiceGroup({
  label,
  name,
  options,
  value,
  onChange,
  hint,
  error,
}: ChoiceGroupProps) {
  const messageId = `${useId()}-message`;

  return (
    <fieldset aria-describedby={error || hint ? messageId : undefined}>
      <legend className="text-foreground mb-2 text-sm font-medium">
        {label}
      </legend>
      <div className="flex flex-wrap gap-2">
        {options.map((option) => (
          <label
            key={option.value}
            className="border-border-strong/40 bg-surface text-foreground hover:bg-surface-muted has-checked:border-primary has-checked:bg-primary has-checked:text-on-primary has-focus-visible:outline-primary relative flex h-10 cursor-pointer items-center rounded-full border px-4 text-sm font-medium transition-colors duration-150 has-focus-visible:outline-2 has-focus-visible:outline-offset-2"
          >
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={value === option.value}
              onChange={() => onChange(option.value)}
              className="absolute inset-0 cursor-pointer opacity-0"
            />
            {option.label}
          </label>
        ))}
      </div>
      <FieldMessage id={messageId} hint={hint} error={error} />
    </fieldset>
  );
}
