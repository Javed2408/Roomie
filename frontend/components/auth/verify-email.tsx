"use client";

import { CircleAlert } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { AuthHeading } from "@/components/auth/auth-heading";
import { SuccessPanel } from "@/components/auth/success-panel";
import { ButtonLink } from "@/components/ui/button";
import { Spinner } from "@/components/ui/states";
import { verifyEmail } from "@/services/auth";

type Outcome = { state: "ok" } | { state: "failed"; message: string };

/**
 * Opened from the link in the confirmation email
 * (`/verify-email?token=...`). It sends the token to the backend once and
 * shows the result.
 */
export function VerifyEmail() {
  const token = useSearchParams().get("token");
  const [outcome, setOutcome] = useState<Outcome | null>(null);

  useEffect(() => {
    if (!token) {
      return;
    }
    let isCurrent = true;
    void verifyEmail(token).then((result) => {
      if (isCurrent) {
        setOutcome(
          result.ok
            ? { state: "ok" }
            : { state: "failed", message: result.message },
        );
      }
    });
    return () => {
      isCurrent = false;
    };
  }, [token]);

  if (!token || outcome?.state === "failed") {
    return (
      <>
        <span className="bg-danger-soft text-danger mb-5 flex size-12 items-center justify-center rounded-full">
          <CircleAlert aria-hidden="true" className="size-6" />
        </span>
        <AuthHeading
          title="This link did not work"
          description={
            outcome?.state === "failed"
              ? outcome.message
              : "The confirmation link is missing or incomplete."
          }
        />
        <p className="text-muted -mt-4 mb-6 text-sm leading-relaxed">
          Links can be used once and expire after two days. Log in and use “Send
          the link again” to get a new one.
        </p>
        <ButtonLink href="/login" size="lg" fullWidth>
          Go to log in
        </ButtonLink>
      </>
    );
  }

  if (outcome === null) {
    return <Spinner label="Confirming your email" />;
  }

  return (
    <SuccessPanel
      title="Email confirmed"
      actions={
        <ButtonLink href="/dashboard" size="lg" fullWidth>
          Continue
        </ButtonLink>
      }
    >
      <p>
        Thank you. Your email address is confirmed. This is separate from
        identity and student verification, which you can do from your profile.
      </p>
    </SuccessPanel>
  );
}
