"use client";

import { SocietyPicker } from "@/components/profile/society-picker";
import { useSession } from "@/components/session/session-provider";
import { Alert } from "@/components/ui/alert";
import { Avatar } from "@/components/ui/avatar";
import { Checkbox } from "@/components/ui/checkbox";
import { ChoiceGroup } from "@/components/ui/choice-group";
import { SelectField } from "@/components/ui/select-field";
import { TextField } from "@/components/ui/text-field";
import { TextAreaField } from "@/components/ui/textarea-field";
import type { UseFormResult } from "@/hooks/use-form";
import {
  BIO_MAX_LENGTH,
  MAX_SOCIETIES,
  PROFILE_OPTIONS,
  type ProfileFormValues,
  type ProfileStep,
} from "@/lib/profile-form";

/*
 * The groups of fields that make up a profile. Each group is used twice:
 * as a card in the profile editor and as a step in onboarding.
 */

interface FieldsProps {
  form: UseFormResult<ProfileFormValues>;
}

function StudentDetailsFields({ form }: FieldsProps) {
  return (
    <div className="grid gap-x-4 gap-y-2 sm:grid-cols-2">
      <TextField
        label="Full name"
        autoComplete="name"
        className="sm:col-span-2"
        {...form.text("fullName")}
      />
      <TextField
        label="College or university"
        autoComplete="organization"
        className="sm:col-span-2"
        {...form.text("collegeName")}
      />
      <TextField
        label="Course (optional)"
        hint="For example B.Tech or B.Des."
        {...form.text("course")}
      />
      <TextField label="Department (optional)" {...form.text("department")} />
      <SelectField
        label="Year (optional)"
        placeholder="Prefer not to say"
        options={PROFILE_OPTIONS.academicYear}
        {...form.text("academicYear")}
      />
    </div>
  );
}

function AboutFields({ form }: FieldsProps) {
  return (
    <div className="space-y-2">
      <div className="mb-4 flex items-center gap-4">
        <Avatar name={form.values.fullName || "Roomie"} size="lg" />
        <p className="text-muted text-sm leading-relaxed">
          Photo upload is coming soon. Until then your initials are shown.
        </p>
      </div>
      <TextAreaField
        label="Bio (optional)"
        hint="What are you like to live with?"
        maxLength={BIO_MAX_LENGTH}
        {...form.text("bio")}
      />
      <SelectField
        label="Gender (optional)"
        placeholder="Prefer not to say"
        options={PROFILE_OPTIONS.gender}
        {...form.text("gender")}
      />
      <Checkbox
        name="showGender"
        checked={form.values.showGender}
        onChange={(event) => form.setValue("showGender", event.target.checked)}
      >
        Show my gender on my profile. It stays private unless you tick this.
      </Checkbox>
    </div>
  );
}

function AccommodationFields({ form }: FieldsProps) {
  return (
    <div className="grid gap-x-4 gap-y-2 sm:grid-cols-2">
      <TextField
        label="Minimum budget (₹ / month)"
        inputMode="numeric"
        {...form.text("minBudget")}
      />
      <TextField
        label="Maximum budget (₹ / month)"
        inputMode="numeric"
        {...form.text("maxBudget")}
      />
      <TextField
        label="Move-in date"
        type="date"
        {...form.text("moveInDate")}
      />
      <SelectField
        label="Room (optional)"
        placeholder="Not sure yet"
        options={PROFILE_OPTIONS.roomType}
        {...form.text("roomType")}
      />
    </div>
  );
}

function SocietiesFields({ form }: FieldsProps) {
  const { account } = useSession();
  // Saved choices that have since left the directory. They are left out
  // of the form (see accountToFormValues) and named here, so nothing
  // disappears without the person being told.
  const unavailable = account.societies.filter((item) => !item.available);

  return (
    <div className="space-y-4">
      {unavailable.length > 0 && (
        <Alert tone="warning" title="Some of your choices are no longer listed">
          {unavailable.map((item) => item.society.name).join(", ")}{" "}
          {unavailable.length === 1 ? "is" : "are"} no longer in Roomie&apos;s
          directory, so {unavailable.length === 1 ? "it has" : "they have"} been
          left out below. Save to update your list.
        </Alert>
      )}
      <SocietyPicker
        label="Societies you would like to live in"
        name="societyIds"
        value={form.values.societyIds}
        onChange={(ids) => {
          form.setValue("societyIds", ids);
          form.markTouched("societyIds");
        }}
        savedSocieties={account.societies.map((item) => item.society)}
        max={MAX_SOCIETIES}
        hint={`Choose up to ${MAX_SOCIETIES}. Use the arrows to set your order.`}
        error={form.errors.societyIds}
      />
    </div>
  );
}

function LifestyleFields({ form }: FieldsProps) {
  const choice = (
    name:
      | "foodPreference"
      | "sleepSchedule"
      | "cleanliness"
      | "socialPreference"
      | "guestFrequency"
      | "smoking"
      | "drinking",
  ) => ({
    name,
    value: form.values[name],
    onChange: (value: string) => form.setValue(name, value),
  });

  return (
    <div className="space-y-3">
      <Alert tone="info">
        Answer for yourself, as honestly as you can. Nothing here is used to
        guess anything else about you.
      </Alert>
      <ChoiceGroup
        label="Food"
        options={PROFILE_OPTIONS.food}
        {...choice("foodPreference")}
      />
      <ChoiceGroup
        label="Sleep schedule"
        options={PROFILE_OPTIONS.sleep}
        {...choice("sleepSchedule")}
      />
      <ChoiceGroup
        label="Cleanliness"
        options={PROFILE_OPTIONS.cleanliness}
        {...choice("cleanliness")}
      />
      <ChoiceGroup
        label="Social life at home"
        options={PROFILE_OPTIONS.social}
        {...choice("socialPreference")}
      />
      <ChoiceGroup
        label="Guests"
        options={PROFILE_OPTIONS.guests}
        {...choice("guestFrequency")}
      />
      <ChoiceGroup
        label="Smoking"
        options={PROFILE_OPTIONS.habit}
        {...choice("smoking")}
      />
      <ChoiceGroup
        label="Alcohol"
        options={PROFILE_OPTIONS.habit}
        {...choice("drinking")}
      />
    </div>
  );
}

/** Render the fields for one section of the profile. */
export function ProfileStepFields({
  stepId,
  form,
}: FieldsProps & { stepId: ProfileStep["id"] }) {
  switch (stepId) {
    case "details":
      return <StudentDetailsFields form={form} />;
    case "about":
      return <AboutFields form={form} />;
    case "accommodation":
      return <AccommodationFields form={form} />;
    case "societies":
      return <SocietiesFields form={form} />;
    case "lifestyle":
      return <LifestyleFields form={form} />;
  }
}
