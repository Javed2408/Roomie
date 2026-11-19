import {
  BedDouble,
  CalendarDays,
  MapPin,
  Wallet,
  type LucideIcon,
} from "lucide-react";
import type { ReactNode } from "react";

import { CompatibilityScore } from "@/components/discovery/compatibility-score";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { VerificationStatus } from "@/components/verification/verification-status";
import { cn } from "@/lib/cn";
import { unavailableLabels } from "@/lib/compatibility";
import { formatAcademicYear, formatDate, formatInrRange } from "@/lib/format";
import {
  CLEANLINESS_LABELS,
  FOOD_LABELS,
  ROOM_TYPE_LABELS,
  SLEEP_LABELS,
  SOCIAL_LABELS,
  type DiscoveryCandidate,
  type StudentProfile,
} from "@/types/profile";

const NOT_SET = "Not set";

function Fact({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-start gap-2.5">
      <Icon aria-hidden="true" className="text-subtle mt-0.5 size-4 shrink-0" />
      <div className="min-w-0">
        <dt className="text-subtle text-xs">{label}</dt>
        <dd className="text-foreground text-sm font-medium">{value}</dd>
      </div>
    </div>
  );
}

/** "2nd year · B.Tech Computer Science", leaving out what is missing. */
export function studySummary(
  profile: Pick<StudentProfile, "academicYear" | "course" | "department">,
): string {
  const subject = [profile.course, profile.department]
    .filter(Boolean)
    .join(" ");
  return [
    profile.academicYear ? formatAcademicYear(profile.academicYear) : null,
    subject || null,
  ]
    .filter(Boolean)
    .join(" · ");
}

interface ProfileCardProps {
  candidate: DiscoveryCandidate;
  /** A shorter version, used as a preview on the landing page. */
  compact?: boolean;
  /** Something to show beside the name, such as "Looking elsewhere". */
  badge?: ReactNode;
  /**
   * Show at most this many reasons for and against. The full profile has
   * the complete breakdown, so cards stay short enough to decide on.
   */
  maxReasons?: number;
  className?: string;
}

/**
 * A roommate profile as it appears in Discover.
 *
 * Privacy: this card shows only what the PRD allows on a discovery card.
 * It never shows a date of birth, contact details or an address. Answers
 * the student left blank show as "Not set" and are never guessed.
 */
export function ProfileCard({
  candidate,
  compact = false,
  badge,
  maxReasons,
  className,
}: ProfileCardProps) {
  const { profile, compatibilityScore, positives, cautions } = candidate;
  const { preferences } = profile;

  const societies = [...profile.societyPreferences]
    .sort((a, b) => a.priority - b.priority)
    .map((preference) => preference.society.name);

  const lifestyle = [
    preferences.foodPreference && FOOD_LABELS[preferences.foodPreference],
    preferences.sleepSchedule && SLEEP_LABELS[preferences.sleepSchedule],
    preferences.cleanliness && CLEANLINESS_LABELS[preferences.cleanliness],
    preferences.socialPreference && SOCIAL_LABELS[preferences.socialPreference],
  ].filter((item): item is string => Boolean(item));

  const budget =
    preferences.minBudget !== null && preferences.maxBudget !== null
      ? formatInrRange(preferences.minBudget, preferences.maxBudget)
      : NOT_SET;
  const study = studySummary(profile);

  return (
    <Card padding="none" elevated className={cn("overflow-hidden", className)}>
      <div className="flex items-center gap-4 p-5">
        <Avatar
          name={profile.fullName}
          src={profile.photoUrl}
          size={compact ? "lg" : "xl"}
        />
        <div className="min-w-0">
          <h3 className="truncate text-xl font-semibold">{profile.fullName}</h3>
          {study && <p className="text-muted text-sm">{study}</p>}
          <p className="text-subtle truncate text-sm">{profile.collegeName}</p>
          {badge && <div className="mt-1.5">{badge}</div>}
        </div>
      </div>

      <div className="space-y-5 px-5 pb-5">
        <CompatibilityScore
          score={compatibilityScore}
          positives={positives.slice(0, compact ? 2 : maxReasons)}
          cautions={compact ? [] : cautions.slice(0, maxReasons)}
          unavailable={
            !compact && candidate.compatibility
              ? unavailableLabels(candidate.compatibility)
              : []
          }
        />

        <dl className="grid grid-cols-2 gap-x-4 gap-y-3.5">
          <Fact icon={Wallet} label="Budget / month" value={budget} />
          <Fact
            icon={CalendarDays}
            label="Move-in"
            value={
              preferences.moveInDate
                ? formatDate(preferences.moveInDate)
                : NOT_SET
            }
          />
          {!compact && (
            <Fact
              icon={BedDouble}
              label="Room"
              value={
                preferences.roomType
                  ? ROOM_TYPE_LABELS[preferences.roomType]
                  : NOT_SET
              }
            />
          )}
          <div className={cn(compact ? "col-span-2" : undefined)}>
            <Fact
              icon={MapPin}
              label="Preferred societies"
              value={societies.length > 0 ? societies.join(", ") : NOT_SET}
            />
          </div>
        </dl>

        {!compact && (
          <>
            {profile.bio && (
              <p className="text-muted text-sm leading-relaxed">
                {profile.bio}
              </p>
            )}
            {lifestyle.length > 0 && (
              <ul aria-label="Lifestyle" className="flex flex-wrap gap-2">
                {lifestyle.map((item) => (
                  <li key={item}>
                    <Badge>{item}</Badge>
                  </li>
                ))}
              </ul>
            )}
            <div className="flex flex-col gap-1">
              <VerificationStatus
                kind="IDENTITY"
                state={profile.identityVerification}
              />
              <VerificationStatus
                kind="STUDENT"
                state={profile.studentVerification}
              />
            </div>
          </>
        )}
      </div>
    </Card>
  );
}
