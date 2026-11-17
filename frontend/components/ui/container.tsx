import type { ComponentProps } from "react";

import { cn } from "@/lib/cn";

/**
 * Centres content and keeps a consistent gutter on every screen size.
 * Public pages use this so their left and right edges always line up.
 */
export function Container({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      className={cn("mx-auto w-full max-w-6xl px-5 sm:px-8", className)}
      {...props}
    />
  );
}
