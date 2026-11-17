"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/cn";
import { APP_NAV_ITEMS, isNavItemActive } from "@/lib/navigation";

function SidebarNavList({ pathname }: { pathname: string | null }) {
  return (
    <nav aria-label="Main">
      <ul className="space-y-1">
        {APP_NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const isActive = pathname !== null && isNavItemActive(pathname, href);
          return (
            <li key={href}>
              <Link
                href={href}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "rounded-control flex h-11 items-center gap-3 px-3 text-[0.9375rem] font-medium transition-colors duration-150",
                  isActive
                    ? "bg-primary-soft text-primary-strong"
                    : "text-muted hover:bg-surface-muted hover:text-foreground",
                )}
              >
                <Icon aria-hidden="true" className="size-5 shrink-0" />
                {label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

/** The vertical section list shown in the sidebar on large screens. */
export function SidebarNav() {
  return <SidebarNavList pathname={usePathname()} />;
}

/**
 * The same list with nothing highlighted. Shown for the instant before the
 * current address is known (see the Suspense note in app-shell.tsx).
 */
export function SidebarNavFallback() {
  return <SidebarNavList pathname={null} />;
}
