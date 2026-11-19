"use client";

import { Hand } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button, ButtonLink } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/states";
import { formatInr, formatTimestampDate } from "@/lib/format";
import { describeApiError } from "@/services/api-client";
import { fetchMyInterests, withdrawInterest } from "@/services/listings";
import {
  INTEREST_STATUS_LABELS,
  type InterestStatus,
  type MyInterest,
} from "@/types/listing";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; interests: MyInterest[] };

const TONES: Record<
  InterestStatus,
  "warning" | "success" | "danger" | "neutral"
> = {
  PENDING: "warning",
  ACCEPTED: "success",
  DECLINED: "danger",
  WITHDRAWN: "neutral",
};

/** Listings you expressed interest in, and what the creator replied. */
export function MyInterests() {
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{ key: number; state: State } | null>(
    null,
  );
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchMyInterests(controller.signal)
      .then((interests) =>
        setResult({ key: attempt, state: { status: "ready", interests } }),
      )
      .catch((problem: unknown) => {
        if (!controller.signal.aborted) {
          setResult({
            key: attempt,
            state: { status: "error", message: describeApiError(problem) },
          });
        }
      });
    return () => controller.abort();
  }, [attempt]);

  const state: State =
    result?.key === attempt ? result.state : { status: "loading" };

  async function withdraw(listingId: string) {
    setBusy(listingId);
    setError(null);
    try {
      await withdrawInterest(listingId);
      setAttempt((value) => value + 1);
    } catch (problem) {
      setError(describeApiError(problem));
    } finally {
      setBusy(null);
    }
  }

  if (state.status === "loading") {
    return (
      <div className="space-y-4" aria-busy>
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }
  if (state.status === "error") {
    return (
      <ErrorState
        title="Your interests could not load"
        description={state.message}
        onRetry={() => setAttempt((value) => value + 1)}
      />
    );
  }
  if (state.interests.length === 0) {
    return (
      <EmptyState
        icon={Hand}
        title="No interests yet"
        description="When a listing looks right, open it and tap “I am interested”. The poster then sees your profile."
        action={
          <ButtonLink href="/accommodation">Browse accommodation</ButtonLink>
        }
      />
    );
  }
  return (
    <>
      {error && (
        <p role="alert" className="text-danger mb-4 text-sm">
          {error}
        </p>
      )}
      <ul className="space-y-4">
        {state.interests.map((interest) => (
          <li key={interest.listingId}>
            <Card>
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={TONES[interest.status]}>
                  {INTEREST_STATUS_LABELS[interest.status]}
                </Badge>
                {!interest.listingAvailable && (
                  <Badge>No longer available</Badge>
                )}
              </div>
              <h2 className="mt-2 text-base font-semibold">
                {interest.listingAvailable ? (
                  <Link
                    href={`/accommodation/${interest.listingId}`}
                    className="hover:text-primary underline-offset-4 hover:underline"
                  >
                    {interest.title}
                  </Link>
                ) : (
                  interest.title
                )}
              </h2>
              <p className="text-muted mt-1 text-sm">
                {interest.type === "EXISTING_ACCOMMODATION"
                  ? "Room available"
                  : "Looking to rent together"}{" "}
                · sent {formatTimestampDate(interest.createdAt)}
                {interest.acknowledgedBrokerageAmount !== null &&
                  ` · brokerage ${formatInr(interest.acknowledgedBrokerageAmount)} acknowledged`}
              </p>
              {interest.status === "ACCEPTED" && (
                <p className="text-foreground mt-2 text-sm">
                  Accepted. You will be able to message the poster on Roomie
                  once messaging opens.
                </p>
              )}
              {interest.status === "PENDING" && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="mt-3"
                  isLoading={busy === interest.listingId}
                  disabled={busy !== null}
                  onClick={() => void withdraw(interest.listingId)}
                >
                  Withdraw
                </Button>
              )}
            </Card>
          </li>
        ))}
      </ul>
    </>
  );
}
