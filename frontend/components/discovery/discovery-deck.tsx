"use client";

import { Heart, RotateCcw, Sparkles, UserRound, X } from "lucide-react";
import Link from "next/link";
import {
  useEffect,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from "react";

import { MatchDialog } from "@/components/discovery/match-dialog";
import { ProfileCard } from "@/components/discovery/profile-card";
import { useSession } from "@/components/session/session-provider";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button, ButtonLink } from "@/components/ui/button";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/states";
import { useDecision } from "@/hooks/use-decision";
import { cn } from "@/lib/cn";
import { ApiError, describeApiError } from "@/services/api-client";
import { fetchDiscovery } from "@/services/discovery";
import type { AreaOverlap, Decision } from "@/types/discovery";
import type { DiscoveryCandidate } from "@/types/profile";

/** How far (in pixels) a card must be dragged to count as a decision. */
const SWIPE_DISTANCE = 110;
/** How long the card takes to leave, when motion is allowed. */
const LEAVE_MS = 220;
/** Load the next page when this few cards are left. */
const PREFETCH_AT = 3;

type DeckState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "incomplete" }
  | {
      status: "ready";
      queue: DiscoveryCandidate[];
      nextCursor: string | null;
      remaining: number;
    };

const AREA_BADGES: Record<
  AreaOverlap,
  { label: string; tone: "primary" | "info" | "neutral" } | null
> = {
  SAME_SOCIETY: { label: "Shares your societies", tone: "primary" },
  SAME_LOCALITY: { label: "Same area as you", tone: "info" },
  NONE: { label: "Looking in another area", tone: "neutral" },
  UNKNOWN: null,
};

function prefersReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Discover: one profile at a time, best match first, with Pass and Like.
 *
 * Buttons are the main way to decide. On touch screens and with a mouse a
 * card can also be dragged: right to like, left to pass. Every decision is
 * saved by the backend; a mutual like becomes a match straight away.
 */
