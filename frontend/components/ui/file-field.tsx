import { useId, type ChangeEvent } from "react";

import { FieldMessage } from "@/components/ui/field-message";
import { cn } from "@/lib/cn";

interface FileFieldProps {
  label: string;
  name: string;
  /** File types offered by the file picker, e.g. ".pdf,.jpg,.png". */
  accept: string;
  onChange: (file: File | null) => void;
  hint?: string;
  error?: string;
  /** Change this value to clear the chosen file (after a successful upload). */
  resetKey?: number;
}

/** A labelled "choose a file" control. */
export function FileField({
  label,
  name,
  accept,
  onChange,
  hint,
  error,
  resetKey = 0,
}: FileFieldProps) {
  const id = useId();
  const messageId = `${id}-message`;

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    onChange(event.target.files?.[0] ?? null);
  }

  return (
    <div>
      <label
        htmlFor={id}
        className="text-foreground mb-1.5 block text-sm font-medium"
      >
        {label}
      </label>
      <input
        // A file input cannot be cleared by setting its value, so a new
        // key makes React replace it with a fresh, empty one.
        key={resetKey}
        id={id}
        name={name}
        type="file"
        accept={accept}
        onChange={handleChange}
        aria-invalid={error ? true : undefined}
        aria-describedby={error || hint ? messageId : undefined}
        className={cn(
          "rounded-control bg-surface text-foreground file:bg-surface-muted file:text-foreground block w-full cursor-pointer border text-sm transition-colors duration-150 file:mr-3 file:h-11 file:cursor-pointer file:border-0 file:px-4 file:text-sm file:font-medium",
          error
            ? "border-danger"
            : "border-border-strong hover:border-foreground",
        )}
      />
      <FieldMessage id={messageId} hint={hint} error={error} />
    </div>
  );
}
