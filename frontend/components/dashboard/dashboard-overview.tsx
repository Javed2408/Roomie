"use client";

import {
  ArrowRight,
  Building2,
  Check,
  Circle,
  Compass,
  Heart,
  MapPin,
  MessageCircle,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/app-shell/page-header";
import { useSession } from "@/components/session/session-provider";
import { Badge } from "@/components/ui/badge";
import { Button, ButtonLink } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { SampleDataBadge } from "@/components/ui/sample-data-badge";
import { profileChecklist } from "@/lib/account-display";
import { formatTimestampDate } from "@/lib/format";
import { LISTINGS } from "@/lib/mock/listings";
import { CONVERSATIONS } from "@/lib/mock/matches";
import {
  fetchDiscovery,
  fetchMatches,
  fetchNotifications,
  markAllNotificationsRead,
} from "@/services/discovery";
import type { AppNotification } from "@/types/discovery";

interface SectionLink {
  href: string;
  icon: LucideIcon;
  title: string;
  status: string;
  /** Still shows invented data: built in a later roadmap phase. */
  sample?: boolean;
}

const UNREAD_SAMPLE_MESSAGES = CONVERSATIONS.reduce(
  (total, conversation) => total + conversation.unreadCount,
  0,
);

/** Real counts for Discover and Matches, and unread notifications. */
interface Overview {
  /** People left to discover; null when the profile is not published. */
  toDiscover: number | null;
  matches: number;
  notifications: AppNotification[];
}

function useOverview(isPublished: boolean) {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    const { signal } = controller;
    Promise.all([
      isPublished
        ? fetchDiscovery({ limit: 1, signal }).then((page) => page.remaining)
        : Promise.resolve(null),
      fetchMatches(signal),
      fetchNotifications(signal),
    ])
      .then(([toDiscover, matches, inbox]) =>
        setOverview({
          toDiscover,
          matches: matches.length,
          notifications: inbox.notifications.filter((item) => !item.isRead),
        }),
      )
      .catch(() => {
        if (!signal.aborted) {
          setFailed(true);
        }
      });
    return () => controller.abort();
  }, [isPublished]);

  return {
    overview,
    failed,
    clearNotifications: () =>
      setOverview((current) =>
        current ? { ...current, notifications: [] } : current,
      ),
  };
}

