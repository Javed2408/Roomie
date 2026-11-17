import { AuthShell } from "@/components/auth/auth-shell";

/**
 * Shared frame for the sign-in screens. The "(auth)" folder name is a route
 * group: it groups these pages under one layout without adding "/auth" to
 * their addresses, so the login page is simply "/login".
 */
export default function AuthLayout({ children }: LayoutProps<"/">) {
  return <AuthShell>{children}</AuthShell>;
}
