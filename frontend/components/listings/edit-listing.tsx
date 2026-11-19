"use client";

import { ArrowLeft, Building2, Lock } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/app-shell/page-header";
import { PageSkeleton } from "@/components/app-shell/page-skeleton";
import { ListingForm } from "@/components/listings/listing-form";
import { ButtonLink } from "@/components/ui/button";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { ApiError, describeApiError } from "@/services/api-client";
import { fetchMyListing } from "@/services/listings";
import type { OwnListing } from "@/types/listing";

type State =
  | { status: "loading" }
  | { status: "missing" }
  | { status: "error"; message: string }
  | { status: "ready"; own: OwnListing };

/** Load one of your listings, then show the form filled in with it. */
export function EditListing({ id }: { id: string }) {
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{ key: string; state: State } | null>(
    null,
  );
  const key = `${id}|${attempt}`;

  useEffect(() => {
    const controller = new AbortController();
    fetchMyListing(id, controller.signal)
      .then((own) => setResult({ key, state: { status: "ready", own } }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        const missing =
          error instanceof ApiError &&
          (error.status === 404 || error.status === 422);
        setResult({
          key,
          state: missing
            ? { status: "missing" }
            : { status: "error", message: describeApiError(error) },
        });
      });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const state: State =
    result?.key === key ? result.state : { status: "loading" };

  if (state.status === "loading") {
    return <PageSkeleton />;
  }
  if (state.status === "missing") {
    return (
      <EmptyState
        icon={Building2}
        title="Listing not found"
        description="It may have been deleted, or the link may be wrong."
        action={<ButtonLink href="/accommodation/mine">My listings</ButtonLink>}
        className="mx-auto max-w-md"
      />
    );
  }
  if (state.status === "error") {
    return (
      <ErrorState
        title="This listing could not load"
        description={state.message}
        onRetry={() => setAttempt((value) => value + 1)}
        className="mx-auto max-w-md"
      />
    );
  }

  const { own } = state;
  return (
    <div className="mx-auto max-w-2xl">
      <Link
        href={`/accommodation/mine/${own.listing.id}`}
        className="text-muted hover:text-foreground mb-2 -ml-2 inline-flex h-10 items-center gap-1.5 rounded-lg px-2 text-sm font-medium transition-colors duration-150"
      >
        <ArrowLeft aria-hidden="true" className="size-4" />
        Back to the listing
      </Link>
      <PageHeader title="Edit listing" description={own.listing.title} />
      {own.canEdit ? (
        <ListingForm existing={own} />
      ) : (
        <EmptyState
          icon={Lock}
          title="This listing cannot be edited"
          description="Closed and suspended listings cannot be changed."
          action={
            <ButtonLink href={`/accommodation/mine/${own.listing.id}`}>
              Back to the listing
            </ButtonLink>
          }
        />
      )}
    </div>
  );
}
