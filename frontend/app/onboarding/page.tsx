import type { Metadata } from "next";

import { OnboardingWizard } from "@/components/profile/onboarding-wizard";
import { RequireSession } from "@/components/session/session-provider";
import { Logo } from "@/components/ui/logo";
import { SkipLink } from "@/components/ui/skip-link";

export const metadata: Metadata = { title: "Set up your profile" };

/**
 * Shown after registering. It sits outside the signed-in app frame on
 * purpose: a new student should finish this before seeing the navigation.
 * Each step is saved as it is completed, so it can be resumed later.
 */
export default function OnboardingPage() {
  return (
    <>
      <SkipLink />
      <header className="border-border border-b">
        <div className="mx-auto flex h-16 w-full max-w-2xl items-center px-5">
          <Logo />
        </div>
      </header>
      <main id="main" className="mx-auto w-full max-w-2xl flex-1 px-5 py-8">
        <RequireSession>
          <OnboardingWizard />
        </RequireSession>
      </main>
    </>
  );
}
