/**
 * Verification is never a single yes/no. Roomie has three independent
 * checks, and the interface must always say WHICH one it is talking about,
 * so one check is never mistaken for another.
 *
 * - IDENTITY: the person is who they say they are.
 * - STUDENT: the person is currently enrolled at an institution.
 * - LISTING_AUTHORITY: the person is allowed to offer one specific property
 *   (an owner, a tenant with permission, or an agent the owner has
 *   independently confirmed).
 *
 * They do not depend on each other. A property owner can pass IDENTITY and
 * LISTING_AUTHORITY without being a student; a student can pass IDENTITY
 * and STUDENT with no right to list a property.
 *
 * This mirrors the three verification tables in the backend. Evidence
 * documents are private and are never sent to the browser of anyone except
 * the uploader and authorised administrators.
 */

export type VerificationKind = "IDENTITY" | "STUDENT" | "LISTING_AUTHORITY";

export type VerificationState =
  "NOT_VERIFIED" | "PENDING" | "VERIFIED" | "REJECTED";

export const VERIFICATION_KIND_LABELS: Record<VerificationKind, string> = {
  IDENTITY: "Identity",
  STUDENT: "Student status",
  LISTING_AUTHORITY: "Listing authority",
};
