import {
  Ban,
  CircleCheck,
  CircleX,
  Clock,
  type LucideIcon,
} from "lucide-react";
import type { ComponentProps } from "react";

import { Badge } from "@/components/ui/badge";
import {
  MODERATION_STATUS_LABELS,
  type ListingModerationStatus,
} from "@/types/listing";

const STYLES: Record<
  ListingModerationStatus,
  { tone: ComponentProps<typeof Badge>["tone"]; icon: LucideIcon }
> = {
  PENDING: { tone: "warning", icon: Clock },
  APPROVED: { tone: "success", icon: CircleCheck },
  REJECTED: { tone: "danger", icon: CircleX },
  SUSPENDED: { tone: "danger", icon: Ban },
};

/**
 * Shows where a listing is in admin review. Only its creator and
 * administrators see this.
 *
 * "Approved" means a moderator allowed the post to be shown. It does NOT
 * mean the property or the poster has been verified; those are separate
 * checks with their own labels.
 */
export function ModerationStatusBadge({
  status,
}: {
  status: ListingModerationStatus;
}) {
  const { tone, icon: Icon } = STYLES[status];
  return (
    <Badge tone={tone}>
      <Icon aria-hidden="true" className="size-3.5" />
      {MODERATION_STATUS_LABELS[status]}
    </Badge>
  );
}
