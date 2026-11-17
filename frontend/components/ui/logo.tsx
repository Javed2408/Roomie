import Link from "next/link";

import { cn } from "@/lib/cn";

function LogoMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      aria-hidden="true"
      className={cn("size-8", className)}
    >
      <rect width="32" height="32" rx="9" className="fill-primary" />
      <path
        d="M8 15.5 16 9l8 6.5"
        fill="none"
        stroke="#fff"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="12.5" cy="20.5" r="2.5" fill="#fff" />
      <circle cx="19.5" cy="20.5" r="2.5" fill="#fff" />
    </svg>
  );
}

interface LogoProps {
  /** Where clicking the logo goes. */
  href?: string;
  className?: string;
}

/** The Roomie mark (two people under one roof) with the wordmark. */
export function Logo({ href = "/", className }: LogoProps) {
  return (
    <Link
      href={href}
      aria-label="Roomie home"
      className={cn("inline-flex items-center gap-2 rounded-lg", className)}
    >
      <LogoMark />
      <span className="font-display text-foreground text-xl font-semibold tracking-tight">
        roomie
      </span>
    </Link>
  );
}
