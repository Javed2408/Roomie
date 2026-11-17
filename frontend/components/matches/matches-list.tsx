"use client";

import { Heart } from "lucide-react";
import { useEffect, useState } from "react";

import { studySummary } from "@/components/discovery/profile-card";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { ButtonLink } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/states";
import { formatTimestampDate } from "@/lib/format";
import { describeApiError } from "@/services/api-client";
import {
  fetchMatches,
  fetchNotifications,
  markNotificationRead,
} from "@/services/discovery";
import type { MatchSummary } from "@/types/discovery";

type ListState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; matches: MatchSummary[]; isNew: Set<string> };

/**
 * Everyone you have matched with, newest first. A match is new until you
 * have seen it here once: its "new match" notification is then marked read.
 */
export function MatchesList() {
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{ attempt: number; state: ListState }>({
    attempt: -1,
    state: { status: "loading" },
  });

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      fetchMatches(controller.signal),
      fetchNotifications(controller.signal),
    ])
      .then(([matches, inbox]) => {
        const unseen = inbox.notifications.filter(
          (item) =>
            !item.isRead &&
            item.type === "NEW_MATCH" &&
            item.referenceId !== null,
        );
        setResult({
          attempt,
          state: {
            status: "ready",
            matches,
            isNew: new Set(unseen.map((item) => item.referenceId ?? "")),
          },
        });
        // Seen now. If this fails they simply show as new again next time.
        for (const item of unseen) {
          void markNotificationRead(item.id).catch(() => undefined);
        }
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setResult({
            attempt,
            state: { status: "error", message: describeApiError(error) },
          });
        }
      });
    return () => controller.abort();
  }, [attempt]);

  const state: ListState =
    result.attempt === attempt ? result.state : { status: "loading" };

  if (state.status === "loading") {
    return (
      <div className="grid gap-5 md:grid-cols-2" aria-busy="true">
        <p role="status" className="sr-only">
          Loading matches…
        </p>
        <Skeleton className="h-44" />
        <Skeleton className="h-44" />
      </div>
    );
  }
  if (state.status === "error") {
    return (
      <ErrorState
        title="Your matches could not load"
        description={state.message}
        onRetry={() => setAttempt((value) => value + 1)}
      />
    );
  }
  if (state.matches.length === 0) {
    return (
      <EmptyState
        icon={Heart}
        title="No matches yet"
        description="When you and another student both like each other, they will appear here."
        action={<ButtonLink href="/discover">Discover roommates</ButtonLink>}
      />
    );
  }

  return (
    <>
      <ul className="grid gap-5 md:grid-cols-2">
        {state.matches.map((match) => {
          const study = studySummary(match.student);
          return (
            <li key={match.id}>
              <Card className="flex h-full flex-col">
                <div className="flex items-center gap-4">
                  <Avatar name={match.student.fullName} size="lg" />
                  <div className="min-w-0">
                    <h2 className="truncate text-lg font-semibold">
                      {match.student.fullName}
                    </h2>
                    {study && <p className="text-muted text-sm">{study}</p>}
                    <p className="text-subtle truncate text-sm">
                      {match.student.collegeName}
                    </p>
                  </div>
                </div>
                <div className="mt-4 flex flex-1 flex-wrap items-start gap-2">
                  {state.isNew.has(match.id) && (
                    <Badge tone="accent">New match</Badge>
                  )}
                  {match.compatibilityScore !== null && (
                    <Badge tone="primary">
                      {match.compatibilityScore}% compatibility
                    </Badge>
                  )}
                  <Badge>Matched {formatTimestampDate(match.matchedAt)}</Badge>
                </div>
                <div className="mt-5">
                  <ButtonLink
                    href={`/students/${match.student.id}`}
                    variant="secondary"
                    fullWidth
                  >
                    View profile
                  </ButtonLink>
                </div>
              </Card>
            </li>
          );
        })}
      </ul>
      <p className="text-subtle mt-6 text-sm leading-relaxed">
        Messaging between matches opens in a later update. The score shown is
        the one from when you matched; a profile shows the latest.
      </p>
    </>
  );
}
