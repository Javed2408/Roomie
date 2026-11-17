"use client";

import { ArrowLeft, ArrowRight } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { SuccessPanel } from "@/components/auth/success-panel";
import { ProfileStepFields } from "@/components/profile/profile-fields";
import { useSession } from "@/components/session/session-provider";
import { Alert } from "@/components/ui/alert";
import { Button, ButtonLink } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useForm } from "@/hooks/use-form";
import { formatDate, formatInrRange } from "@/lib/format";
import {
  PROFILE_OPTIONS,
  PROFILE_STEPS,
  accountToFormValues,
  parseWholeNumber,
  saveProfileStep,
  validateProfile,
  type ProfileFormValues,
} from "@/lib/profile-form";
import { publishProfile } from "@/services/account";
import { describeApiError } from "@/services/api-client";

/** Find the display label for a stored option value. */
function labelFor(
  options: Array<{ value: string; label: string }>,
  value: string,
): string {
  return options.find((option) => option.value === value)?.label ?? "";
}

function ReviewRow({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="grid grid-cols-[8rem_1fr] gap-3 py-2 text-sm">
      <dt className="text-subtle">{label}</dt>
      <dd className="text-foreground font-medium">
        {children || <span className="text-subtle font-normal">Not given</span>}
      </dd>
    </div>
  );
}

/** The last step: a summary of what other students will see. */
function Review({
  values,
  societyNames,
  onEdit,
}: {
  values: ProfileFormValues;
  /** Society id -> name, for showing the chosen societies. */
  societyNames: Map<string, string>;
  onEdit: (stepIndex: number) => void;
}) {
  const min = parseWholeNumber(values.minBudget);
  const max = parseWholeNumber(values.maxBudget);
  const lifestyle = [
    labelFor(PROFILE_OPTIONS.food, values.foodPreference),
    labelFor(PROFILE_OPTIONS.sleep, values.sleepSchedule),
    labelFor(PROFILE_OPTIONS.cleanliness, values.cleanliness),
    labelFor(PROFILE_OPTIONS.social, values.socialPreference),
    labelFor(PROFILE_OPTIONS.guests, values.guestFrequency),
  ].filter(Boolean);

  const groups: Array<{ stepIndex: number; title: string; rows: ReactNode }> = [
    {
      stepIndex: 0,
      title: "Student details",
      rows: (
        <>
          <ReviewRow label="Name">{values.fullName}</ReviewRow>
          <ReviewRow label="College">{values.collegeName}</ReviewRow>
          <ReviewRow label="Course">
            {[values.course, values.department].filter(Boolean).join(", ")}
          </ReviewRow>
          <ReviewRow label="Year">
            {labelFor(PROFILE_OPTIONS.academicYear, values.academicYear)}
          </ReviewRow>
        </>
      ),
    },
    {
      stepIndex: 1,
      title: "About you",
      rows: (
        <>
          <ReviewRow label="Bio">{values.bio}</ReviewRow>
          <ReviewRow label="Gender">
            {values.gender
              ? `${labelFor(PROFILE_OPTIONS.gender, values.gender)} (${
                  values.showGender ? "shown on profile" : "kept private"
                })`
              : ""}
          </ReviewRow>
        </>
      ),
    },
    {
      stepIndex: 2,
      title: "Budget and move-in",
      rows: (
        <>
          <ReviewRow label="Budget">
            {min !== null && max !== null
              ? `${formatInrRange(min, max)} / month`
              : ""}
          </ReviewRow>
          <ReviewRow label="Move-in">
            {values.moveInDate ? formatDate(values.moveInDate) : ""}
          </ReviewRow>
          <ReviewRow label="Room">
            {labelFor(PROFILE_OPTIONS.roomType, values.roomType)}
          </ReviewRow>
        </>
      ),
    },
    {
      stepIndex: 3,
      title: "Preferred societies",
      rows: (
        <ReviewRow label="In order">
          {values.societyIds
            .map((id, index) => `${index + 1}. ${societyNames.get(id) ?? id}`)
            .join("  ")}
        </ReviewRow>
      ),
    },
    {
      stepIndex: 4,
      title: "Lifestyle",
      rows: <ReviewRow label="Answers">{lifestyle.join(", ")}</ReviewRow>,
    },
  ];

  return (
    <div className="space-y-5">
      {groups.map((group) => (
        <section key={group.title}>
          <div className="border-border flex items-center justify-between gap-3 border-b pb-1">
            <h3 className="text-base font-semibold">{group.title}</h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onEdit(group.stepIndex)}
              aria-label={`Edit ${group.title}`}
            >
              Edit
            </Button>
          </div>
          <dl>{group.rows}</dl>
        </section>
      ))}
      <p className="text-muted text-sm leading-relaxed">
        Your date of birth, contact details and exact address are never part of
        your public profile.
      </p>
    </div>
  );
}

/** The first step that still needs something, or the review step. */
function firstUnfinishedStep(values: ProfileFormValues): number {
  const errors = validateProfile(values);
  const index = PROFILE_STEPS.findIndex((step) =>
    step.fields.some((field) => errors[field]),
  );
  return index === -1 ? PROFILE_STEPS.length : index;
}

