/**
 * Turning backend responses into the frontend's typed shapes.
 *
 * The backend writes field names with underscores (`full_name`); the
 * frontend uses camelCase (`fullName`). These functions convert, and they
 * check as they go: if the backend ever sends something unexpected, the
 * app shows a clear error here rather than misbehaving somewhere else.
 */

import type {
  Account,
  AccountPreferences,
  AccountProfile,
  OwnVerification,
  OwnVerificationStatus,
  SessionUser,
  VerificationDocument,
  VerificationDocumentType,
} from "@/types/account";
import { reasonsFrom } from "@/lib/compatibility";
import { API_BASE_URL } from "@/lib/config";
import type {
  AreaOverlap,
  Compatibility,
  Decision,
  DecisionResult,
  DiscoveryPage,
  FactorKey,
  MatchSummary,
  NotificationList,
  StudentView,
} from "@/types/discovery";
import {
  CLEANLINESS_LABELS,
  FOOD_LABELS,
  GUEST_LABELS,
  HABIT_LABELS,
  ROOM_TYPE_LABELS,
  SLEEP_LABELS,
  SOCIAL_LABELS,
  type DiscoveryCandidate,
  type StudentProfile,
} from "@/types/profile";
import type {
  CommunityType,
  DirectoryLocality,
  DirectorySociety,
  Society,
} from "@/types/society";
import type { VerificationState } from "@/types/verification";

/**
 * Turn an API path such as "/api/v1/students/1/photo" into a full address
 * the browser can load. The backend never sends storage locations, only
 * these access-checked API paths.
 */
export function apiAddress(path: string | null): string | null {
  if (path === null) {
    return null;
  }
  if (!path.startsWith("/api/")) {
    throw new UnexpectedResponseError("photo address");
  }
  return `${API_BASE_URL}${path}`;
}

export class UnexpectedResponseError extends Error {
  constructor(what: string) {
    super(`Roomie sent an unexpected response (${what}). Please try again.`);
    this.name = "UnexpectedResponseError";
  }
}

export type Json = Record<string, unknown>;

export function record(value: unknown, what: string): Json {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new UnexpectedResponseError(what);
  }
  return value as Json;
}

export function text(value: unknown, what: string): string {
  if (typeof value !== "string") {
    throw new UnexpectedResponseError(what);
  }
  return value;
}

export function optionalText(value: unknown, what: string): string | null {
  return value === null || value === undefined ? null : text(value, what);
}

export function optionalNumber(value: unknown, what: string): number | null {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value !== "number") {
    throw new UnexpectedResponseError(what);
  }
  return value;
}

export function list(value: unknown, what: string): unknown[] {
  if (!Array.isArray(value)) {
    throw new UnexpectedResponseError(what);
  }
  return value;
}

export function parseUser(value: unknown): SessionUser {
  const user = record(value, "user");
  return {
    id: text(user.id, "user.id"),
    email: text(user.email, "user.email"),
    role: user.role === "ADMIN" ? "ADMIN" : "MEMBER",
    emailVerified: user.email_verified === true,
  };
}

export function parseSession(value: unknown): {
  user: SessionUser;
  csrfToken: string;
} {
  const session = record(value, "session");
  return {
    user: parseUser(session.user),
    csrfToken: text(session.csrf_token, "session.csrf_token"),
  };
}

export function parseSociety(value: unknown): Society {
  const society = record(value, "society");
  const locality = record(society.locality, "society.locality");
  return {
    id: text(society.id, "society.id"),
    name: text(society.name, "society.name"),
    locality: {
      id: text(locality.id, "locality.id"),
      name: text(locality.name, "locality.name"),
      city: text(locality.city, "locality.city"),
    },
  };
}

function parseProfile(value: unknown): AccountProfile | null {
  if (value === null) {
    return null;
  }
  const profile = record(value, "profile");
  return {
    fullName: text(profile.full_name, "profile.full_name"),
    collegeName: text(profile.college_name, "profile.college_name"),
    course: optionalText(profile.course, "profile.course"),
    department: optionalText(profile.department, "profile.department"),
    academicYear: optionalNumber(
      profile.academic_year,
      "profile.academic_year",
    ),
    bio: optionalText(profile.bio, "profile.bio"),
    gender: optionalText(profile.gender, "profile.gender"),
    genderVisible: profile.gender_visible === true,
    profileCompleted: profile.profile_completed === true,
    photoUrl: apiAddress(optionalText(profile.photo_url, "profile.photo_url")),
  };
}

