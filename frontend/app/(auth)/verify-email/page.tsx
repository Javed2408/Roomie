import type { Metadata } from "next";
import { Suspense } from "react";

import { VerifyEmail } from "@/components/auth/verify-email";
import { Spinner } from "@/components/ui/states";

export const metadata: Metadata = { title: "Confirm your email" };

export default function VerifyEmailPage() {
  // The token is read from the page address, which is only known in the
  // browser. Suspense shows the spinner until it is available.
  return (
    <Suspense fallback={<Spinner label="Confirming your email" />}>
      <VerifyEmail />
    </Suspense>
  );
}
