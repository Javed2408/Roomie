import type { Metadata } from "next";
import { Suspense } from "react";

import { ResetPasswordForm } from "@/components/auth/reset-password-form";
import { Spinner } from "@/components/ui/states";

export const metadata: Metadata = { title: "Choose a new password" };

export default function ResetPasswordPage() {
  // The form reads the token from the page address, which is only known in
  // the browser. Suspense shows the spinner until that value is available.
  return (
    <Suspense fallback={<Spinner label="Checking your link" />}>
      <ResetPasswordForm />
    </Suspense>
  );
}
