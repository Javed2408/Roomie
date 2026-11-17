/** Helpers for showing the signed-in person's account on screen. */

import {
  CLEANLINESS_LABELS,
  FOOD_LABELS,
  GUEST_LABELS,
  HABIT_LABELS,
  ROOM_TYPE_LABELS,
  SLEEP_LABELS,
  SOCIAL_LABELS,
} from "@/types/profile";
import type { Account, OwnVerificationStatus } from "@/types/account";

/** Look a stored value up in a label map; `null` if absent or unknown. */
function label(labels: Record<string, string>, value: string | null) {
  return value === null ? null : (labels[value] ?? null);
}

export const GENDER_LABELS: Record<string, string> = {
  WOMAN: "Woman",
  MAN: "Man",
  NON_BINARY: "Non-binary",
};

/** The lifestyle answers as label/value pairs, skipping unanswered ones. */
export function lifestyleAnswers(
  account: Account,
): Array<{ label: string; value: string }> {
  const p = account.preferences;
  if (!p) {
    return [];
  }
  const rows: Array<[string, string | null]> = [
    ["Food", label(FOOD_LABELS, p.foodPreference)],
    ["Sleep", label(SLEEP_LABELS, p.sleepSchedule)],
    ["Cleanliness", label(CLEANLINESS_LABELS, p.cleanlinessLevel)],
    ["Social life", label(SOCIAL_LABELS, p.socialPreference)],
    ["Guests", label(GUEST_LABELS, p.guestFrequency)],
    ["Smoking", label(HABIT_LABELS, p.smokingPreference)],
    ["Alcohol", label(HABIT_LABELS, p.drinkingPreference)],
  ];
  return rows.flatMap(([name, value]) =>
    value === null ? [] : [{ label: name, value }],
  );
}

export function roomTypeLabel(account: Account): string | null {
  return label(ROOM_TYPE_LABELS, account.preferences?.roomType ?? null);
}

export interface ChecklistItem {
  id: string;
  label: string;
  isComplete: boolean;
}

/** What the profile still needs, worked out from the real saved data. */
export function profileChecklist(account: Account): ChecklistItem[] {
  const p = account.preferences;
  return [
    {
      id: "details",
      label: "Student details",
      isComplete: account.profile !== null,
    },
    {
      id: "budget",
      label: "Budget and move-in date",
      isComplete:
        p !== null &&
        p.minBudget !== null &&
        p.maxBudget !== null &&
        p.moveInDate !== null,
    },
    {
      id: "societies",
      label: "Preferred societies",
      // Only societies still in the directory count.
      isComplete: account.societies.some((item) => item.available),
    },
    {
      id: "lifestyle",
      label: "Lifestyle preferences",
      isComplete: lifestyleAnswers(account).length > 0,
    },
    {
      id: "published",
      label: "Profile published",
      isComplete: account.profile?.profileCompleted === true,
    },
  ];
}

/**
 * How a person's OWN verification status is worded. (Other people only
 * ever see "verified", "pending" or "not verified".)
 */
export const OWN_VERIFICATION_TEXT: Record<
  OwnVerificationStatus,
  { label: string; tone: "neutral" | "warning" | "success" | "danger" }
> = {
  NOT_SUBMITTED: { label: "Not submitted", tone: "neutral" },
  PENDING: { label: "Under review", tone: "warning" },
  APPROVED: { label: "Verified", tone: "success" },
  REJECTED: { label: "Not approved", tone: "danger" },
  NEEDS_RESUBMISSION: { label: "More information needed", tone: "danger" },
};
