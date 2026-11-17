"use client";

import { DoorOpen, Users } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { ModerationStatusBadge } from "@/components/listings/moderation-status-badge";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button, ButtonLink } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { Listing } from "@/types/listing";

/**
 * One of the student's own listings, with its review status and actions.
 * Phase 1 shell: "Mark as filled" is remembered only by this component.
 */
export function MyListingRow({ listing }: { listing: Listing }) {
  const [isFilled, setIsFilled] = useState(false);
  const isExisting = listing.type === "EXISTING_ACCOMMODATION";
  // Only a post that is live can be marked as filled.
  const canMarkFilled =
    listing.moderationStatus === "APPROVED" &&
    listing.lifecycleStatus === "ACTIVE" &&
    !isFilled;

  return (
    <Card>
      <div className="flex flex-wrap items-center gap-2">
        {isExisting ? (
          <Badge tone="primary">
            <DoorOpen aria-hidden="true" className="size-3.5" />
            Room available
          </Badge>
        ) : (
          <Badge tone="info">
            <Users aria-hidden="true" className="size-3.5" />
            Looking to rent together
          </Badge>
        )}
        <ModerationStatusBadge status={listing.moderationStatus} />
        {isFilled && <Badge>Filled</Badge>}
      </div>

      <h2 className="mt-3 text-lg font-semibold">
        <Link
          href={`/accommodation/${listing.id}`}
          className="hover:text-primary underline-offset-4 hover:underline"
        >
          {listing.title}
        </Link>
      </h2>

      {listing.moderationStatus === "PENDING" && (
        <p className="text-muted mt-1 text-sm leading-relaxed">
          Waiting for review. It is not visible to other students yet.
        </p>
      )}
      {listing.moderationNote && (
        <Alert tone="danger" title="Why it was not approved" className="mt-3">
          {listing.moderationNote}
        </Alert>
      )}
      {isFilled && (
        <p role="status" className="text-muted mt-1 text-sm">
          Marked as filled (in this preview only).
        </p>
      )}

      <div className="mt-4 flex flex-wrap gap-3">
        <ButtonLink
          href={`/accommodation/${listing.id}`}
          variant="secondary"
          size="sm"
        >
          View
        </ButtonLink>
        {canMarkFilled && (
          <Button variant="ghost" size="sm" onClick={() => setIsFilled(true)}>
            Mark as filled
          </Button>
        )}
      </div>
    </Card>
  );
}
