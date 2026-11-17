/**
 * The shape, starting values and validation rules of the profile form.
 * The profile editor and the onboarding steps both use this one definition,
 * so the two can never disagree about what a valid profile is.
 *
 * As with all client-side validation, this is for fast feedback only. The
 * backend must check everything again (roadmap Phase 3).
 */

import type { SelectOption } from "@/components/ui/select-field";
import {
  savePreferences,
  saveProfile,
  saveSocieties,
  type PreferencesInput,
  type ProfileInput,
} from "@/services/account";
import type { Account } from "@/types/account";
import {
  CLEANLINESS_LABELS,
  FOOD_LABELS,
  GUEST_LABELS,
  HABIT_LABELS,
  ROOM_TYPE_LABELS,
  SLEEP_LABELS,
  SOCIAL_LABELS,
} from "@/types/profile";

// A `type` (not an `interface`) so it fits the form hook's value shape.
export type ProfileFormValues = {
  fullName: string;
  collegeName: string;
  course: string;
  department: string;
  academicYear: string;
  bio: string;
  gender: string;
  showGender: boolean;
  minBudget: string;
  maxBudget: string;
  moveInDate: string;
  roomType: string;
  societyIds: string[];
  foodPreference: string;
  smoking: string;
  drinking: string;
  sleepSchedule: string;
  cleanliness: string;
  socialPreference: string;
  guestFrequency: string;
};

type ProfileFieldName = keyof ProfileFormValues & string;

export const BIO_MAX_LENGTH = 500;
export const MAX_SOCIETIES = 5;
const MIN_BUDGET = 1000;
const MAX_BUDGET = 100000;

/** Turn a `{ VALUE: "Label" }` map into drop-down options. */
function toOptions(labels: Record<string, string>): SelectOption[] {
  return Object.entries(labels).map(([value, label]) => ({ value, label }));
}

export const PROFILE_OPTIONS = {
  academicYear: [
    { value: "1", label: "1st year" },
    { value: "2", label: "2nd year" },
    { value: "3", label: "3rd year" },
    { value: "4", label: "4th year" },
    { value: "5", label: "5th year or above" },
  ],
  gender: [
    { value: "WOMAN", label: "Woman" },
    { value: "MAN", label: "Man" },
    { value: "NON_BINARY", label: "Non-binary" },
  ],
  roomType: toOptions(ROOM_TYPE_LABELS),
  food: toOptions(FOOD_LABELS),
  habit: toOptions(HABIT_LABELS),
  sleep: toOptions(SLEEP_LABELS),
  cleanliness: toOptions(CLEANLINESS_LABELS),
  social: toOptions(SOCIAL_LABELS),
  guests: toOptions(GUEST_LABELS),
} satisfies Record<string, SelectOption[]>;

/** "12000" -> 12000. Anything that is not a whole number gives null. */
export function parseWholeNumber(value: string): number | null {
  const trimmed = value.trim();
  return /^\d+$/.test(trimmed) ? Number(trimmed) : null;
}

function validateBudget(value: string, label: string): string | undefined {
  if (!value.trim()) {
    return `Enter your ${label} budget.`;
  }
  const amount = parseWholeNumber(value);
  if (amount === null) {
    return "Use numbers only, like 9000.";
  }
  if (amount < MIN_BUDGET || amount > MAX_BUDGET) {
    return "Enter an amount from ₹1,000 to ₹1,00,000.";
  }
  return undefined;
}

export function validateProfile(
  values: ProfileFormValues,
): Partial<Record<ProfileFieldName, string>> {
  const errors: Partial<Record<ProfileFieldName, string>> = {};

  if (!values.fullName.trim()) {
    errors.fullName = "Enter your name.";
  } else if (values.fullName.trim().length > 120) {
    errors.fullName = "Use 120 characters or fewer.";
  }
  if (!values.collegeName.trim()) {
    errors.collegeName = "Enter your college.";
  }
  if (values.bio.length > BIO_MAX_LENGTH) {
    errors.bio = `Use ${BIO_MAX_LENGTH} characters or fewer.`;
  }

  errors.minBudget = validateBudget(values.minBudget, "minimum");
  errors.maxBudget = validateBudget(values.maxBudget, "maximum");
  const min = parseWholeNumber(values.minBudget);
  const max = parseWholeNumber(values.maxBudget);
  if (!errors.minBudget && !errors.maxBudget && min !== null && max !== null) {
    if (min > max) {
      errors.maxBudget = "Must be at least your minimum.";
    }
  }

  if (!values.moveInDate) {
    errors.moveInDate = "Choose a move-in date.";
  }

  if (values.societyIds.length === 0) {
    errors.societyIds = "Choose at least one society.";
  } else if (values.societyIds.length > MAX_SOCIETIES) {
    errors.societyIds = `Choose up to ${MAX_SOCIETIES} societies.`;
  }

  return errors;
}