function parsePreferences(value: unknown): AccountPreferences | null {
  if (value === null) {
    return null;
  }
  const p = record(value, "preferences");
  return {
    minBudget: optionalNumber(p.min_budget, "preferences.min_budget"),
    maxBudget: optionalNumber(p.max_budget, "preferences.max_budget"),
    moveInDate: optionalText(p.move_in_date, "preferences.move_in_date"),
    roomType: optionalText(p.room_type, "preferences.room_type"),
    foodPreference: optionalText(p.food_preference, "preferences.food"),
    smokingPreference: optionalText(
      p.smoking_preference,
      "preferences.smoking",
    ),
    drinkingPreference: optionalText(
      p.drinking_preference,
      "preferences.drinking",
    ),
    sleepSchedule: optionalText(p.sleep_schedule, "preferences.sleep"),
    cleanlinessLevel: optionalText(
      p.cleanliness_level,
      "preferences.cleanliness",
    ),
    socialPreference: optionalText(p.social_preference, "preferences.social"),
    guestFrequency: optionalText(p.guest_frequency, "preferences.guests"),
  };
}

const OWN_STATUSES: OwnVerificationStatus[] = [
  "NOT_SUBMITTED",
  "PENDING",
  "APPROVED",
  "REJECTED",
  "NEEDS_RESUBMISSION",
];

function parseDocument(value: unknown): VerificationDocument {
  const document = record(value, "document");
  return {
    id: text(document.id, "document.id"),
    documentType: text(
      document.document_type,
      "document.document_type",
    ) as VerificationDocumentType,
    originalFilename: optionalText(document.original_filename, "document.name"),
    contentType: text(document.content_type, "document.content_type"),
    sizeBytes: optionalNumber(document.size_bytes, "document.size_bytes") ?? 0,
    createdAt: text(document.created_at, "document.created_at"),
  };
}

export function parseOwnVerification(value: unknown): OwnVerification {
  const verification = record(value, "verification");
  const status = OWN_STATUSES.find((item) => item === verification.status);
  if (!status) {
    throw new UnexpectedResponseError("verification.status");
  }
  return {
    status,
    submittedAt: optionalText(verification.submitted_at, "verification.date"),
    documents: list(verification.documents, "verification.documents").map(
      parseDocument,
    ),
  };
}

export function parseAccount(value: unknown): Account {
  const account = record(value, "account");
  const verifications = record(account.verifications, "account.verifications");
  return {
    user: parseUser(account.user),
    profile: parseProfile(account.profile),
    preferences: parsePreferences(account.preferences),
    societies: list(account.societies, "account.societies").map((item) => {
      const preference = record(item, "society preference");
      return {
        society: parseSociety(preference.society),
        priority: optionalNumber(preference.priority, "priority") ?? 0,
        // Only an explicit `false` marks a society as gone.
        available: preference.available !== false,
      };
    }),
    verifications: {
      identity: parseOwnVerification(verifications.identity),
      student: parseOwnVerification(verifications.student),
    },
  };
}

const COMMUNITY_TYPES: CommunityType[] = [
  "APARTMENT_COMPLEX",
  "VILLA_COMMUNITY",
];

export function parseDirectorySocieties(value: unknown): DirectorySociety[] {
  return list(value, "societies").map((item) => {
    const society = record(item, "society");
    return {
      ...parseSociety(society),
      communityType:
        COMMUNITY_TYPES.find((type) => type === society.community_type) ?? null,
      description: optionalText(society.description, "society.description"),
    };
  });
}

export function parseLocalities(value: unknown): DirectoryLocality[] {
  return list(value, "localities").map((item) => {
    const locality = record(item, "locality");
    return {
      id: text(locality.id, "locality.id"),
      name: text(locality.name, "locality.name"),
      city: text(locality.city, "locality.city"),
      description: optionalText(locality.description, "locality.description"),
      societyCount:
        optionalNumber(locality.society_count, "locality.society_count") ?? 0,
    };
  });
}

