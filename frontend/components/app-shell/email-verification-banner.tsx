"use client";

import { useState } from "react";

import { useSession } from "@/components/session/session-provider";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { resendVerificationEmail } from "@/services/auth";

/**
 * Shown on every signed-in page until the person has confirmed their
 * email address. Confirming the address is separate from identity and
 * student verification: it only proves the address works.
 */
export function EmailVerificationBanner() {
  const { account } = useSession();
  const [state, setState] = useState<"idle" | "sending" | "sent" | "failed">(
    "idle",
  );
  const [message, setMessage] = useState("");

  if (account.user.emailVerified) {
    return null;
  }

  async function resend() {
    setState("sending");
    const result = await resendVerificationEmail();
    if (result.ok) {
      setState("sent");
    } else {
      setMessage(result.message);
      setState("failed");
    }
  }

  return (
    <Alert tone="warning" title="Confirm your email address" className="mb-6">
      <p>
        We sent a link to{" "}
        <span className="font-medium break-all">{account.user.email}</span>.
        Open it to confirm the address is yours.
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => void resend()}
          isLoading={state === "sending"}
          disabled={state === "sent"}
        >
          Send the link again
        </Button>
        <span role="status">
          {state === "sent" && "A new link is on its way."}
          {state === "failed" && message}
        </span>
      </div>
    </Alert>
  );
}