function plural(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`;
}

function sectionsFor(
  overview: Overview | null,
  failed: boolean,
  isPublished: boolean,
): SectionLink[] {
  const unknown = failed ? "Open to see" : "Loading…";
  let discoverStatus = unknown;
  if (!isPublished) {
    discoverStatus = "Publish your profile to start";
  } else if (overview?.toDiscover != null) {
    discoverStatus = `${plural(overview.toDiscover, "person", "people")} to discover`;
  }
  return [
    {
      href: "/discover",
      icon: Compass,
      title: "Discover",
      status: discoverStatus,
    },
    {
      href: "/accommodation",
      icon: Building2,
      title: "Accommodation",
      status: `${LISTINGS.length} posts to browse`,
      sample: true,
    },
    {
      href: "/matches",
      icon: Heart,
      title: "Matches",
      status: overview ? plural(overview.matches, "match", "matches") : unknown,
    },
    {
      href: "/messages",
      icon: MessageCircle,
      title: "Messages",
      status: `${UNREAD_SAMPLE_MESSAGES} unread`,
      sample: true,
    },
  ];
}

function SectionCard({ href, icon: Icon, title, status, sample }: SectionLink) {
  return (
    <Link
      href={href}
      className="group rounded-card border-border bg-surface hover:border-primary flex h-full items-start gap-4 border p-5 transition-colors duration-150"
    >
      <span className="bg-primary-soft text-primary-strong flex size-11 shrink-0 items-center justify-center rounded-full">
        <Icon aria-hidden="true" className="size-5" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="font-display text-foreground block text-lg font-semibold">
          {title}
        </span>
        <span className="text-muted mt-0.5 block text-sm">{status}</span>
        {sample && <SampleDataBadge className="mt-2" />}
      </span>
      <ArrowRight
        aria-hidden="true"
        className="text-subtle group-hover:text-primary mt-1 size-5 shrink-0 transition-colors duration-150"
      />
    </Link>
  );
}

export function DashboardOverview() {
  const { account } = useSession();
  const firstName = account.profile?.fullName.split(" ")[0];
  const checklist = profileChecklist(account);
  const completedSteps = checklist.filter((item) => item.isComplete).length;
  const completion = Math.round((completedSteps / checklist.length) * 100);
  const isComplete = completedSteps === checklist.length;
  const isPublished = account.profile?.profileCompleted === true;
  const { overview, failed, clearNotifications } = useOverview(isPublished);
  const sections = sectionsFor(overview, failed, isPublished);

  return (
    <>
      <PageHeader
        title={firstName ? `Welcome back, ${firstName}` : "Welcome to Roomie"}
        description="Here is where things stand with your roommate search."
      />

      <div className="grid gap-5 lg:grid-cols-3 lg:items-start">
        <div className="space-y-5 lg:col-span-2">
          <section aria-labelledby="sections-heading">
            <h2 id="sections-heading" className="mb-3 text-lg font-semibold">
              Explore
            </h2>
            <ul className="grid gap-5 sm:grid-cols-2">
              {sections.map((section) => (
                <li key={section.href}>
                  <SectionCard {...section} />
                </li>
              ))}
            </ul>
          </section>

          <Card>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-semibold">
                Your preferred societies
              </h2>
              <Link
                href="/profile/edit"
                className="text-primary hover:text-primary-hover py-1 text-sm font-medium underline-offset-4 hover:underline"
              >
                Manage
              </Link>
            </div>
            {account.societies.length > 0 ? (
              <ol className="mt-4 grid gap-3 sm:grid-cols-3">
                {account.societies.map(({ society, priority, available }) => (
                  <li
                    key={society.id}
                    className="bg-background rounded-control flex items-center gap-3 px-3.5 py-3"
                  >
                    <span
                      aria-hidden="true"
                      className="font-display bg-primary-soft text-primary-strong flex size-7 shrink-0 items-center justify-center rounded-full text-sm font-semibold"
                    >
                      {priority}
                    </span>
                    <span className="min-w-0">
                      <span className="text-foreground block text-sm leading-snug font-medium">
                        {society.name}
                      </span>
                      <span className="text-subtle mt-0.5 flex items-center gap-1 text-xs">
                        <MapPin aria-hidden="true" className="size-3" />
                        {society.locality.name}
                      </span>
                      {!available && (
                        <Badge tone="warning" className="mt-1">
                          No longer available
                        </Badge>
                      )}
                    </span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="text-muted mt-3 text-sm leading-relaxed">
                You have not chosen any societies yet. Roomie shows you people
                looking in the same places first.
              </p>
            )}
          </Card>
        </div>

        <div className="space-y-5">
          <NotificationsCard
            notifications={overview?.notifications ?? null}
            failed={failed}
            onAllRead={clearNotifications}
          />

          <Card className="flex flex-col">
            <h2 className="text-lg font-semibold">
              {isComplete ? "Your profile is complete" : "Finish your profile"}
            </h2>
            <p className="text-muted mt-1 text-sm leading-relaxed">
              Complete profiles get better matches.
            </p>

            <div className="mt-4 flex items-baseline justify-between text-sm">
              <span className="text-foreground font-medium">
                {completedSteps} of {checklist.length} steps done
              </span>
              <span className="text-muted tabular-nums">{completion}%</span>
            </div>
            <div
              role="progressbar"
              aria-label="Profile completion"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={completion}
              className="bg-surface-muted mt-2 h-2 overflow-hidden rounded-full"
            >
              <div
                className="bg-primary h-full rounded-full"
                style={{ width: `${completion}%` }}
              />
            </div>

            <ul className="mt-5 space-y-2.5">
              {checklist.map((item) => (
                <li key={item.id} className="flex items-center gap-2.5 text-sm">
                  {item.isComplete ? (
                    <Check
                      aria-hidden="true"
                      className="text-primary size-4 shrink-0"
                    />
                  ) : (
                    <Circle
                      aria-hidden="true"
                      className="text-border-strong size-4 shrink-0"
                    />
                  )}
                  <span
                    className={
                      item.isComplete ? "text-muted" : "text-foreground"
                    }
                  >
                    {item.label}
                    <span className="sr-only">
                      {item.isComplete ? " (done)" : " (not done yet)"}
                    </span>
                  </span>
                </li>
              ))}
            </ul>

            <ButtonLink
              href={isComplete ? "/profile" : "/onboarding"}
              variant={isComplete ? "secondary" : "primary"}
              fullWidth
              className="mt-6"
            >
              {isComplete ? "View your profile" : "Continue setting up"}
            </ButtonLink>
          </Card>
        </div>
      </div>
    </>
  );
}

/** Unread in-app notifications, such as a new match. */
function NotificationsCard({
  notifications,
  failed,
  onAllRead,
}: {
  /** null while loading. */
  notifications: AppNotification[] | null;
  failed: boolean;
  onAllRead: () => void;
}) {
  const [isClearing, setIsClearing] = useState(false);
  const [clearFailed, setClearFailed] = useState(false);

  async function markAllRead() {
    setIsClearing(true);
    setClearFailed(false);
    try {
      await markAllNotificationsRead();
      onAllRead();
    } catch {
      setClearFailed(true);
    } finally {
      setIsClearing(false);
    }
  }

  let content;
  if (notifications === null) {
    content = (
      <p className="text-muted mt-2 text-sm">
        {failed ? "Notifications could not load." : "Loading…"}
      </p>
    );
  } else if (notifications.length === 0) {
    content = <p className="text-muted mt-2 text-sm">Nothing new.</p>;
  } else {
    content = (
      <ul className="mt-3 space-y-1">
        {notifications.slice(0, 5).map((item) => (
          <li key={item.id}>
            <Link
              href={item.type === "NEW_MATCH" ? "/matches" : "/dashboard"}
              className="hover:bg-surface-muted -mx-2 block rounded-lg px-2 py-1.5 transition-colors duration-150"
            >
              <span className="text-foreground block text-sm font-medium">
                {item.title}
              </span>
              <span className="text-muted block text-sm">{item.body}</span>
              <span className="text-subtle block text-xs">
                {formatTimestampDate(item.createdAt)}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    );
  }

  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">Notifications</h2>
        {notifications && notifications.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => void markAllRead()}
            isLoading={isClearing}
          >
            Mark all as read
          </Button>
        )}
      </div>
      {content}
      {clearFailed && (
        <p role="alert" className="text-danger mt-2 text-sm">
          That did not work. Please try again.
        </p>
      )}
    </Card>
  );
}
