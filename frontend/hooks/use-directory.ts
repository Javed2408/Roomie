"use client";

import { useEffect, useState } from "react";

import { describeApiError } from "@/services/api-client";
import { fetchLocalities, searchSocieties } from "@/services/directory";
import type { DirectoryLocality, DirectorySociety } from "@/types/society";

/**
 * A value that only changes once it has stopped changing for `delayMs`.
 * Used so the society search waits for a pause in typing instead of
 * sending a request for every key pressed.
 */
export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [settled, setSettled] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return settled;
}

export type LocalitiesState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; localities: DirectoryLocality[] };

/** The areas students can filter by. */
export function useLocalities(): LocalitiesState {
  const [state, setState] = useState<LocalitiesState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    fetchLocalities(controller.signal)
      .then((localities) => setState({ status: "ready", localities }))
      .catch(() => {
        if (!controller.signal.aborted) {
          setState({ status: "error" });
        }
      });
    return () => controller.abort();
  }, []);

  return state;
}

export type SocietySearchState =
  | { status: "loading" }
  | { status: "error"; message: string; retry: () => void }
  | { status: "ready"; societies: DirectorySociety[] };

interface SearchResult {
  /** Which search these results belong to. */
  key: string;
  outcome:
    | { ok: true; societies: DirectorySociety[] }
    | { ok: false; message: string };
}

/**
 * Search the directory, again whenever the query or locality changes.
 *
 * Also returns `seen`: every society any search has returned so far, so
 * the picker can still show the name of a chosen society after the
 * search moves on to something else.
 */
export function useSocietySearch(
  query: string,
  localityId: string | null,
): { search: SocietySearchState; seen: Map<string, DirectorySociety> } {
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<SearchResult | null>(null);
  const [seen, setSeen] = useState<Map<string, DirectorySociety>>(
    () => new Map(),
  );
  const key = `${attempt}|${localityId ?? ""}|${query.trim().toLowerCase()}`;

  useEffect(() => {
    const controller = new AbortController();
    searchSocieties({ query, localityId, signal: controller.signal })
      .then((societies) => {
        setResult({ key, outcome: { ok: true, societies } });
        setSeen((current) => {
          const next = new Map(current);
          for (const society of societies) {
            next.set(society.id, society);
          }
          return next;
        });
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setResult({
            key,
            outcome: { ok: false, message: describeApiError(error) },
          });
        }
      });
    return () => controller.abort();
    // `key` already combines query, localityId and attempt.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  // Results from an earlier search are not shown: a new one is under way.
  if (result === null || result.key !== key) {
    return { search: { status: "loading" }, seen };
  }
  if (!result.outcome.ok) {
    return {
      search: {
        status: "error",
        message: result.outcome.message,
        retry: () => setAttempt((current) => current + 1),
      },
      seen,
    };
  }
  return {
    search: { status: "ready", societies: result.outcome.societies },
    seen,
  };
}
