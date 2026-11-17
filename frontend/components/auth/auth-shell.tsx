import { Check } from "lucide-react";
import type { ReactNode } from "react";

import { Logo } from "@/components/ui/logo";
import { SkipLink } from "@/components/ui/skip-link";

const POINTS = [
  "Matches based on budget, society and lifestyle",
  "Your exact address is never shown publicly",
  "Chat only with people you have matched with",
];

/**
 * The frame around every sign-in screen: the form on one side and, on
 * larger screens, a calm brand panel on the other.
 */
export function AuthShell({ children }: { children: ReactNode }) {
  return (
    <div className="grid min-h-dvh flex-1 lg:grid-cols-[5fr_6fr]">
      <SkipLink />

      <aside className="bg-primary-soft hidden flex-col justify-between p-12 lg:flex">
        <Logo />
        <div>
          <p className="font-display text-primary-strong text-3xl leading-tight font-semibold text-balance">
            Find people you can actually live with.
          </p>
          <ul className="mt-8 space-y-3">
            {POINTS.map((point) => (
              <li
                key={point}
                className="text-primary-strong flex items-start gap-3"
              >
                <Check aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
                {point}
              </li>
            ))}
          </ul>
        </div>
        <p className="text-primary-strong/80 text-sm">
          For students around SRM Kattankulathur.
        </p>
      </aside>

      <div className="flex flex-col px-5 py-6 sm:px-8">
        <div className="lg:hidden">
          <Logo />
        </div>
        <main
          id="main"
          className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center py-10"
        >
          {children}
        </main>
      </div>
    </div>
  );
}
