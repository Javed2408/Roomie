"use client";

import { MapPin, Pencil, UserRound } from "lucide-react";
import type { ReactNode } from "react";

import { useSession } from "@/components/session/session-provider";
import { ProfilePhotoControls } from "@/components/profile/profile-photo";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { ButtonLink } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/states";
import {
  GENDER_LABELS,
  OWN_VERIFICATION_TEXT,
  lifestyleAnswers,
  roomTypeLabel,
} from "@/lib/account-display";
import { formatAcademicYear, formatDate, formatInrRange } from "@/lib/format";
import type { OwnVerification } from "@/types/account";

function Detail({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-subtle text-xs">{label}</dt>
      <dd className="text-foreground mt-0.5 text-sm font-medium">
        {children ?? <span className="text-subtle font-normal">Not set</span>}
      </dd>
    </div>
  );
}

function VerificationRow({
  name,
  verification,
}: {
  name: string;
  verification: OwnVerification;
}) {
  const { label, tone } = OWN_VERIFICATION_TEXT[verification.status];
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-foreground text-sm font-medium">{name}</span>
      <Badge tone={tone}>{label}</Badge>
    </div>
  );
}

/** The signed-in person's own profile, read from their saved account. */
export function ProfileOverview() {
  const { account } = useSession();
  const { profile, preferences, societies, verifications } = account;

  if (profile === null) {
    return (
      <EmptyState
        icon={UserRound}
        title="You have not set up your profile yet"
        description="Tell other students a little about yourself, your budget and where you would like to live."
        action={<ButtonLink href="/onboarding">Set up your profile</ButtonLink>}
      />
    );
  }

  const headline = [
    profile.academicYear ? formatAcademicYear(profile.academicYear) : null,
    [profile.course, profile.department].filter(Boolean).join(" ") || null,
  ]
    .filter(Boolean)
    .join(" · ");
  const lifestyle = lifestyleAnswers(account);
  const hasBudget =
    preferences?.minBudget != null && preferences.maxBudget != null;

  return (
    <>
      <div className="mb-5 flex flex-wrap gap-3">
        <ButtonLink href="/profile/edit">
          <Pencil aria-hidden="true" className="size-4" />
          Edit profile
        </ButtonLink>
        {!profile.profileCompleted && (
          <ButtonLink href="/onboarding" variant="secondary">
            Finish setting up
          </ButtonLink>
        )}
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <div className="space-y-5 lg:col-span-2">
          <Card>
            <div className="flex items-center gap-4">
              <Avatar
                name={profile.fullName}
                src={profile.photoUrl}
                size="xl"
              />
              <div className="min-w-0">
                <h2 className="truncate text-xl font-semibold">
                  {profile.fullName}
                </h2>
                {headline && <p className="text-muted text-sm">{headline}</p>}
                <p className="text-subtle truncate text-sm">
                  {profile.collegeName}
                </p>
              </div>
            </div>
            <ProfilePhotoControls hasPhoto={profile.photoUrl !== null} />
            {profile.bio && (
              <p className="text-muted mt-5 leading-relaxed whitespace-pre-line">
                {profile.bio}
              </p>
            )}
          </Card>

          <Card>
            <h2 className="text-lg font-semibold">Accommodation preferences</h2>
            <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-4 sm:grid-cols-3">
              <Detail label="Budget per month">
                {hasBudget
                  ? formatInrRange(
                      preferences.minBudget ?? 0,
                      preferences.maxBudget ?? 0,
                    )
                  : null}
              </Detail>
              <Detail label="Move-in date">
                {preferences?.moveInDate
                  ? formatDate(preferences.moveInDate)
                  : null}
              </Detail>
              <Detail label="Room">{roomTypeLabel(account)}</Detail>
            </dl>
          </Card>

          <Card>
            <h2 className="text-lg font-semibold">Lifestyle</h2>
            {lifestyle.length > 0 ? (
              <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-4 sm:grid-cols-3">
                {lifestyle.map((answer) => (
                  <Detail key={answer.label} label={answer.label}>
                    {answer.value}
                  </Detail>
                ))}
              </dl>
            ) : (
              <p className="text-muted mt-2 text-sm leading-relaxed">
                You have not answered any lifestyle questions yet. They help
                find people whose routines fit with yours.
              </p>
            )}
          </Card>
        </div>

        <div className="space-y-5">
          <Card>
            <h2 className="text-lg font-semibold">Preferred societies</h2>
            {societies.length > 0 ? (
              <ol className="mt-4 space-y-3">
                {societies.map(({ society, priority, available }) => (
                  <li key={society.id} className="flex items-center gap-3">
                    <span
                      aria-hidden="true"
                      className="font-display bg-primary-soft text-primary-strong flex size-7 shrink-0 items-center justify-center rounded-full text-sm font-semibold"
                    >
                      {priority}
                    </span>
                    <span className="min-w-0">
                      <span className="text-foreground block text-sm font-medium">
                        {society.name}
                      </span>
                      <span className="text-subtle flex items-center gap-1 text-xs">
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
              <p className="text-muted mt-2 text-sm">None chosen yet.</p>
            )}
          </Card>

          <Card>
            <h2 className="text-lg font-semibold">Verification</h2>
            <p className="text-muted mt-1 text-sm leading-relaxed">
              Two separate checks. Each is reviewed by a person.
            </p>
            <div className="mt-4 space-y-3">
              <VerificationRow
                name="Identity"
                verification={verifications.identity}
              />
              <VerificationRow
                name="Student status"
                verification={verifications.student}
              />
            </div>
            <ButtonLink
              href="/profile/verification"
              variant="secondary"
              fullWidth
              className="mt-5"
            >
              Manage verification
            </ButtonLink>
          </Card>

          <Card>
            <h2 className="text-lg font-semibold">Privacy</h2>
            <p className="text-muted mt-2 text-sm leading-relaxed">
              Your email, contact details and exact address are never shown on
              your public profile.{" "}
              {profile.gender
                ? `Your gender (${GENDER_LABELS[profile.gender] ?? profile.gender}) is ${
                    profile.genderVisible ? "shown" : "kept private"
                  }.`
                : ""}
            </p>
          </Card>
        </div>
      </div>
    </>
  );
}
