/**
 * Discovery, compatibility, matches and notifications, as the backend
 * returns them (backend/app/schemas/discovery.py).
 */

import type { DiscoveryCandidate } from "@/types/profile";

export type FactorKey =
  "budget" | "societies" | "lifestyle" | "move_in" | "room" | "food";

/** Whether two people want to live in the same place. */
export type AreaOverlap = "SAME_SOCIETY" | "SAME_LOCALITY" | "NONE" | "UNKNOWN";

export interface CompatibilityFactor {
  key: FactorKey;
  label: string;
  /** 0 to 100, or null when it could not be judged. */
  score: number | null;
  available: boolean;
  /** The configured weight, in percent. */
  weight: number;
  /** The share it really had once unjudged factors were left out. */
  effectiveWeight: number;
  explanation: string;
}

export interface Compatibility {
  /** 0 to 100, or null when nothing could be compared. */
  score: number | null;
  summary: string;
  factors: CompatibilityFactor[];
  unavailable: FactorKey[];
  areaOverlap: AreaOverlap;
  sharedSocieties: string[];
}

export type Decision = "LIKE" | "PASS";

export interface DiscoveryPage {
  candidates: DiscoveryCandidate[];
  /** Pass back to load the next page; null on the last page. */
  nextCursor: string | null;
  /** How many people are left to decide on, including this page. */
  remaining: number;
}

/** A full profile, opened from a card or a match. */
export interface StudentView {
  candidate: DiscoveryCandidate;
  /** Your own decision. The other person's is never revealed. */
  yourDecision: Decision | null;
  matchId: string | null;
}

export interface DecisionResult {
  decision: Decision;
  matched: boolean;
  matchId: string | null;
}

export interface MatchStudent {
  id: string;
  fullName: string;
  photoUrl: string | null;
  collegeName: string;
  course: string | null;
  department: string | null;
  academicYear: number | null;
}

export interface MatchSummary {
  id: string;
  /** ISO date and time. */
  matchedAt: string;
  /** The score when you matched. */
  compatibilityScore: number | null;
  conversationId: string | null;
  student: MatchStudent;
}

export interface AppNotification {
  id: string;
  type: string;
  title: string;
  body: string;
  referenceType: string | null;
  referenceId: string | null;
  isRead: boolean;
  /** ISO date and time. */
  createdAt: string;
}

export interface NotificationList {
  notifications: AppNotification[];
  unreadCount: number;
}
