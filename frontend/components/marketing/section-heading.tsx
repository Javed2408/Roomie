import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

interface SectionHeadingProps {
  /** A short label above the title that names the section. */
  eyebrow?: string;
  title: string;
  description?: ReactNode;
  align?: "left" | "center";
  className?: string;
}

/** The consistent heading block used by every landing page section. */
export function SectionHeading({
  eyebrow,
  title,
  description,
  align = "left",
  className,
}: SectionHeadingProps) {
  return (
    <div
      className={cn(
        "max-w-2xl",
        align === "center" && "mx-auto text-center",
        className,
      )}
    >
      {eyebrow && (
        <p className="text-primary text-sm font-semibold tracking-wide uppercase">
          {eyebrow}
        </p>
      )}
      <h2 className="mt-2 text-2xl font-semibold text-balance sm:text-3xl">
        {title}
      </h2>
      {description && (
        <p className="text-muted mt-3 text-base leading-relaxed text-pretty sm:text-lg">
          {description}
        </p>
      )}
    </div>
  );
}
