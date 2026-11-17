import type { ComponentProps } from "react";

import { cn } from "@/lib/cn";

type CardPadding = "none" | "md" | "lg";

const PADDING_CLASSES: Record<CardPadding, string> = {
  none: "",
  md: "p-5",
  lg: "p-6 sm:p-8",
};

interface CardProps extends ComponentProps<"div"> {
  padding?: CardPadding;
  /** Adds the soft shadow. Leave off for cards that sit inside other cards. */
  elevated?: boolean;
}

/** The standard white, rounded container used across the app. */
export function Card({
  padding = "md",
  elevated = false,
  className,
  ...props
}: CardProps) {
  return (
    <div
      className={cn(
        "rounded-card border-border bg-surface border",
        elevated && "shadow-card",
        PADDING_CLASSES[padding],
        className,
      )}
      {...props}
    />
  );
}
