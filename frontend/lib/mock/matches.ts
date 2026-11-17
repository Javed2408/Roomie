/**
 * SAMPLE DATA — invented matches and conversations for building and
 * reviewing screens only. None of these people or messages are real.
 *
 * Any screen that shows this data must display a "Sample data" label.
 */

import { DISCOVERY_CANDIDATES } from "@/lib/mock/profiles";
import type { Conversation, Match } from "@/types/match";
import type { DiscoveryCandidate } from "@/types/profile";

function candidate(id: string): DiscoveryCandidate {
  const found = DISCOVERY_CANDIDATES.find((item) => item.profile.id === id);
  if (!found) {
    throw new Error(
      `Sample profile "${id}" is missing from lib/mock/profiles.`,
    );
  }
  return found;
}

const MEERA_MATCH: Match = {
  id: "match-meera",
  candidate: candidate("user-meera"),
  matchedOn: "2026-11-10",
};

const KAVYA_MATCH: Match = {
  id: "match-kavya",
  candidate: candidate("user-kavya"),
  matchedOn: "2026-11-12",
};

export const MATCHES: Match[] = [KAVYA_MATCH, MEERA_MATCH];

export const CONVERSATIONS: Conversation[] = [
  {
    id: "conversation-meera",
    match: MEERA_MATCH,
    unreadCount: 1,
    messages: [
      {
        id: "m1",
        sender: "them",
        content:
          "Hi Ananya! Saw we both have Lakeside Residency as first choice.",
        sentAt: "2026-11-10T18:42",
      },
      {
        id: "m2",
        sender: "me",
        content:
          "Hi Meera! Yes, I visited last week. Are you looking at a 2BHK or 3BHK?",
        sentAt: "2026-11-10T19:05",
      },
      {
        id: "m3",
        sender: "them",
        content:
          "3BHK if we can find one more person. Want to go and see a flat together this weekend?",
        sentAt: "2026-11-11T09:15",
      },
    ],
  },
  {
    id: "conversation-kavya",
    match: KAVYA_MATCH,
    unreadCount: 0,
    messages: [],
  },
];