// --- Discovery, matches and notifications -----------------------------------

// The allowed values come from the label tables, so they are listed once.
const keysOf = <T extends string>(labels: Record<T, string>) =>
  Object.keys(labels) as T[];
const ROOM_TYPES = keysOf(ROOM_TYPE_LABELS);
const FOOD_PREFERENCES = keysOf(FOOD_LABELS);
const HABITS = keysOf(HABIT_LABELS);
const SLEEP_SCHEDULES = keysOf(SLEEP_LABELS);
const CLEANLINESS_LEVELS = keysOf(CLEANLINESS_LABELS);
const SOCIAL_PREFERENCES = keysOf(SOCIAL_LABELS);
const GUEST_FREQUENCIES = keysOf(GUEST_LABELS);

const FACTOR_KEYS: FactorKey[] = [
  "budget",
  "societies",
  "lifestyle",
  "move_in",
  "room",
  "food",
];
const AREA_OVERLAPS: AreaOverlap[] = [
  "SAME_SOCIETY",
  "SAME_LOCALITY",
  "NONE",
  "UNKNOWN",
];
const PUBLIC_VERIFICATION_STATES: VerificationState[] = [
  "NOT_VERIFIED",
  "PENDING",
  "VERIFIED",
];

/** One of a fixed set of values, or null; anything else is an error. */
export function oneOf<T extends string>(
  value: unknown,
  allowed: readonly T[],
  what: string,
): T | null {
  if (value === null || value === undefined) {
    return null;
  }
  const found = allowed.find((item) => item === value);
  if (found === undefined) {
    throw new UnexpectedResponseError(what);
  }
  return found;
}

export function required<T>(value: T | null, what: string): T {
  if (value === null) {
    throw new UnexpectedResponseError(what);
  }
  return value;
}

export function parseCompatibility(value: unknown): Compatibility {
  const c = record(value, "compatibility");
  return {
    score: optionalNumber(c.score, "compatibility.score"),
    summary: text(c.summary, "compatibility.summary"),
    factors: list(c.factors, "compatibility.factors").map((item) => {
      const factor = record(item, "factor");
      return {
        key: required(oneOf(factor.key, FACTOR_KEYS, "factor.key"), "factor"),
        label: text(factor.label, "factor.label"),
        score: optionalNumber(factor.score, "factor.score"),
        available: factor.available === true,
        weight: optionalNumber(factor.weight, "factor.weight") ?? 0,
        effectiveWeight:
          optionalNumber(factor.effective_weight, "factor.effective") ?? 0,
        explanation: text(factor.explanation, "factor.explanation"),
      };
    }),
    unavailable: list(c.unavailable, "compatibility.unavailable").map((key) =>
      required(oneOf(key, FACTOR_KEYS, "unavailable"), "unavailable"),
    ),
    areaOverlap:
      oneOf(c.area_overlap, AREA_OVERLAPS, "compatibility.area") ?? "UNKNOWN",
    sharedSocieties: list(c.shared_societies, "shared_societies").map((name) =>
      text(name, "shared society"),
    ),
  };
}

