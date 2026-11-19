/**
 * Student profile and roommate preference shapes.
 * These follow `student_profiles`, `roommate_preferences` and
 * `user_society_preferences` in DATABASE_SCHEMA.md.
 */

import type { Compatibility } from "@/types/discovery";
import type { Society } from "@/types/society";
import type { VerificationState } from "@/types/verification";

export type RoomType = "PRIVATE_ROOM" | "SHARED_ROOM" | "NO_PREFERENCE";
export type FoodPreference = "VEGETARIAN" | "NON_VEGETARIAN" | "VEGAN";
export type SleepSchedule = "EARLY_BIRD" | "NIGHT_OWL" | "FLEXIBLE";
export type CleanlinessLevel = "RELAXED" | "TIDY" | "VERY_TIDY";
export type SocialPreference = "QUIET" | "BALANCED" | "SOCIAL";
export type GuestFrequency = "RARELY" | "SOMETIMES" | "OFTEN";
export type HabitPreference = "NEVER" | "OCCASIONALLY" | "REGULARLY";

export const ROOM_TYPE_LABELS: Record<RoomType, string> = {
  PRIVATE_ROOM: "Private room",
  SHARED_ROOM: "Shared room",
  NO_PREFERENCE: "No preference",
};

export const FOOD_LABELS: Record<FoodPreference, string> = {
  VEGETARIAN: "Vegetarian",
  NON_VEGETARIAN: "Non-vegetarian",
  VEGAN: "Vegan",
};

export const SLEEP_LABELS: Record<SleepSchedule, string> = {
  EARLY_BIRD: "Early bird",
  NIGHT_OWL: "Night owl",
  FLEXIBLE: "Flexible sleeper",
};

export const CLEANLINESS_LABELS: Record<CleanlinessLevel, string> = {
  RELAXED: "Relaxed about mess",
  TIDY: "Tidy",
  VERY_TIDY: "Very tidy",
};

export const SOCIAL_LABELS: Record<SocialPreference, string> = {
  QUIET: "Prefers quiet",
  BALANCED: "Balanced",
  SOCIAL: "Social",
};

export const GUEST_LABELS: Record<GuestFrequency, string> = {
  RARELY: "Rarely has guests",
  SOMETIMES: "Sometimes has guests",
  OFTEN: "Often has guests",
};

export const HABIT_LABELS: Record<HabitPreference, string> = {
  NEVER: "Never",
  OCCASIONALLY: "Occasionally",
  REGULARLY: "Regularly",
};

export interface RoommatePreferences {
  /** Monthly budget per person, in whole rupees. */
  minBudget: number | null;
  maxBudget: number | null;
  /** ISO date, YYYY-MM-DD. */
  moveInDate: string | null;
  // Every habit is optional: null means the student did not answer.
  roomType: RoomType | null;
  foodPreference: FoodPreference | null;
  smoking: HabitPreference | null;
  drinking: HabitPreference | null;
  sleepSchedule: SleepSchedule | null;
  cleanliness: CleanlinessLevel | null;
  socialPreference: SocialPreference | null;
  guestFrequency: GuestFrequency | null;
}

export interface SocietyPreference {
  society: Society;
  /** 1 is the most preferred. */
  priority: number;
}

export interface StudentProfile {
  id: string;
  fullName: string;
  collegeName: string;
  course: string | null;
  department: string | null;
  academicYear: number | null;
  bio: string | null;
  /** Only present when the student chose to show it. */
  gender?: string | null;
  /** An access-checked photo address; `null` shows initials instead. */
  photoUrl: string | null;
  // Two separate checks. Neither implies the other.
  identityVerification: VerificationState;
  studentVerification: VerificationState;
  preferences: RoommatePreferences;
  /** Only societies students can currently see, most preferred first. */
  societyPreferences: SocietyPreference[];
}

/**
 * A profile as it appears in Discover, together with its compatibility
 * result. The score is a decision aid, never a guarantee (PRD 8.6).
 */
export interface DiscoveryCandidate {
  profile: StudentProfile;
  /** 0 to 100, or null when there was not enough to compare. */
  compatibilityScore: number | null;
  /** The main reasons for the score, strongest first. */
  positives: string[];
  /** Things that lowered the score. */
  cautions: string[];
  /** The full breakdown, when the score came from the scoring service. */
  compatibility?: Compatibility;
}
