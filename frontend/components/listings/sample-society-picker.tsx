"use client";

import { ArrowDown, ArrowUp, MapPin, X } from "lucide-react";

import { FieldMessage } from "@/components/ui/field-message";
import type { Society } from "@/types/society";

interface SampleSocietyPickerProps {
  label: string;
  name: string;
  /** The sample societies to choose from. */
  societies: Society[];
  /** Selected society ids, most preferred first. */
  value: string[];
  onChange: (value: string[]) => void;
  hint?: string;
  error?: string;
}

const ICON_BUTTON =
  "text-primary-strong hover:bg-surface flex size-10 shrink-0 items-center justify-center rounded-lg transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-40";

/**
 * A simple picker over a fixed list, for the SAMPLE listing form only.
 *
 * Listings still run on sample data until roadmap Phase 6, so this form
 * must not mix in societies from the real directory. Phase 6 replaces
 * this with the directory-backed SocietyPicker used by profiles.
 */
export function SampleSocietyPicker({
  label,
  name,
  societies,
  value,
  onChange,
  hint,
  error,
}: SampleSocietyPickerProps) {
  const messageId = `${name}-message`;
  const byId = new Map(societies.map((society) => [society.id, society]));

  function toggle(id: string) {
    onChange(
      value.includes(id) ? value.filter((item) => item !== id) : [...value, id],
    );
  }

  function move(index: number, direction: -1 | 1) {
    const moving = value[index];
    const displaced = value[index + direction];
    if (moving === undefined || displaced === undefined) {
      return;
    }
    const next = [...value];
    next[index] = displaced;
    next[index + direction] = moving;
    onChange(next);
  }

  return (
    <fieldset aria-describedby={error || hint ? messageId : undefined}>
      <legend className="text-foreground mb-2 text-sm font-medium">
        {label}
      </legend>

      {value.length > 0 && (
        <ol aria-label="Your order of preference" className="mb-4 space-y-2">
          {value.map((id, index) => {
            const societyName = byId.get(id)?.name ?? "A chosen society";
            return (
              <li
                key={id}
                className="bg-primary-soft rounded-control flex items-center gap-2 py-1.5 pr-1.5 pl-3"
              >
                <span className="text-primary-strong min-w-0 flex-1 text-sm font-medium">
                  {index + 1}. {societyName}
                </span>
                <button
                  type="button"
                  onClick={() => move(index, -1)}
                  disabled={index === 0}
                  aria-label={`Move ${societyName} up`}
                  className={ICON_BUTTON}
                >
                  <ArrowUp aria-hidden="true" className="size-4" />
                </button>
                <button
                  type="button"
                  onClick={() => move(index, 1)}
                  disabled={index === value.length - 1}
                  aria-label={`Move ${societyName} down`}
                  className={ICON_BUTTON}
                >
                  <ArrowDown aria-hidden="true" className="size-4" />
                </button>
                <button
                  type="button"
                  onClick={() => toggle(id)}
                  aria-label={`Remove ${societyName}`}
                  className={ICON_BUTTON}
                >
                  <X aria-hidden="true" className="size-4" />
                </button>
              </li>
            );
          })}
        </ol>
      )}

      <ul className="border-border divide-border rounded-control divide-y border">
        {societies.map((society) => (
          <li key={society.id}>
            <label className="hover:bg-surface-muted flex cursor-pointer items-center gap-3 px-3.5 py-3 transition-colors duration-150">
              <input
                type="checkbox"
                name={name}
                value={society.id}
                checked={value.includes(society.id)}
                onChange={() => toggle(society.id)}
                className="accent-primary size-5 shrink-0 cursor-pointer"
              />
              <span className="min-w-0">
                <span className="text-foreground block text-sm font-medium">
                  {society.name}
                </span>
                <span className="text-subtle flex items-center gap-1 text-xs">
                  <MapPin aria-hidden="true" className="size-3" />
                  {society.locality.name}
                </span>
              </span>
            </label>
          </li>
        ))}
      </ul>

      <FieldMessage id={messageId} hint={hint} error={error} />
    </fieldset>
  );
}
