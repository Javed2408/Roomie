import type { Metadata } from "next";
import Link from "next/link";

import { SystemStatus } from "@/components/system-status";
import { Logo } from "@/components/ui/logo";

export const metadata: Metadata = { title: "System status" };

/**
 * A developer page: proves the browser can reach the backend and that the
 * backend can reach the database. (Built in Phase 0, when it was the home
 * page.)
 */
export default function StatusPage() {
  return (
    <main
      id="main"
      className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center gap-8 px-5 py-16"
    >
      <Logo />
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold">System status</h1>
        <p className="text-muted leading-relaxed">
          Checks that this page can reach the Roomie API, and that the API can
          reach its database.
        </p>
      </header>

      <SystemStatus />

      <Link
        href="/"
        className="text-primary hover:text-primary-hover self-start py-1 text-sm font-medium underline-offset-4 hover:underline"
      >
        Back to the home page
      </Link>
    </main>
  );
}
