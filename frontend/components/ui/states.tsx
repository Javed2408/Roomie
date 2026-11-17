import { CircleAlert, LoaderCircle, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";

/*
 * The three states every data-driven screen needs besides "here is the data":
 * loading, empty and error. Using these shared components keeps those
 * moments consistent everywhere.
 */

/** A grey placeholder block shown while content loads. */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={cn("bg-surface-muted animate-pulse rounded-lg", className)}
    />
  );
}

/** A spinner with a label that screen readers announce. */
export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <span role="status" className="text-muted inline-flex items-center gap-2">
      <LoaderCircle aria-hidden="true" className="size-5 animate-spin" />
      <span className="text-sm">{label}…</span>
    </span>
  );
}

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  /** Usually one button or link that helps the person move forward. */
  action?: ReactNode;
  className?: string;
}

/** Shown when a list has nothing in it yet. Always suggests a next step. */
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "rounded-card border-border-strong/40 flex flex-col items-center border border-dashed px-6 py-12 text-center",
        className,
      )}
    >
      <span className="bg-primary-soft text-primary-strong flex size-12 items-center justify-center rounded-full">
        <Icon aria-hidden="true" className="size-6" />
      </span>
      <h2 className="mt-4 text-lg font-semibold">{title}</h2>
      <p className="text-muted mt-1.5 max-w-sm text-sm leading-relaxed">
        {description}
      </p>
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}

interface ErrorStateProps {
  title?: string;
  description?: string;
  /** When provided, a "Try again" button calls this. */
  onRetry?: () => void;
  className?: string;
}

/** Shown when something failed. Says what happened and offers a way out. */
export function ErrorState({
  title = "Something went wrong",
  description = "We could not load this just now. Please try again.",
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        "rounded-card border-border flex flex-col items-center border px-6 py-12 text-center",
        className,
      )}
    >
      <span className="bg-danger-soft text-danger flex size-12 items-center justify-center rounded-full">
        <CircleAlert aria-hidden="true" className="size-6" />
      </span>
      <h2 className="mt-4 text-lg font-semibold">{title}</h2>
      <p className="text-muted mt-1.5 max-w-sm text-sm leading-relaxed">
        {description}
      </p>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry} className="mt-6">
          Try again
        </Button>
      )}
    </div>
  );
}