export function DiscoveryDeck() {
  const { account } = useSession();
  const published = account.profile?.profileCompleted === true;
  const canDecide = account.user.emailVerified;
  const hasSocieties = account.societies.some((item) => item.available);

  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<DeckState>(
    published ? { status: "loading" } : { status: "incomplete" },
  );
  const [leaving, setLeaving] = useState<{
    id: string;
    decision: Decision | null;
  } | null>(null);
  const [dragX, setDragX] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [announcement, setAnnouncement] = useState("");
  const drag = useRef<{ pointerId: number; startX: number } | null>(null);
  const loadingMore = useRef(false);

  // The first page, and again after "Try again" / "Check again".
  useEffect(() => {
    if (!published) {
      return;
    }
    const controller = new AbortController();
    fetchDiscovery({ signal: controller.signal })
      .then((page) =>
        setState({
          status: "ready",
          queue: page.candidates,
          nextCursor: page.nextCursor,
          remaining: page.remaining,
        }),
      )
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        setState(
          error instanceof ApiError && error.code === "profile_incomplete"
            ? { status: "incomplete" }
            : { status: "error", message: describeApiError(error) },
        );
      });
    return () => controller.abort();
  }, [published, attempt]);

  // Load more before the queue runs out.
  const queueLength = state.status === "ready" ? state.queue.length : 0;
  const nextCursor = state.status === "ready" ? state.nextCursor : null;
  useEffect(() => {
    if (!nextCursor || queueLength > PREFETCH_AT || loadingMore.current) {
      return;
    }
    loadingMore.current = true;
    fetchDiscovery({ cursor: nextCursor })
      .then((page) =>
        setState((current) => {
          if (current.status !== "ready") {
            return current;
          }
          const known = new Set(current.queue.map((item) => item.profile.id));
          return {
            ...current,
            queue: [
              ...current.queue,
              ...page.candidates.filter((item) => !known.has(item.profile.id)),
            ],
            nextCursor: page.nextCursor,
          };
        }),
      )
      // A failed prefetch is retried when the next card is decided.
      .catch(() => undefined)
      .finally(() => {
        loadingMore.current = false;
      });
  }, [nextCursor, queueLength]);

  const current = state.status === "ready" ? state.queue[0] : undefined;

  // After a decision, bring the next card's top (the name) back into view.
  // Like and Pass sit below the card, so on a phone the page is usually
  // scrolled down when the next person appears.
  const cardArea = useRef<HTMLDivElement>(null);
  const currentId = current?.profile.id;
  const shownFirst = useRef(false);
  useEffect(() => {
    if (!currentId) {
      return;
    }
    if (!shownFirst.current) {
      shownFirst.current = true;
      return;
    }
    const area = cardArea.current;
    if (area && area.getBoundingClientRect().top < 0) {
      area.scrollIntoView({ block: "start" });
    }
  }, [currentId]);

  function removeCurrent(id: string, decision: Decision | null) {
    setLeaving({ id, decision });
    window.setTimeout(
      () => {
        setState((previous) =>
          previous.status === "ready"
            ? {
                ...previous,
                queue: previous.queue.filter((item) => item.profile.id !== id),
                remaining: Math.max(0, previous.remaining - 1),
              }
            : previous,
        );
        setLeaving(null);
        setDragX(0);
      },
      prefersReducedMotion() ? 0 : LEAVE_MS,
    );
  }

  const { decide, pending, notice, matchedWith, closeMatch } = useDecision({
    onSaved: (result, target) => {
      setAnnouncement(
        result.matched
          ? `You matched with ${target.fullName}.`
          : `You ${result.decision === "LIKE" ? "liked" : "passed on"} ${target.fullName}.`,
      );
      removeCurrent(target.id, result.decision);
    },
    onUnavailable: (target) => removeCurrent(target.id, null),
  });

  function decideOnCurrent(decision: Decision) {
    if (!current || !canDecide || leaving) {
      setDragX(0);
      return;
    }
    void decide(
      { id: current.profile.id, fullName: current.profile.fullName },
      decision,
    );
  }

  // --- Dragging a card ---------------------------------------------------

  function onPointerDown(event: ReactPointerEvent<HTMLDivElement>) {
    const target = event.target as HTMLElement;
    if (
      !canDecide ||
      pending ||
      leaving ||
      event.button !== 0 ||
      target.closest("a, button, input, textarea, select")
    ) {
      return;
    }
    drag.current = { pointerId: event.pointerId, startX: event.clientX };
    event.currentTarget.setPointerCapture(event.pointerId);
    setIsDragging(true);
  }

  function onPointerMove(event: ReactPointerEvent<HTMLDivElement>) {
    if (drag.current?.pointerId === event.pointerId) {
      setDragX(event.clientX - drag.current.startX);
    }
  }

  function onPointerEnd(event: ReactPointerEvent<HTMLDivElement>) {
    if (drag.current?.pointerId !== event.pointerId) {
      return;
    }
    // Measured from the event itself: after a fast flick, the dragX state
    // from the last render can lag behind where the pointer really is.
    const distance =
      event.type === "pointercancel" ? 0 : event.clientX - drag.current.startX;
    drag.current = null;
    setIsDragging(false);
    if (Math.abs(distance) >= SWIPE_DISTANCE) {
      setDragX(distance);
      decideOnCurrent(distance > 0 ? "LIKE" : "PASS");
    } else {
      setDragX(0);
    }
  }

  // --- What to show ------------------------------------------------------

  if (state.status === "incomplete") {
    return (
      <EmptyState
        icon={UserRound}
        title="Finish your profile first"
        description="Discover shows other students your profile and shows you theirs, so yours needs to be complete and published first."
        action={<ButtonLink href="/onboarding">Finish your profile</ButtonLink>}
        className="mx-auto max-w-md"
      />
    );
  }

  if (state.status === "error") {
    return (
      <ErrorState
        title="Discover could not load"
        description={state.message}
        onRetry={() => {
          setState({ status: "loading" });
          setAttempt((value) => value + 1);
        }}
        className="mx-auto max-w-md"
      />
    );
  }

  if (state.status === "loading") {
    return (
      <div className="mx-auto w-full max-w-md" aria-busy="true">
        <p role="status" className="sr-only">
          Loading profiles…
        </p>
        <Skeleton className="h-[30rem] w-full" />
        <div className="mt-4 grid grid-cols-2 gap-3">
          <Skeleton className="h-12" />
          <Skeleton className="h-12" />
        </div>
      </div>
    );
  }

  const areaBadge = current?.compatibility
    ? AREA_BADGES[current.compatibility.areaOverlap]
    : null;
  const leavingThis = leaving !== null && leaving.id === current?.profile.id;
  const direction =
    leaving?.decision === "LIKE" ? 1 : leaving?.decision === "PASS" ? -1 : 0;
  const hint = Math.min(1, Math.abs(dragX) / SWIPE_DISTANCE);

  return (
    <div className="mx-auto w-full max-w-md">
      <p aria-live="polite" className="sr-only">
        {announcement}
      </p>

      {!canDecide && (
        <Alert tone="warning" className="mb-4">
          Confirm your email address to like or pass. Until then you can look,
          and other students cannot see you yet.
        </Alert>
      )}
      {!hasSocieties && (
        <Alert tone="info" className="mb-4">
          None of your preferred societies are in the directory at the moment,
          so societies are not part of your scores.{" "}
          <Link href="/profile/edit" className="font-medium underline">
            Choose societies
          </Link>
        </Alert>
      )}
      {notice && (
        <Alert tone="warning" role="alert" className="mb-4">
          {notice}
        </Alert>
      )}

      {current ? (
        <>
          <p className="text-subtle mb-3 text-center text-sm">
            {state.remaining} {state.remaining === 1 ? "person" : "people"} left
            to see
          </p>
          {current.compatibility?.areaOverlap === "NONE" && hasSocieties && (
            <Alert tone="info" className="mb-4">
              You have seen everyone who shares your societies or areas. People
              from here on are looking elsewhere.{" "}
              <Link href="/profile/edit" className="font-medium underline">
                Edit your societies
              </Link>
            </Alert>
          )}

          <div ref={cardArea} className="relative scroll-mt-24">
            <div
              // A new element for each person, so the next card appears in
              // place instead of sliding back from where the last one left.
              key={current.profile.id}
              data-testid="discovery-card"
              onPointerDown={onPointerDown}
              onPointerMove={onPointerMove}
              onPointerUp={onPointerEnd}
              onPointerCancel={onPointerEnd}
              style={{
                transform: leavingThis
                  ? `translateX(${direction * 120}%) rotate(${direction * 6}deg)`
                  : `translateX(${dragX}px) rotate(${dragX / 40}deg)`,
                opacity: leavingThis ? 0 : 1,
              }}
              className={cn(
                "relative touch-pan-y select-none",
                canDecide && "cursor-grab active:cursor-grabbing",
                !isDragging &&
                  "transition-[transform,opacity] duration-200 ease-out motion-reduce:transition-none",
              )}
            >
              <div className="animate-card-in">
                <ProfileCard
                  candidate={current}
                  maxReasons={3}
                  badge={
                    areaBadge && (
                      <Badge tone={areaBadge.tone}>{areaBadge.label}</Badge>
                    )
                  }
                />
              </div>
              {/* What letting go will do, while a card is being dragged. */}
              <span
                aria-hidden="true"
                style={{ opacity: dragX > 0 ? hint : 0 }}
                className="bg-accent pointer-events-none absolute top-5 right-5 rounded-full px-3 py-1 text-sm font-semibold text-white"
              >
                Like
              </span>
              <span
                aria-hidden="true"
                style={{ opacity: dragX < 0 ? hint : 0 }}
                className="bg-foreground text-surface pointer-events-none absolute top-5 left-5 rounded-full px-3 py-1 text-sm font-semibold"
              >
                Pass
              </span>
            </div>
          </div>

          <div className="mt-2 text-center">
            <Link
              href={`/students/${current.profile.id}`}
              className="text-primary hover:text-primary-hover inline-block py-2 text-sm font-medium underline-offset-4 hover:underline"
            >
              View full profile
            </Link>
          </div>
          {/* Stays in reach at the bottom of the screen (above the phone's
              tab bar) while a long card is scrolled. */}
          <div className="bg-background/90 sticky bottom-[calc(4rem+env(safe-area-inset-bottom)+0.5rem)] z-10 mt-1 grid grid-cols-2 gap-3 rounded-2xl py-2 backdrop-blur-sm lg:bottom-4">
            <Button
              variant="secondary"
              size="lg"
              onClick={() => decideOnCurrent("PASS")}
              disabled={!canDecide || pending !== null || leaving !== null}
              isLoading={pending === "PASS"}
            >
              <X aria-hidden="true" className="size-5" />
              Pass
            </Button>
            <Button
              variant="accent"
              size="lg"
              onClick={() => decideOnCurrent("LIKE")}
              disabled={!canDecide || pending !== null || leaving !== null}
              isLoading={pending === "LIKE"}
            >
              <Heart aria-hidden="true" className="size-5" />
              Like
            </Button>
          </div>
          <p className="text-subtle mt-4 text-center text-xs leading-relaxed">
            The compatibility score is a guide to help you decide, not a
            guarantee that you will get along. They are not told when you pass.
          </p>
        </>
      ) : (
        <EmptyState
          icon={Sparkles}
          title="You're all caught up"
          description="There is nobody new to show you right now. New students join over time, so check back soon."
          action={
            <div className="flex flex-col items-center gap-3 sm:flex-row">
              <ButtonLink href="/matches">See your matches</ButtonLink>
              <Button
                variant="ghost"
                onClick={() => {
                  setState({ status: "loading" });
                  setAttempt((value) => value + 1);
                }}
              >
                <RotateCcw aria-hidden="true" className="size-4" />
                Check again
              </Button>
            </div>
          }
        />
      )}

      <MatchDialog name={matchedWith} onClose={closeMatch} />
    </div>
  );
}
