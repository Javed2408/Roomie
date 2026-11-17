"use client";

import { Eye, EyeOff } from "lucide-react";
import { useLayoutEffect, useState, type ComponentProps } from "react";

import { TextField } from "@/components/ui/text-field";

type PasswordFieldProps = Omit<
  ComponentProps<typeof TextField>,
  "type" | "trailing"
>;

/** A password input with a button to reveal what was typed. */
export function PasswordField(props: PasswordFieldProps) {
  const [isVisible, setIsVisible] = useState(false);
  const Icon = isVisible ? EyeOff : Eye;

  // Go back to hiding the password when the page is navigated away from.
  // Next.js keeps hidden pages in memory, and a revealed password should
  // not still be revealed when someone returns.
  useLayoutEffect(() => {
    return () => setIsVisible(false);
  }, []);

  return (
    <TextField
      {...props}
      type={isVisible ? "text" : "password"}
      trailing={
        <button
          type="button"
          onClick={() => setIsVisible((current) => !current)}
          aria-label={isVisible ? "Hide password" : "Show password"}
          aria-pressed={isVisible}
          className="text-muted hover:text-foreground hover:bg-surface-muted flex size-10 items-center justify-center rounded-lg transition-colors duration-150"
        >
          <Icon aria-hidden="true" className="size-5" />
        </button>
      }
    />
  );
}
