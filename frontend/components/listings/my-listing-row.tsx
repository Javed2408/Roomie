import { ChevronRight, Hand, ImageOff, Users } from "lucide-react";
import Link from "next/link";

import { ListingStatusBadges } from "@/components/listings/listing-status-badges";
import { Card } from "@/components/ui/card";
import { formatTimestampDate } from "@/lib/format";
import type { OwnListingSummary } from "@/types/listing";

const AUTHORITY_TEXT: Record<string, string> = {
  NOT_SUBMITTED: "Evidence needed",
  PENDING: "Evidence waiting for review",
  APPROVED: "Listing authority verified",
  REJECTED: "Evidence not approved",
  NEEDS_RESUBMISSION: "More evidence needed",
};

/** One of your own listings, linking to where it is managed. */
export function MyListingRow({ listing }: { listing: OwnListingSummary }) {
  const isProperty = listing.type === "EXISTING_ACCOMMODATION";
  return (
    <Card padding="none" className="group relative">
      <div className="flex gap-4 p-4">
        <div className="bg-surface-muted text-subtle flex size-20 shrink-0 items-center justify-center overflow-hidden rounded-lg sm:size-24">
          {listing.coverPhoto ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={listing.coverPhoto.url}
              alt=""
              className="size-full object-cover"
            />
          ) : isProperty ? (
            <ImageOff aria-hidden="true" className="size-6" />
          ) : (
            <Users aria-hidden="true" className="size-6" />
          )}
        </div>
        <div className="min-w-0 flex-1 space-y-2">
          <ListingStatusBadges
            lifecycle={listing.lifecycleStatus}
            moderation={listing.moderationStatus}
            isPublic={listing.isPublic}
          />
          <h2 className="truncate text-base font-semibold">
            <Link
              href={`/accommodation/mine/${listing.id}`}
              className="group-hover:text-primary after:rounded-card focus-visible:after:ring-primary after:absolute after:inset-0 focus-visible:outline-none focus-visible:after:ring-2"
            >
              {listing.title}
            </Link>
          </h2>
          <p className="text-muted flex flex-wrap gap-x-3 gap-y-1 text-sm">
            <span>
              {isProperty ? "Room available" : "Looking to rent together"}
            </span>
            {listing.authorityStatus && (
              <span>{AUTHORITY_TEXT[listing.authorityStatus]}</span>
            )}
            <span>Updated {formatTimestampDate(listing.updatedAt)}</span>
          </p>
          {listing.moderationReason && (
            <p className="text-danger text-sm">{listing.moderationReason}</p>
          )}
          {listing.pendingInterests > 0 && (
            <p className="text-primary-strong flex items-center gap-1.5 text-sm font-medium">
              <Hand aria-hidden="true" className="size-4" />
              {listing.pendingInterests} waiting for your reply
            </p>
          )}
        </div>
        <ChevronRight
          aria-hidden="true"
          className="text-subtle size-5 shrink-0 self-center"
        />
      </div>
    </Card>
  );
}