/**
 * Onboarding: the profile, asked for one small section at a time.
 *
 * "Continue" checks the current step's fields and then saves that step to
 * the backend straight away. Progress is therefore never lost: someone who
 * closes the browser halfway returns to the first step they have not
 * finished. "Publish" asks the backend to mark the profile complete, which
 * it only does if everything required is really there.
 */
export function OnboardingWizard() {
  const { account, setAccount } = useSession();
  const reviewIndex = PROFILE_STEPS.length;
  const totalSteps = PROFILE_STEPS.length + 1;

  // Worked out once, from what was already saved when the page opened.
  const [startingValues] = useState(() => accountToFormValues(account));
  const [stepIndex, setStepIndex] = useState(() =>
    firstUnfinishedStep(startingValues),
  );
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [isPublished, setIsPublished] = useState(false);
  const fieldsRef = useRef<HTMLDivElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const isFirstRender = useRef(true);

  const form = useForm<ProfileFormValues>({
    initialValues: startingValues,
    validate: validateProfile,
    // Saving is handled step by step below, not by one form submit.
    onSubmit: async () => ({ ok: true }),
  });

  // When the step changes, move focus to its heading so screen-reader and
  // keyboard users land at the top of the new step, not on a stale button.
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    headingRef.current?.focus();
  }, [stepIndex]);

  const step = PROFILE_STEPS[stepIndex];
  const isReview = stepIndex === reviewIndex;
  // The societies step is saved before the review step, so the saved
  // account always has the names the review needs.
  const societyNames = new Map(
    account.societies.map((item) => [item.society.id, item.society.name]),
  );

  function goTo(index: number) {
    setSaveError(null);
    setStepIndex(index);
  }

  async function goNext() {
    if (!step || isSaving) {
      return;
    }
    if (!form.validateFields(step.fields, fieldsRef.current)) {
      return;
    }
    setIsSaving(true);
    setSaveError(null);
    try {
      setAccount(await saveProfileStep(step.id, form.values));
      setStepIndex((current) => Math.min(current + 1, reviewIndex));
    } catch (error) {
      setSaveError(describeApiError(error));
    } finally {
      setIsSaving(false);
    }
  }

  async function publish() {
    setIsSaving(true);
    setSaveError(null);
    try {
      setAccount(await publishProfile());
      setIsPublished(true);
    } catch (error) {
      setSaveError(describeApiError(error));
    } finally {
      setIsSaving(false);
    }
  }

  if (isPublished) {
    return (
      <SuccessPanel
        title="Your profile is ready"
        actions={
          <ButtonLink href="/dashboard" size="lg" fullWidth>
            Go to your dashboard
          </ButtonLink>
        }
      >
        <p>
          Your profile is saved and complete. You can change any of it later
          from the Profile page.
        </p>
      </SuccessPanel>
    );
  }
  const progress = Math.round(((stepIndex + 1) / totalSteps) * 100);

  return (
    <div>
      <p className="text-muted text-sm font-medium">
        Step {stepIndex + 1} of {totalSteps}
      </p>
      <div
        role="progressbar"
        aria-label="Onboarding progress"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={progress}
        className="bg-surface-muted mt-2 h-2 overflow-hidden rounded-full"
      >
        <div
          className="bg-primary h-full rounded-full transition-[width] duration-200"
          style={{ width: `${progress}%` }}
        />
      </div>

      <h1
        ref={headingRef}
        tabIndex={-1}
        className="mt-6 text-2xl font-semibold outline-none sm:text-3xl"
      >
        {isReview ? "Review your profile" : step?.title}
      </h1>
      <p className="text-muted mt-2 leading-relaxed">
        {isReview
          ? "This is what other students will see. You can change anything later."
          : step?.description}
      </p>

      {/* Enter in a text field should move forward, not reload the page. */}
      <form
        {...form.formProps}
        onSubmit={(event) => {
          event.preventDefault();
          if (!isReview) {
            void goNext();
          }
        }}
        className="mt-6"
      >
        <Card padding="lg">
          <div ref={fieldsRef}>
            {isReview ? (
              <Review
                values={form.values}
                societyNames={societyNames}
                onEdit={goTo}
              />
            ) : (
              step && <ProfileStepFields stepId={step.id} form={form} />
            )}
          </div>
        </Card>

        {saveError && (
          <Alert
            tone="danger"
            role="alert"
            title="This step was not saved"
            className="mt-4"
          >
            {saveError}
          </Alert>
        )}

        <div className="mt-6 flex items-center justify-between gap-3">
          {stepIndex > 0 ? (
            <Button variant="ghost" onClick={() => goTo(stepIndex - 1)}>
              <ArrowLeft aria-hidden="true" className="size-4" />
              Back
            </Button>
          ) : (
            <span />
          )}
          {isReview ? (
            <Button onClick={() => void publish()} isLoading={isSaving}>
              Publish profile
            </Button>
          ) : (
            <Button type={form.submitType} isLoading={isSaving}>
              Continue
              <ArrowRight aria-hidden="true" className="size-4" />
            </Button>
          )}
        </div>
      </form>
    </div>
  );
}
