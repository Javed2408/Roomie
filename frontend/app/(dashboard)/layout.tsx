import { AppShell } from "@/components/app-shell/app-shell";
import { RequireSession } from "@/components/session/session-provider";

/**
 * Shared frame for every signed-in page. "(dashboard)" is a route group, so
 * it does not appear in page addresses: the Discover page is "/discover".
 *
 * <RequireSession> sends visitors who are not signed in to the login page
 * and gives everything inside it the signed-in person's account.
 */
export default function DashboardLayout({ children }: LayoutProps<"/">) {
  return (
    <RequireSession>
      <AppShell>{children}</AppShell>
    </RequireSession>
  );
}
