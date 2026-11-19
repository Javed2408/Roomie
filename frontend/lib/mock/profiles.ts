/**
 * SAMPLE DATA — invented people for building and reviewing screens only.
 *
 * None of these students exist. Since Phase 5 they appear only in the
 * landing page's preview card and the sample Messages screens; Discover
 * and Matches use real students. Their
 * compatibility scores are hand-written examples (the real scoring is in
 * backend/app/services/compatibility.py). Every identity check is
 * "NOT_VERIFIED" because no verification has happened.
 *
 * Any screen that shows this data must display a "Sample data" label.
 */

import { SOCIETIES } from "@/lib/mock/societies";
import type { DiscoveryCandidate } from "@/types/profile";

const SRM = "SRM IST, Kattankulathur";

export const DISCOVERY_CANDIDATES: DiscoveryCandidate[] = [
  {
    profile: {
      id: "user-meera",
      fullName: "Meera Iyer",
      collegeName: SRM,
      course: "B.Tech",
      department: "Electronics",
      academicYear: 2,
      bio: "Early riser who likes a calm flat. Happy to split cooking and keep a cleaning rota.",
      photoUrl: null,
      identityVerification: "NOT_VERIFIED",
      studentVerification: "NOT_VERIFIED",
      preferences: {
        minBudget: 9000,
        maxBudget: 13000,
        moveInDate: "2027-01-10",
        roomType: "PRIVATE_ROOM",
        foodPreference: "VEGETARIAN",
        smoking: "NEVER",
        drinking: "NEVER",
        sleepSchedule: "EARLY_BIRD",
        cleanliness: "VERY_TIDY",
        socialPreference: "QUIET",
        guestFrequency: "RARELY",
      },
      societyPreferences: [
        { society: SOCIETIES.lakeside, priority: 1 },
        { society: SOCIETIES.greenfield, priority: 2 },
      ],
    },
    compatibilityScore: 86,
    positives: [
      "Same first-choice society",
      "Budgets overlap",
      "Move-in dates 5 days apart",
    ],
    cautions: ["Different sleep schedules"],
  },
  {
    profile: {
      id: "user-farhan",
      fullName: "Farhan Sheikh",
      collegeName: "Valliammai Engineering College",
      course: "B.E.",
      department: "Mechanical",
      academicYear: 3,
      bio: "Into football and weekend treks. I am out most evenings and keep things low-drama at home.",
      photoUrl: null,
      identityVerification: "NOT_VERIFIED",
      studentVerification: "NOT_VERIFIED",
      preferences: {
        minBudget: 7000,
        maxBudget: 10000,
        moveInDate: "2027-01-20",
        roomType: "SHARED_ROOM",
        foodPreference: "NON_VEGETARIAN",
        smoking: "NEVER",
        drinking: "OCCASIONALLY",
        sleepSchedule: "NIGHT_OWL",
        cleanliness: "TIDY",
        socialPreference: "SOCIAL",
        guestFrequency: "SOMETIMES",
      },
      societyPreferences: [
        { society: SOCIETIES.mapleCourt, priority: 1 },
        { society: SOCIETIES.palmGrove, priority: 2 },
      ],
    },
    compatibilityScore: 71,
    positives: ["One shared society", "Similar sleep schedule"],
    cautions: ["Budgets only partly overlap", "Different room preference"],
  },
  {
    profile: {
      id: "user-kavya",
      fullName: "Kavya Nair",
      collegeName: SRM,
      course: "B.Des",
      department: "Design",
      academicYear: 1,
      bio: "First year, new to the area. I draw a lot, love quiet mornings and am looking for a friendly, respectful flat.",
      photoUrl: null,
      identityVerification: "NOT_VERIFIED",
      studentVerification: "NOT_VERIFIED",
      preferences: {
        minBudget: 8000,
        maxBudget: 11000,
        moveInDate: "2027-02-01",
        roomType: "NO_PREFERENCE",
        foodPreference: "VEGETARIAN",
        smoking: "NEVER",
        drinking: "NEVER",
        sleepSchedule: "FLEXIBLE",
        cleanliness: "TIDY",
        socialPreference: "BALANCED",
        guestFrequency: "RARELY",
      },
      societyPreferences: [
        { society: SOCIETIES.greenfield, priority: 1 },
        { society: SOCIETIES.lakeside, priority: 2 },
        { society: SOCIETIES.sunrise, priority: 3 },
      ],
    },
    compatibilityScore: 78,
    positives: [
      "Two shared societies",
      "Budgets overlap",
      "Same food preference",
    ],
    cautions: ["Move-in dates almost 4 weeks apart"],
  },
];
