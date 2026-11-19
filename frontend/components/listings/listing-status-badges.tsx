import { Eye, EyeOff } from "lucide-react";

import { ModerationStatusBadge } from "@/components/listings/moderation-status-badge";
import { Badge } from "@/components/ui/badge";
import {
  LIFECYCLE_STATUS_LABELS,
  type ListingLifecycleStatus,
  type ListingModerationStatus,
} from "@/types/listing";

/**
 * The two separate statuses of one of your own listings, and whether it
 * is public right now. Lifecycle is yours to change; review is Roomie's.
 */
export function ListingStatusBadges({
  lifecycle,
  moderation,
  isPublic,
}: {
  lifecycle: ListingLifecycleStatus;
  moderation: ListingModerationStatus;
  isPublic: boolean;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Badge tone={lifecycle === "ACTIVE" ? "primary" : "neutral"}>
        {LIFECYCLE_STATUS_LABELS[lifecycle]}
      </Badge>
      {lifecycle !== "DRAFT" && <ModerationStatusBadge status={moderation} />}
      {isPublic ? (
        <Badge tone="success">
          <Eye aria-hidden="true" className="size-3.5" />
          Visible to students
        </Badge>
      ) : (
        <Badge>
          <EyeOff aria-hidden="true" className="size-3.5" />
          Not public
        </Badge>
      )}
    </div>
  );
}
