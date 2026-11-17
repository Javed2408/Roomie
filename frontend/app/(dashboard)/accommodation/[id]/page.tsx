import { ArrowLeft } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { PageSkeleton } from "@/components/app-shell/page-skeleton";

import { InterestButton } from "@/components/listings/interest-button";
import { ListingCard } from "@/components/listings/listing-card";
import { ModerationStatusBadge } from "@/components/listings/moderation-status-badge";
import { SafetyActions } from "@/components/safety/safety-actions";
import { Alert } from "@/components/ui/alert";
import { Card } from "@/components/ui/card";
import { SampleDataBadge } from "@/components/ui/sample-data-badge";
import {
  CURRENT_USER_AS_POSTER,
  LISTINGS,
  MY_LISTINGS,
  findListing,
} from "@/lib/mock/listings";

export const metadata: Metadata = { title: "Listing" };

/** Lists the listings that exist, so their pages can be pre-built. */
export function generateStaticParams() {
  return [...LISTINGS, ...MY_LISTINGS].map((listing) => ({ id: listing.id }));
}

export default function ListingDetailPage({
  params,
}: PageProps<"/accommodation/[id]">) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      {params.then(({ id }) => (
        <ListingDetail id={id} />
      ))}
    </Suspense>
  );
}

/*
 * The id comes from the page address, which is only known when someone
 * actually visits. Next.js asks for that to happen inside <Suspense>, so
 * the page frame can appear instantly with a placeholder while the id is
 * read. params.then(...) hands the id to the real content once ready.
 */
function ListingDetail({ id }: { id: string }) {
  const listing = findListing(id);
  if (!listing) {
    notFound();
  }
  const isMine = listing.postedBy.id === CURRENT_USER_AS_POSTER.id;
  const isExisting = listing.type === "EXISTING_ACCOMMODATION";

  return (
    <>
      <div className="mb-4 flex items-center justify-between gap-3">
        <Link
          href={isMine ? "/accommodation/mine" : "/accommodation"}
          className="text-muted hover:text-foreground -ml-2 inline-flex h-10 items-center gap-1.5 rounded-lg px-2 text-sm font-medium transition-colors duration-150"
        >
          <ArrowLeft aria-hidden="true" className="size-4" />
          {isMine ? "My listings" : "All accommodation"}
        </Link>
        <SampleDataBadge />
      </div>

      <h1 className="sr-only">{listing.title}</h1>

      <div className="grid gap-5 lg:grid-cols-3 lg:items-start">
        <div className="lg:col-span-2">
          <ListingCard listing={listing} />
        </div>

        <div className="space-y-5">
          {isMine ? (
            <Card>
              <h2 className="text-lg font-semibold">Your listing</h2>
              <div className="mt-3">
                <ModerationStatusBadge status={listing.moderationStatus} />
              </div>
              {listing.moderationNote && (
                <p className="text-muted mt-3 text-sm leading-relaxed">
                  {listing.moderationNote}
                </p>
              )}
            </Card>
          ) : (
            <Card>
              <h2 className="mb-4 text-lg font-semibold">
                {isExisting ? "Interested in this room?" : "Want to join them?"}
              </h2>
              <InterestButton posterName={listing.postedBy.displayName} />
            </Card>
          )}

          <Alert tone="warning" title="Stay safe">
            Roomie has not verified this post. Meet in person, see the place
            yourself and never pay anything before you have. Roomie never
            collects payments, and nobody may ask for money in its name.
          </Alert>

          {!isMine && (
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
