import { Suspense, type ReactNode } from "react";

import {
  BottomNav,
  BottomNavFallback,
} from "@/components/app-shell/bottom-nav";
import {
  SidebarNav,
  SidebarNavFallback,
} from "@/components/app-shell/sidebar-nav";
import { EmailVerificationBanner } from "@/components/app-shell/email-verification-banner";
import { UserMenu } from "@/components/app-shell/user-menu";
import { Badge } from "@/components/ui/badge";
import { Logo } from "@/components/ui/logo";
import { SkipLink } from "@/components/ui/skip-link";

/**
 * The frame around every signed-in screen.
 *
 * - Large screens: a fixed sidebar on the left and a slim header.
 * - Phones and tablets: the header plus a tab bar at the bottom, where
 *   thumbs can reach it.
 */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-1">
      <SkipLink />

      <aside className="border-border bg-surface sticky top-0 hidden h-dvh w-64 shrink-0 flex-col border-r lg:flex">
        <div className="flex h-16 items-center px-5">
          <Logo href="/dashboard" />
        </div>
        <div className="flex-1 overflow-y-auto px-3 py-4">
          {/*
            The navigation highlights the current section, so it reads the
            page address. On pages whose address has a changeable part, such
            as /students/[id], that address is not known while Next.js
            pre-builds the page. Suspense lets it show the un-highlighted
            version for that instant instead of failing.
          */}
          <Suspense fallback={<SidebarNavFallback />}>
            <SidebarNav />
          </Suspense>
        </div>
        <p className="text-subtle border-border border-t px-5 py-4 text-xs leading-relaxed">
          Your profile, Discover and matches are saved to your account. Messages
          and accommodation still show sample data.
        </p>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-border bg-background/90 sticky top-0 z-20 border-b backdrop-blur">
          <div className="flex h-16 items-center justify-between gap-4 px-5 sm:px-8">
            <div className="flex items-center gap-3">
              <div className="lg:hidden">
                <Logo href="/dashboard" />
              </div>
              <Badge tone="warning">Early build</Badge>
            </div>
            <UserMenu />
          </div>
        </header>

        {/* pb-28 on small screens leaves room for the fixed bottom bar. */}
        <main id="main" className="flex-1 px-5 pt-6 pb-28 sm:px-8 lg:py-8">
          <div className="mx-auto w-full max-w-5xl">
            <EmailVerificationBanner />
            {children}
          </div>
        </main>
      </div>

      <Suspense fallback={<BottomNavFallback />}>
        <BottomNav />
      </Suspense>
    </div>
  );
}
