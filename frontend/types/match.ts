/** Mirrors the `matches`, `conversations` and `messages` tables. */

import type { DiscoveryCandidate } from "@/types/profile";

export interface Match {
  id: string;
  candidate: DiscoveryCandidate;
  /** ISO date, YYYY-MM-DD. */
  matchedOn: string;
}

export interface Message {
  id: string;
  /** "me" is the signed-in student; "them" is the other participant. */
  sender: "me" | "them";
  content: string;
  /** Local date and time, YYYY-MM-DDTHH:MM. */
  sentAt: string;
}

/** One conversation per match (DATABASE_SCHEMA.md, section 3.10). */
export interface Conversation {
  id: string;
  match: Match;
  messages: Message[];
  unreadCount: number;
}

export const MESSAGE_MAX_LENGTH = 1000;
