import { LoaderCircle } from "lucide-react";
import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";

import { cn } from "@/lib/cn";

type ButtonVariant =
  | "primary"
  | "secondary"
  | "ghost"
  | "ghost-on-dark"
  | "solid-on-dark"
  | "accent"
  | "danger";
type ButtonSize = "sm" | "md" | "lg";

interface ButtonStyleOptions {
  variant?: ButtonVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
}

const BASE_CLASSES =
  "inline-flex items-center justify-center gap-2 rounded-control font-medium whitespace-nowrap transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-60";

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  // The one main action on a screen.
  primary: "bg-primary text-on-primary hover:bg-primary-hover",
  // A supporting action next to a primary one.
  secondary:
    "border border-border-strong/40 bg-surface text-foreground hover:bg-surface-muted",
  // A low-emphasis action, e.g. in a header or a card footer.
  ghost: "text-foreground hover:bg-surface-muted",
  // The ghost style for use on a dark background.
  "ghost-on-dark": "text-white hover:bg-white/10",
  // The main action on a dark band. Fixed colours on purpose: the band is
  // dark in both light and dark mode, so this must not follow the theme.
  "solid-on-dark": "bg-white text-stone-900 hover:bg-white/90",
  // Reserved for "like" and match moments.
  accent: "bg-accent text-white hover:bg-accent-hover",
  // For confirming something destructive, such as blocking a person.
  danger: "bg-danger-solid text-white hover:bg-danger-solid-hover",
};

// Every size is at least 40px tall; md and lg meet the 44px touch target.
const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: "h-10 px-3.5 text-sm",
  md: "h-11 px-5 text-[0.9375rem]",
  lg: "h-12 px-6 text-base",
};

function buttonClasses({
  variant = "primary",
  size = "md",
  fullWidth = false,
}: ButtonStyleOptions): string {
  return cn(
    BASE_CLASSES,
    VARIANT_CLASSES[variant],
    SIZE_CLASSES[size],
    fullWidth && "w-full",
  );
}

interface ButtonProps extends ComponentProps<"button">, ButtonStyleOptions {
  /** Shows a spinner and blocks further clicks while work is in progress. */
  isLoading?: boolean;
  children: ReactNode;
}

export function Button({
  variant,
  size,
  fullWidth,
  isLoading = false,
  disabled,
  className,
  children,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || isLoading}
      aria-busy={isLoading || undefined}
      className={cn(buttonClasses({ variant, size, fullWidth }), className)}
      {...props}
    >
      {isLoading && (
        <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
      )}
      {children}
    </button>
  );
}

interface ButtonLinkProps
  extends ComponentProps<typeof Link>, ButtonStyleOptions {
  children: ReactNode;
}

/** A link that looks like a button. Use it when the action is navigation. */
export function ButtonLink({
  variant,
  size,
  fullWidth,
  className,
  children,
  ...props
}: ButtonLinkProps) {
  return (
    <Link
      className={cn(buttonClasses({ variant, size, fullWidth }), className)}
      {...props}
    >
      {children}
    </Link>
  );
}
