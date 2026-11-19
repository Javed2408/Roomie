import type { AppNotification } from "@/types/discovery";

/** Notifications about your own listing open its management page. */
const OWN_LISTING_TYPES = new Set([
  "LISTING_INTEREST",
  "LISTING_APPROVED",
  "LISTING_REJECTED",
  "LISTING_SUSPENDED",
  "AUTHORITY_NEEDS_ATTENTION",
]);

/** Where tapping a notification should take you. */
export function notificationHref(item: AppNotification): string {
  if (item.type === "NEW_MATCH") {
    return "/matches";
  }
  if (item.type === "INTEREST_ACCEPTED") {
    return "/accommodation/interests";
  }
  if (OWN_LISTING_TYPES.has(item.type) && item.referenceId) {
    return `/accommodation/mine/${encodeURIComponent(item.referenceId)}`;
  }
  return "/dashboard";
}
