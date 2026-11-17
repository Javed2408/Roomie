"use client";

import { CircleCheck } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";

interface SuccessPanelProps {
  title: string;
  children: ReactNode;
  /** Links or buttons for what to do next. */
  actions: ReactNode;
}

/**
 * Replaces a form once it has been submitted successfully.
 *
 * When the form disappears, keyboard focus would otherwise be lost. Moving
 * focus to the heading makes screen readers announce the result and keeps
 * keyboard users in the right place.
 */
export function SuccessPanel({ title, children, actions }: SuccessPanelProps) {
  const headingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    headingRef.current?.focus();
  }, []);

  return (
    <div>
      <span className="bg-success-soft text-success flex size-12 items-center justify-center rounded-full">
        <CircleCheck aria-hidden="true" className="size-6" />
      </span>
      <h1
        ref={headingRef}
        tabIndex={-1}
        className="mt-5 text-2xl font-semibold outline-none sm:text-3xl"
      >
        {title}
      </h1>
      <div className="text-muted mt-2 space-y-3 leading-relaxed">
        {children}
      </div>
      <div className="mt-8 flex flex-col gap-3">{actions}</div>
    </div>
  );
}