export interface ProfileStep {
  id: "details" | "about" | "accommodation" | "societies" | "lifestyle";
  title: string;
  description: string;
  /** The fields this step is responsible for checking. */
  fields: ProfileFieldName[];
}

/** The sections of the profile, in the order onboarding asks for them. */
export const PROFILE_STEPS: ProfileStep[] = [
  {
    id: "details",
    title: "Student details",
    description: "The basics other students see first.",
    fields: ["fullName", "collegeName", "course", "department", "academicYear"],
  },
  {
    id: "about",
    title: "About you",
    description: "A short introduction helps people decide to say hello.",
    fields: ["bio", "gender"],
  },
  {
    id: "accommodation",
    title: "Budget and move-in",
    description: "What you can spend each month, and when you want to move.",
    fields: ["minBudget", "maxBudget", "moveInDate", "roomType"],
  },
  {
    id: "societies",
    title: "Preferred societies",
    description: "Where you would like to live, in order of preference.",
    fields: ["societyIds"],
  },
  {
    id: "lifestyle",
    title: "Lifestyle",
    description:
      "These help find people whose routines fit yours. All are optional.",
    fields: [],
  },
];

/** Fill the form from what the backend has stored. */
export function accountToFormValues(account: Account): ProfileFormValues {
  const { profile, preferences } = account;
  const number = (value: number | null | undefined) =>
    value === null || value === undefined ? "" : String(value);
  return {
    fullName: profile?.fullName ?? "",
    collegeName: profile?.collegeName ?? "",
    course: profile?.course ?? "",
    department: profile?.department ?? "",
    academicYear: number(profile?.academicYear),
    bio: profile?.bio ?? "",
    gender: profile?.gender ?? "",
    showGender: profile?.genderVisible ?? false,
    minBudget: number(preferences?.minBudget),
    maxBudget: number(preferences?.maxBudget),
    moveInDate: preferences?.moveInDate ?? "",
    roomType: preferences?.roomType ?? "",
    // Societies that have left the directory cannot be saved again, so they
    // start out of the form. The societies step tells the person which.
    societyIds: [...account.societies]
      .filter((item) => item.available)
      .sort((a, b) => a.priority - b.priority)
      .map((item) => item.society.id),
    foodPreference: preferences?.foodPreference ?? "",
    smoking: preferences?.smokingPreference ?? "",
    drinking: preferences?.drinkingPreference ?? "",
    sleepSchedule: preferences?.sleepSchedule ?? "",
    cleanliness: preferences?.cleanlinessLevel ?? "",
    socialPreference: preferences?.socialPreference ?? "",
    guestFrequency: preferences?.guestFrequency ?? "",
  };
}

function toProfileInput(values: ProfileFormValues): ProfileInput {
  return {
    fullName: values.fullName,
    collegeName: values.collegeName,
    course: values.course,
    department: values.department,
    academicYear: values.academicYear,
    bio: values.bio,
    gender: values.gender,
    genderVisible: values.showGender,
  };
}

function toPreferencesInput(values: ProfileFormValues): PreferencesInput {
  return {
    minBudget: values.minBudget,
    maxBudget: values.maxBudget,
    moveInDate: values.moveInDate,
    roomType: values.roomType,
    foodPreference: values.foodPreference,
    smokingPreference: values.smoking,
    drinkingPreference: values.drinking,
    sleepSchedule: values.sleepSchedule,
    cleanlinessLevel: values.cleanliness,
    socialPreference: values.socialPreference,
    guestFrequency: values.guestFrequency,
  };
}

/**
 * Save one onboarding step to the backend.
 *
 * Each step is saved as soon as it is finished, so someone who closes the
 * browser halfway through can carry on later from where they stopped.
 */
export function saveProfileStep(
  stepId: ProfileStep["id"],
  values: ProfileFormValues,
): Promise<Account> {
  switch (stepId) {
    case "details":
    case "about":
      return saveProfile(toProfileInput(values));
    case "accommodation":
    case "lifestyle":
      return savePreferences(toPreferencesInput(values));
    case "societies":
      return saveSocieties(values.societyIds);
  }
}

/** Save every section. Used by the profile editor's single Save button. */
export async function saveWholeProfile(
  values: ProfileFormValues,
): Promise<Account> {
  await saveProfile(toProfileInput(values));
  await savePreferences(toPreferencesInput(values));
  return saveSocieties(values.societyIds);
}
