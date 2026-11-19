/**
 * The signed-in person's own account, as the backend returns it.
 * These mirror backend/app/schemas/account.py — keep the two in sync.
 */

import type { Society } from "@/types/society";

export interface SessionUser {
  id: string;
  email: string;
  role: "MEMBER" | "ADMIN";
  /** Only proves the address works. Not identity or student verification. */
  emailVerified: boolean;
}

export interface AccountProfile {
  fullName: string;
  collegeName: string;
  course: string | null;
  department: string | null;
  academicYear: number | null;
  bio: string | null;
  gender: string | null;
  genderVisible: boolean;
  profileCompleted: boolean;
  /** Your own photo's address, or null for initials. */
  photoUrl: string | null;
}

/** Every value is optional: `null` means "not answered". */
export interface AccountPreferences {
  minBudget: number | null;
  maxBudget: number | null;
  moveInDate: string | null;
  roomType: string | null;
  foodPreference: string | null;
  smokingPreference: string | null;
  drinkingPreference: string | null;
  sleepSchedule: string | null;
  cleanlinessLevel: string | null;
  socialPreference: string | null;
  guestFrequency: string | null;
}

export interface AccountSocietyPreference {
  society: Society;
  /** 1 is the most preferred. */
  priority: number;
  /**
   * False when the society has since left the directory (unverified or
   * switched off). It stays in the list so nothing disappears silently,
   * but it no longer counts and should be replaced.
   */
  available: boolean;
}

/** What a person sees for one of their OWN verifications. */
export type OwnVerificationStatus =
  "NOT_SUBMITTED" | "PENDING" | "APPROVED" | "REJECTED" | "NEEDS_RESUBMISSION";

export type VerificationDocumentType =
  | "GOVERNMENT_ID"
  | "STUDENT_ID"
  | "ENROLMENT_PROOF"
  | "OWNERSHIP_PROOF"
  | "RENTAL_AGREEMENT"
  | "LANDLORD_PERMISSION"
  | "OWNER_AUTHORIZATION";

/** Facts about an uploaded file. Never where it is stored. */
export interface VerificationDocument {
  id: string;
  documentType: VerificationDocumentType;
  originalFilename: string | null;
  contentType: string;
  sizeBytes: number;
  createdAt: string;
}

export interface OwnVerification {
  status: OwnVerificationStatus;
  submittedAt: string | null;
  documents: VerificationDocument[];
}

export interface Account {
  user: SessionUser;
  /** `null` until the person has entered their name and college. */
  profile: AccountProfile | null;
  preferences: AccountPreferences | null;
  societies: AccountSocietyPreference[];
  /** Two separate checks. Neither implies the other. */
  verifications: {
    identity: OwnVerification;
    student: OwnVerification;
  };
}
