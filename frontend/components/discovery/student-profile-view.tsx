"use client";

import { ArrowLeft, Heart, UserRound, UserX, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { PageSkeleton } from "@/components/app-shell/page-skeleton";
import { CompatibilityBreakdown } from "@/components/discovery/compatibility-breakdown";
import { MatchDialog } from "@/components/discovery/match-dialog";
import { ProfileCard } from "@/components/discovery/profile-card";
import { SafetyActions } from "@/components/safety/safety-actions";
import { useSession } from "@/components/session/session-provider";
import { Alert } from "@/components/ui/alert";
import { Button, ButtonLink } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { useDecision } from "@/hooks/use-decision";
import { ApiError, describeApiError } from "@/services/api-client";
import { fetchStudent } from "@/services/discovery";
import type { StudentView } from "@/types/discovery";
import { GUEST_LABELS, HABIT_LABELS } from "@/types/profile";

type ViewState =
  | { status: "loading" }
  | { status: "missing" }
  | { status: "incomplete" }
  | { status: "error"; message: string }
  | { status: "ready"; view: StudentView };

function BackLink() {
  return (
    <Link
      href="/discover"
      className="text-muted hover:text-foreground -ml-2 inline-flex h-10 items-center gap-1.5 rounded-lg px-2 text-sm font-medium transition-colors duration-150"
    >
      <ArrowLeft aria-hidden="true" className="size-4" />
      Back to Discover
    </Link>
  );
}

/**
 * Another student's full profile, with how the score was worked out and
 * Like and Pass. Opened from a Discover card or from a match.
 */
export function StudentProfileView({ id }: { id: string }) {
  const { account } = useSession();
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{
    key: string;
    state: ViewState;
  } | null>(null);
  const key = `${id}|${attempt}`;

  useEffect(() => {
    const controller = new AbortController();
    fetchStudent(id, controller.signal)
      .then((view) => setResult({ key, state: { status: "ready", view } }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        let state: ViewState = {
          status: "error",
          message: describeApiError(error),
        };
        // 404: hidden or gone. 422: not even a valid profile address.
        if (
          error instanceof ApiError &&
          (error.status === 404 || error.status === 422)
        ) {
          state = { status: "missing" };
        } else if (
          error instanceof ApiError &&
          error.code === "profile_incomplete"
        ) {
          state = { status: "incomplete" };
        }
        setResult({ key, state });
      });
    return () => controller.abort();
    // `key` combines the id and the retry count.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const { decide, pending, notice, matchedWith, closeMatch } = useDecision({
    onSaved: (decision) =>
      setResult((current) =>
        current?.state.status === "ready"
          ? {
              ...current,
              state: {
                status: "ready",
                view: {
                  ...current.state.view,
                  yourDecision: decision.decision,
                  matchId: decision.matchId,
                },
              },
            }
          : current,
      ),
    onUnavailable: () =>
      setResult((current) =>
        current ? { ...current, state: { status: "missing" } } : current,
      ),
  });

  const state: ViewState =
    result && result.key === key ? result.state : { status: "loading" };

  if (state.status === "loading") {
    return <PageSkeleton />;
  }
  if (state.status === "missing") {
    return (
      <div className="mx-auto max-w-md">
        <BackLink />
        <EmptyState
          icon={UserX}
          title="This profile is not available"
          description="The student may have changed their profile or closed their account, or the link may be wrong."
          action={<ButtonLink href="/discover">Back to Discover</ButtonLink>}
          className="mt-4"
        />
      </div>
    );
  }
  if (state.status === "incomplete") {
    return (
      <div className="mx-auto max-w-md">
        <EmptyState
          icon={UserRound}
          title="Finish your profile first"
          description="Other students' profiles open once your own is complete and published."
          action={
            <ButtonLink href="/onboarding">Finish your profile</ButtonLink>
          }
        />
      </div>
    );
  }
  if (state.status === "error") {
    return (
      <ErrorState
        title="This profile could not load"
        description={state.message}
        onRetry={() => setAttempt((value) => value + 1)}
        className="mx-auto max-w-md"
      />
    );
  }

  const { candidate, yourDecision, matchId } = state.view;
  const { profile } = candidate;
  const firstName = profile.fullName.split(" ")[0] ?? profile.fullName;
  const canDecide = account.user.emailVerified;
  const target = { id: profile.id, fullName: profile.fullName };
  const habits: Array<[string, string | null]> = [
    [
      "Guests",
      profile.preferences.guestFrequency &&
        GUEST_LABELS[profile.preferences.guestFrequency],
    ],
    [
      "Smoking",
      profile.preferences.smoking && HABIT_LABELS[profile.preferences.smoking],
    ],
    [
      "Alcohol",
      profile.preferences.drinking &&
        HABIT_LABELS[profile.preferences.drinking],
    ],
  ];

  return (
    <div className="mx-auto max-w-md">
      <div className="mb-4">
        <BackLink />
      </div>

      <h1 className="sr-only">{profile.fullName}</h1>
      {/* The full breakdown is further down, so the card keeps it short. */}
      <ProfileCard candidate={candidate} maxReasons={3} />

      <Card className="mt-5">
        {matchId ? (
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-foreground text-sm font-medium">
              You and {firstName} matched.
            </p>
            <ButtonLink href="/matches" size="sm" variant="secondary">
              See your matches
            </ButtonLink>
          </div>
        ) : yourDecision ? (
          <p className="text-muted text-sm">
            {yourDecision === "LIKE"
              ? `You liked ${firstName}. If they like you too, you will match.`
              : `You passed on ${firstName}. They are not told.`}
          </p>
        ) : (
          <>
            <h2 className="text-lg font-semibold">
              Would you live with {firstName}?
            </h2>
            {!canDecide && (
              <p className="text-muted mt-1 text-sm">
                Confirm your email address to like or pass.
              </p>
            )}
            <div className="mt-3 grid grid-cols-2 gap-3">
              <Button
                variant="secondary"
                onClick={() => void decide(target, "PASS")}
                disabled={!canDecide || pending !== null}
                isLoading={pending === "PASS"}
              >
                <X aria-hidden="true" className="size-4" />
                Pass
              </Button>
              <Button
                variant="accent"
                onClick={() => void decide(target, "LIKE")}
                disabled={!canDecide || pending !== null}
                isLoading={pending === "LIKE"}
              >
                <Heart aria-hidden="true" className="size-4" />
                Like
              </Button>
            </div>
          </>
        )}
        {notice && (
          <Alert tone="warning" role="alert" className="mt-3">
            {notice}
          </Alert>
        )}
      </Card>

      {candidate.compatibility && (
        <div className="mt-5">
          <CompatibilityBreakdown
            compatibility={candidate.compatibility}
            name={firstName}
          />
        </div>
      )}

      <Card className="mt-5">
        <h2 className="text-lg font-semibold">More about home life</h2>
        <dl className="mt-3 grid grid-cols-3 gap-4 text-sm">
          {habits.map(([label, value]) => (
            <div key={label}>
              <dt className="text-subtle text-xs">{label}</dt>
              <dd className="text-foreground mt-0.5 font-medium">
                {value ?? "Not set"}
              </dd>
            </div>
          ))}
        </dl>
      </Card>

      <Card className="mt-5">
        <h2 className="text-lg font-semibold">Safety</h2>
        <p className="text-muted mt-1 mb-3 text-sm leading-relaxed">
          Something not right about this profile?
        </p>
        <SafetyActions targetName={profile.fullName} kind="person" />
      </Card>

      <MatchDialog name={matchedWith} onClose={closeMatch} closeLabel="Close" />
    </div>
  );
}