function parseStudentPublic(value: unknown): StudentProfile {
  const student = record(value, "student");
  const p = record(student.preferences, "student.preferences");
  const pick = <T extends string>(field: unknown, allowed: readonly T[]) =>
    oneOf(field, allowed, "student.preferences");
  return {
    id: text(student.id, "student.id"),
    fullName: text(student.full_name, "student.full_name"),
    collegeName: text(student.college_name, "student.college_name"),
    course: optionalText(student.course, "student.course"),
    department: optionalText(student.department, "student.department"),
    academicYear: optionalNumber(student.academic_year, "student.year"),
    bio: optionalText(student.bio, "student.bio"),
    gender: optionalText(student.gender, "student.gender"),
    photoUrl: apiAddress(optionalText(student.photo_url, "student.photo_url")),
    identityVerification:
      oneOf(student.identity_verification, PUBLIC_VERIFICATION_STATES, "id") ??
      "NOT_VERIFIED",
    studentVerification:
      oneOf(
        student.student_verification,
        PUBLIC_VERIFICATION_STATES,
        "student",
      ) ?? "NOT_VERIFIED",
    preferences: {
      minBudget: optionalNumber(p.min_budget, "min_budget"),
      maxBudget: optionalNumber(p.max_budget, "max_budget"),
      moveInDate: optionalText(p.move_in_date, "move_in_date"),
      roomType: pick(p.room_type, ROOM_TYPES),
      foodPreference: pick(p.food_preference, FOOD_PREFERENCES),
      smoking: pick(p.smoking_preference, HABITS),
      drinking: pick(p.drinking_preference, HABITS),
      sleepSchedule: pick(p.sleep_schedule, SLEEP_SCHEDULES),
      cleanliness: pick(p.cleanliness_level, CLEANLINESS_LEVELS),
      socialPreference: pick(p.social_preference, SOCIAL_PREFERENCES),
      guestFrequency: pick(p.guest_frequency, GUEST_FREQUENCIES),
    },
    societyPreferences: list(student.societies, "student.societies").map(
      (item) => {
        const choice = record(item, "society choice");
        return {
          society: parseSociety(choice.society),
          priority: optionalNumber(choice.priority, "priority") ?? 0,
        };
      },
    ),
  };
}

export function parseCandidate(value: unknown): DiscoveryCandidate {
  const item = record(value, "candidate");
  const compatibility = parseCompatibility(item.compatibility);
  return {
    profile: parseStudentPublic(item.student),
    compatibilityScore: compatibility.score,
    ...reasonsFrom(compatibility),
    compatibility,
  };
}

export function parseDiscoveryPage(value: unknown): DiscoveryPage {
  const page = record(value, "discovery page");
  return {
    candidates: list(page.items, "discovery.items").map(parseCandidate),
    nextCursor: optionalText(page.next_cursor, "discovery.next_cursor"),
    remaining: optionalNumber(page.remaining, "discovery.remaining") ?? 0,
  };
}

const DECISIONS: Decision[] = ["LIKE", "PASS"];

export function parseStudentView(value: unknown): StudentView {
  const view = record(value, "student view");
  return {
    candidate: parseCandidate(view),
    yourDecision: oneOf(view.your_decision, DECISIONS, "your_decision"),
    matchId: optionalText(view.match_id, "match_id"),
  };
}

export function parseDecision(value: unknown): DecisionResult {
  const result = record(value, "decision");
  return {
    decision: required(
      oneOf(result.decision, DECISIONS, "decision"),
      "decision",
    ),
    matched: result.matched === true,
    matchId: optionalText(result.match_id, "decision.match_id"),
  };
}

export function parseMatches(value: unknown): MatchSummary[] {
  return list(value, "matches").map((item) => {
    const match = record(item, "match");
    const student = record(match.student, "match.student");
    return {
      id: text(match.id, "match.id"),
      matchedAt: text(match.matched_at, "match.matched_at"),
      compatibilityScore: optionalNumber(match.compatibility_score, "score"),
      conversationId: optionalText(match.conversation_id, "conversation_id"),
      student: {
        id: text(student.id, "student.id"),
        fullName: text(student.full_name, "student.full_name"),
        photoUrl: apiAddress(
          optionalText(student.photo_url, "student.photo_url"),
        ),
        collegeName: text(student.college_name, "student.college_name"),
        course: optionalText(student.course, "student.course"),
        department: optionalText(student.department, "student.department"),
        academicYear: optionalNumber(student.academic_year, "student.year"),
      },
    };
  });
}

export function parseNotifications(value: unknown): NotificationList {
  const body = record(value, "notifications");
  return {
    notifications: list(body.items, "notifications.items").map((item) => {
      const n = record(item, "notification");
      return {
        id: text(n.id, "notification.id"),
        type: text(n.type, "notification.type"),
        title: text(n.title, "notification.title"),
        body: text(n.body, "notification.body"),
        referenceType: optionalText(n.reference_type, "reference_type"),
        referenceId: optionalText(n.reference_id, "reference_id"),
        isRead: n.is_read === true,
        createdAt: text(n.created_at, "notification.created_at"),
      };
    }),
    unreadCount: optionalNumber(body.unread_count, "unread_count") ?? 0,
  };
}
