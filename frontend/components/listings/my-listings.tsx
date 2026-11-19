"use client";

import { Building2, Plus } from "lucide-react";
import { useEffect, useState } from "react";

import { MyListingRow } from "@/components/listings/my-listing-row";
import { ButtonLink } from "@/components/ui/button";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/states";
import { describeApiError } from "@/services/api-client";
import { fetchMyListings } from "@/services/listings";
import type { OwnListingSummary } from "@/types/listing";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; listings: OwnListingSummary[] };

/** Every listing you created, in any state. Only you see this list. */
export function MyListings() {
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{ key: number; state: State } | null>(
    null,
  );

  useEffect(() => {
    const controller = new AbortController();
    fetchMyListings(controller.signal)
      .then((listings) =>
        setResult({ key: attempt, state: { status: "ready", listings } }),
      )
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setResult({
            key: attempt,
            state: { status: "error", message: describeApiError(error) },
          });
        }
      });
    return () => controller.abort();
  }, [attempt]);

  const state: State =
    result?.key === attempt ? result.state : { status: "loading" };

  if (state.status === "loading") {
    return (
      <div className="space-y-4" aria-busy>
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
        <p role="status" className="sr-only">
          Loading your listings…
        </p>
      </div>
    );
  }
  if (state.status === "error") {
    return (
      <ErrorState
        title="Your listings could not load"
        description={state.message}
        onRetry={() => setAttempt((value) => value + 1)}
      />
    );
  }
  if (state.listings.length === 0) {
    return (
      <EmptyState
        icon={Building2}
        title="You have not posted anything yet"
        description="Post a room you have available, or tell others you are looking to rent together."
        action={
          <ButtonLink href="/accommodation/new">Post a listing</ButtonLink>
        }
      />
    );
  }
  return (
    <>
      <ul className="space-y-4">
        {state.listings.map((listing) => (
          <li key={listing.id}>
            <MyListingRow listing={listing} />
          </li>
        ))}
      </ul>
      <ButtonLink href="/accommodation/new" className="mt-6">
        <Plus aria-hidden="true" className="size-4" />
        Post a listing
      </ButtonLink>
    </>
  );
}
