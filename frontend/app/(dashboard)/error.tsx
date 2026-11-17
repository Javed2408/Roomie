"use client"; // Error boundaries must be Client Components.

import { useEffect } from "react";

import { ErrorState } from "@/components/ui/states";

/**
 * Shown when a signed-in page crashes while rendering. The navigation stays
 * usable around it, and "Try again" re-renders the page.
 */
export default function DashboardError({
  error,
  retry,
}: {
  error: unknown;
  retry: () => void;
}) {
  useEffect(() => {
    // Keep the details for developers; an error-reporting service will
    // receive these later.
    console.error(error);
  }, [error]);

  return (
    <ErrorState
      title="This page hit a problem"
      description="Something went wrong while showing this page. Your information is safe. Please try again."
      onRetry={retry}
    />
  );
}
