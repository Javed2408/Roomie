"use client";

import { ArrowLeft, Building2, Settings } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { PageSkeleton } from "@/components/app-shell/page-skeleton";
import { InterestPanel } from "@/components/listings/interest-panel";
import { ListingGallery } from "@/components/listings/listing-gallery";
import {
  ListingFullDetails,
  ListingLocation,
  ListingTypeBadge,
  PosterLine,
} from "@/components/listings/listing-card";
import { SafetyActions } from "@/components/safety/safety-actions";
import { Alert } from "@/components/ui/alert";
import { ButtonLink } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { ApiError, describeApiError } from "@/services/api-client";
import { fetchListing } from "@/services/listings";
import type { ListingView } from "@/types/listing";

type ViewState =
  | { status: "loading" }
  | { status: "missing" }
  | { status: "error"; message: string }
  | { status: "ready"; view: ListingView };

function BackLink() {
  return (
    <Link
      href="/accommodation"
      className="text-muted hover:text-foreground -ml-2 inline-flex h-10 items-center gap-1.5 rounded-lg px-2 text-sm font-medium transition-colors duration-150"
    >
      <ArrowLeft aria-hidden="true" className="size-4" />
      All accommodation
    </Link>
  );
}

/** One approved listing, as any signed-in member sees it. */
export function ListingDetailView({ id }: { id: string }) {
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{
    key: string;
    state: ViewState;
  } | null>(null);
  const key = `${id}|${attempt}`;

  useEffect(() => {
    const controller = new AbortController();
    fetchListing(id, controller.signal)
      .then((view) => setResult({ key, state: { status: "ready", view } }))
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
    // `key` combines the id and the retry count.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const state: ViewState =
    result && result.key === key ? result.state : { status: "loading" };

  if (state.status === "loading") {
    return <PageSkeleton />;
  }
  if (state.status === "missing") {
    return (
      <div className="mx-auto max-w-md">
        <BackLink />
        <EmptyState
          icon={Building2}
          title="This listing is not available"
          description="It may have been filled, closed or taken down for review, or the link may be wrong."
          action={
            <ButtonLink href="/accommodation">Browse accommodation</ButtonLink>
          }
          className="mt-4"
        />
      </div>
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

  const { listing, isYours, yourInterest } = state.view;
  const isExisting = listing.type === "EXISTING_ACCOMMODATION";
  const setInterest = (status: ListingView["yourInterest"]) =>
    setResult((current) =>
      current?.state.status === "ready"
        ? {
            ...current,
            state: {
              status: "ready",
              view: { ...current.state.view, yourInterest: status },
            },
          }
        : current,
    );

  return (
    <>
      <div className="mb-4">
        <BackLink />
      </div>

      <div className="grid gap-6 lg:grid-cols-3 lg:items-start">
        <div className="space-y-5 lg:col-span-2">
          {isExisting && (
            <ListingGallery photos={listing.photos} title={listing.title} />
          )}
          <Card padding="lg">
            <div className="space-y-2">
              <ListingTypeBadge listing={listing} />
              <h1 className="text-2xl leading-tight font-semibold">
                {listing.title}
              </h1>
              <ListingLocation listing={listing} />
            </div>
            <div className="mt-5">
              <ListingFullDetails listing={listing} />
            </div>
            <h2 className="mt-6 text-base font-semibold">About</h2>
            <p className="text-muted mt-1.5 text-sm leading-relaxed whitespace-pre-line">
              {listing.description}
            </p>
            {!isExisting && (
              <p className="text-subtle mt-4 text-xs leading-relaxed">
                This is a request from students who want to rent together. It is
                not an available property.
              </p>
            )}
            {isExisting && (
              <p className="text-subtle mt-4 text-xs leading-relaxed">
                Roomie shows the society and area only. The exact address is
                shared by the poster when you arrange a visit.
              </p>
            )}
          </Card>
        </div>

        <div className="space-y-5">
          <Card>
            <PosterLine listing={listing} />
          </Card>

          {isYours ? (
            <Card>
              <h2 className="text-lg font-semibold">This is your listing</h2>
              <p className="text-muted mt-1 text-sm">
                This is how other students see it.
              </p>
              <ButtonLink
                href={`/accommodation/mine/${listing.id}`}
                variant="secondary"
                className="mt-4"
                fullWidth
              >
                <Settings aria-hidden="true" className="size-4" />
                Manage listing
              </ButtonLink>
            </Card>
          ) : (
            <Card>
              <h2 className="mb-4 text-lg font-semibold">
                {isExisting ? "Interested in this room?" : "Want to join them?"}
              </h2>
              <InterestPanel
                listing={listing}
                status={yourInterest}
                onChange={setInterest}
              />
            </Card>
          )}

          <Alert tone="warning" title="Stay safe">
            Visit the place in person and never pay anything before you have.
            Roomie never collects rent, deposits or brokerage, and nobody may
            ask for money in its name.
          </Alert>

          {!isYours && (
            <Card>
              <h2 className="text-lg font-semibold">Something wrong?</h2>
              <p className="text-muted mt-1 mb-3 text-sm leading-relaxed">
                Report posts that look fake, misleading or unsafe.
              </p>
              <SafetyActions targetName="this listing" kind="listing" />
            </Card>
          )}
        </div>
      </div>
    </>
  );
}
