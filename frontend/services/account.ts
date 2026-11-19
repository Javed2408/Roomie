/** The signed-in person's profile, preferences, societies and verification. */

import { API_V1_URL } from "@/lib/config";
import { apiDelete, apiGet, apiPost, apiPut } from "@/services/api-client";
import { parseAccount, parseOwnVerification } from "@/services/parse";
import type {
  Account,
  OwnVerification,
  VerificationDocumentType,
} from "@/types/account";

export async function fetchAccount(signal?: AbortSignal): Promise<Account> {
  return parseAccount(await apiGet("/me", { signal }));
}

export interface ProfileInput {
  fullName: string;
  collegeName: string;
  course: string;
  department: string;
  academicYear: string;
  bio: string;
  gender: string;
  genderVisible: boolean;
}

export interface PreferencesInput {
  minBudget: string;
  maxBudget: string;
  moveInDate: string;
  roomType: string;
  foodPreference: string;
  smokingPreference: string;
  drinkingPreference: string;
  sleepSchedule: string;
  cleanlinessLevel: string;
  socialPreference: string;
  guestFrequency: string;
}

/** "" -> null, so an empty field is saved as "not answered". */
const orNull = (value: string) => value.trim() || null;
const numberOrNull = (value: string) =>
  /^\d+$/.test(value.trim()) ? Number(value.trim()) : null;

export async function saveProfile(input: ProfileInput): Promise<Account> {
  return parseAccount(
    await apiPut("/me/profile", {
      full_name: input.fullName,
      college_name: input.collegeName,
      course: orNull(input.course),
      department: orNull(input.department),
      academic_year: numberOrNull(input.academicYear),
      bio: orNull(input.bio),
      gender: orNull(input.gender),
      gender_visible: input.genderVisible,
    }),
  );
}

export async function savePreferences(
  input: PreferencesInput,
): Promise<Account> {
  return parseAccount(
    await apiPut("/me/preferences", {
      min_budget: numberOrNull(input.minBudget),
      max_budget: numberOrNull(input.maxBudget),
      move_in_date: orNull(input.moveInDate),
      room_type: orNull(input.roomType),
      food_preference: orNull(input.foodPreference),
      smoking_preference: orNull(input.smokingPreference),
      drinking_preference: orNull(input.drinkingPreference),
      sleep_schedule: orNull(input.sleepSchedule),
      cleanliness_level: orNull(input.cleanlinessLevel),
      social_preference: orNull(input.socialPreference),
      guest_frequency: orNull(input.guestFrequency),
    }),
  );
}

/** `societyIds` is in order of preference, most preferred first. */
export async function saveSocieties(societyIds: string[]): Promise<Account> {
  return parseAccount(
    await apiPut("/me/societies", { society_ids: societyIds }),
  );
}

/** Mark the profile complete. The backend refuses if anything is missing. */
export async function publishProfile(): Promise<Account> {
  return parseAccount(await apiPost("/me/profile/publish"));
}

// --- Profile photo --------------------------------------------------------

/**
 * Upload or replace your profile photo. The backend checks it is a real
 * image, crops it square and removes location and camera details.
 */
export async function uploadProfilePhoto(file: File): Promise<Account> {
  const form = new FormData();
  form.append("file", file);
  return parseAccount(await apiPut("/me/profile/photo", form));
}

export async function removeProfilePhoto(): Promise<Account> {
  return parseAccount(await apiDelete("/me/profile/photo"));
}

// --- Verification ---------------------------------------------------------

async function upload(
  path: string,
  file: File,
  fields: Record<string, string>,
): Promise<OwnVerification> {
  const form = new FormData();
  for (const [name, value] of Object.entries(fields)) {
    form.append(name, value);
  }
  form.append("file", file);
  return parseOwnVerification(await apiPost(path, form));
}

export function submitIdentityDocument(file: File): Promise<OwnVerification> {
  return upload("/me/verifications/identity", file, {
    document_type: "GOVERNMENT_ID",
  });
}

export function submitStudentDocument(
  file: File,
  institutionName: string,
  documentType: VerificationDocumentType,
): Promise<OwnVerification> {
  return upload("/me/verifications/student", file, {
    institution_name: institutionName,
    document_type: documentType,
  });
}

/**
 * The address for downloading one of your own documents. It only works
 * for the person who uploaded the file (and administrators); the backend
 * checks the session cookie on every request.
 */
export function documentDownloadUrl(documentId: string): string {
  return `${API_V1_URL}/verification-documents/${documentId}/content`;
}
