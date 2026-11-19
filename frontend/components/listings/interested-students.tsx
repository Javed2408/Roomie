"use client";

import { Check, Hand, UserRound, X } from "lucide-react";
import { useEffect, useState } from "react";

import { ProfileCard } from "@/components/discovery/profile-card";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button, ButtonLink } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ErrorState, Spinner } from "@/components/ui/states";
import { formatInr, formatTimestampDate } from "@/lib/format";
import { describeApiError } from "@/services/api-client";
import {
  fetchInterestedStudents,
  respondToInterest,
} from "@/services/listings";
import {
  INTEREST_STATUS_LABELS,
  type InterestStatus,
  type InterestedStudent,
} from "@/types/listing";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; students: InterestedStudent[] };

const STATUS_TONES: Record<
  InterestStatus,
  "warning" | "success" | "neutral" | "danger"
> = {
  PENDING: "warning",
  ACCEPTED: "success",
  DECLINED: "danger",
  WITHDRAWN: "neutral",
};

/**
 * Students who expressed interest in your listing, with their public
 * profiles. Withdrawn interest and people you have blocked (or who have
 * blocked you) are never listed: the backend leaves them out.
 */
export function InterestedStudents({ listingId }: { listingId: string }) {
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{ key: string; state: State } | null>(
    null,
  );
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const key = `${listingId}|${attempt}`;

  useEffect(() => {
    const controller = new AbortController();
    fetchInterestedStudents(listingId, controller.signal)
      .then((students) =>
        setResult({ key, state: { status: "ready", students } }),
      )
      .catch((problem: unknown) => {
        if (!controller.signal.aborted) {
          setResult({
            key,
            state: { status: "error", message: describeApiError(problem) },
          });
        }
      });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const state: State =
    result?.key === key ? result.state : { status: "loading" };

  async function respond(interestId: string, status: "ACCEPTED" | "DECLINED") {
    setBusy(`${interestId}|${status}`);
    setError(null);
    try {
      const students = await respondToInterest(listingId, interestId, status);
      setResult({ key, state: { status: "ready", students } });
    } catch (problem) {
      setError(describeApiError(problem));
    } finally {
      setBusy(null);
    }
  }

  return (
    <Card>
      <h2 className="text-lg font-semibold">Interested students</h2>
      {state.status === "loading" && (
        <div className="mt-4">
          <Spinner label="Loading interested students" />
        </div>
      )}
      {state.status === "error" && (
        <ErrorState
          title="Could not load interest"
          description={state.message}
          onRetry={() => setAttempt((value) => value + 1)}
          className="mt-4"
        />
      )}
      {state.status === "ready" && state.students.length === 0 && (
        <p className="text-muted mt-2 flex items-start gap-2 text-sm">
          <Hand aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          Nobody has expressed interest yet. Students can do so once your
          listing is approved and public.
        </p>
      )}
      {error && (
        <Alert tone="danger" role="alert" className="mt-4">
          {error}
        </Alert>
      )}
      {state.status === "ready" && state.students.length > 0 && (
        <ul className="mt-4 space-y-5">
          {state.students.map((item) => {
            const { profile } = item.candidate;
            const firstName = profile.fullName.split(" ")[0] ?? "them";
            return (
              <li key={item.interestId} className="space-y-3">
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <Badge tone={STATUS_TONES[item.status]}>
                    {item.status === "PENDING"
                      ? "Waiting for your reply"
                      : INTEREST_STATUS_LABELS[item.status]}
                  </Badge>
                  <span className="text-muted">
                    Interested since {formatTimestampDate(item.createdAt)}
                  </span>
                  {item.acknowledgedBrokerageAmount !== null && (
                    <span className="text-muted">
                      · acknowledged brokerage of{" "}
                      {formatInr(item.acknowledgedBrokerageAmount)}
                    </span>
                  )}
                </div>
                <ProfileCard candidate={item.candidate} maxReasons={2} />
                <div className="flex flex-wrap gap-3">
                  <ButtonLink
                    href={`/students/${profile.id}`}
                    variant="ghost"
                    size="sm"
                  >
                    <UserRound aria-hidden="true" className="size-4" />
                    Full profile
                  </ButtonLink>
                  {item.status === "PENDING" && (
                    <>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() =>
                          void respond(item.interestId, "DECLINED")
                        }
                        isLoading={busy === `${item.interestId}|DECLINED`}
                        disabled={busy !== null}
                      >
                        <X aria-hidden="true" className="size-4" />
                        Decline
                      </Button>
                      <Button
                        size="sm"
                        onClick={() =>
                          void respond(item.interestId, "ACCEPTED")
                        }
                        isLoading={busy === `${item.interestId}|ACCEPTED`}
                        disabled={busy !== null}
                      >
                        <Check aria-hidden="true" className="size-4" />
                        Accept {firstName}
                      </Button>
                    </>
                  )}
                </div>
                {item.status === "ACCEPTED" && (
                  <p className="text-muted text-sm">
                    {firstName} has been told. You will be able to message each
                    other on Roomie once messaging opens.
                  </p>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
