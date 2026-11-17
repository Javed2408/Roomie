"use client"; // Error boundaries must be Client Components.

import { useEffect } from "react";

import { ErrorState } from "@/components/ui/states";

/** Shown when a public page crashes while rendering. */
export default function RootError({
  error,
  retry,
}: {
  error: unknown;
  retry: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main
      id="main"
      className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center px-5 py-16"
    >
      <ErrorState
        title="Something went wrong"
        description="This page could not be shown. Please try again."
        onRetry={retry}
      />
    </main>
  );
}
