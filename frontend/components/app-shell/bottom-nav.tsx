"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/cn";
import { APP_NAV_ITEMS, isNavItemActive } from "@/lib/navigation";

const BOTTOM_NAV_ITEMS = APP_NAV_ITEMS.filter((item) => item.inBottomNav);

function BottomNavBar({ pathname }: { pathname: string | null }) {
  return (
    <nav
      aria-label="Main"
      className="border-border bg-surface fixed inset-x-0 bottom-0 z-30 border-t pb-[env(safe-area-inset-bottom)] lg:hidden"
    >
      <ul className="mx-auto flex max-w-md">
        {BOTTOM_NAV_ITEMS.map(({ href, label, shortLabel, icon: Icon }) => {
          const isActive = pathname !== null && isNavItemActive(pathname, href);
          return (
            <li key={href} className="min-w-0 flex-1">
              <Link
                href={href}
                aria-label={label}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "flex h-16 flex-col items-center justify-center gap-1 text-xs font-medium transition-colors duration-150",
                  isActive
                    ? "text-primary"
                    : "text-muted hover:text-foreground",
                )}
              >
                <span
                  className={cn(
                    "flex h-7 w-12 items-center justify-center rounded-full transition-colors duration-150",
                    isActive && "bg-primary-soft",
                  )}
                >
                  <Icon aria-hidden="true" className="size-5" />
                </span>
                <span aria-hidden="true">{shortLabel ?? label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

/**
 * The tab bar fixed to the bottom of the screen on phones and tablets.
 * `pb-[env(safe-area-inset-bottom)]` keeps it clear of the home indicator
 * on phones without a physical home button.
 */
export function BottomNav() {
  return <BottomNavBar pathname={usePathname()} />;
}

/** The same bar with nothing highlighted. See the note in app-shell.tsx. */
export function BottomNavFallback() {
  return <BottomNavBar pathname={null} />;
}
