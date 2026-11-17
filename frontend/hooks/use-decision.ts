"use client";

import { useState } from "react";

import { ApiError, describeApiError } from "@/services/api-client";
import { sendDecision } from "@/services/discovery";
import type { Decision, DecisionResult } from "@/types/discovery";

interface Target {
  id: string;
  fullName: string;
}

interface DecisionCallbacks {
  /** The decision was saved (or had already been saved, identically). */
  onSaved: (result: DecisionResult, target: Target) => void;
  /** The person can no longer be decided on (gone, or decided already). */
  onUnavailable?: (target: Target) => void;
}

/**
 * Sending a like or a pass, and everything that can come back: a match,
 * a profile that has meanwhile disappeared, an unconfirmed email, or a
 * network failure. Used by the Discover deck and the full profile page.
 */
export function useDecision({ onSaved, onUnavailable }: DecisionCallbacks) {
  const [pending, setPending] = useState<Decision | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [matchedWith, setMatchedWith] = useState<string | null>(null);

  async function decide(target: Target, decision: Decision): Promise<void> {
    if (pending) {
      return;
    }
    setPending(decision);
    setNotice(null);
    try {
      const result = await sendDecision(target.id, decision);
      if (result.matched) {
        setMatchedWith(target.fullName);
      }
      onSaved(result, target);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        setNotice(`${target.fullName}'s profile is no longer available.`);
        onUnavailable?.(target);
      } else if (error instanceof ApiError && error.status === 409) {
        setNotice(error.message);
        onUnavailable?.(target);
      } else {
        setNotice(describeApiError(error));
      }
    } finally {
      setPending(null);
    }
  }

  return {
    decide,
    pending,
    notice,
    clearNotice: () => setNotice(null),
    matchedWith,
    closeMatch: () => setMatchedWith(null),
  };
}
