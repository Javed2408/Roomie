/**
 * Accommodation listing shapes, as the backend returns them
 * (backend/app/schemas/listing.py).
 *
 * There are two fundamentally different things on the Accommodation page and
 * they must never be confused (USER_FLOWS.md, section 6):
 *
 * - EXISTING_ACCOMMODATION: a real room or flat with space available.
 * - LOOKING_TO_RENT_TOGETHER: a request from students who have no flat yet.
 *
 * Modelling them as two separate types (a "discriminated union") means
 * TypeScript will not let a component read `rentPerPerson` from a search
 * request, or treat a request as an available property.
 */

import type { DiscoveryCandidate } from "@/types/profile";
import type { Society } from "@/types/society";
import type { VerificationState } from "@/types/verification";

export type ListingType = "EXISTING_ACCOMMODATION" | "LOOKING_TO_RENT_TOGETHER";

/**
 * Who is offering a property. Unauthorised brokers are not permitted.
 * - PROPERTY_OWNER: owns the property.
 * - EXISTING_TENANT: lives there and has permission to take someone in.
 * - AUTHORIZED_AGENT: an agent whose authorisation the owner has confirmed
 *   to Roomie independently.
 */
export type ListingCreatorType =
  "PROPERTY_OWNER" | "EXISTING_TENANT" | "AUTHORIZED_AGENT";

export const CREATOR_TYPE_LABELS: Record<ListingCreatorType, string> = {
  PROPERTY_OWNER: "Property owner",
  EXISTING_TENANT: "Current tenant",
  AUTHORIZED_AGENT: "Authorised agent",
};

/** Admin review state. A listing is public only once APPROVED (and active). */
export type ListingModerationStatus =
  "PENDING" | "APPROVED" | "REJECTED" | "SUSPENDED";

export const MODERATION_STATUS_LABELS: Record<ListingModerationStatus, string> =
  {
    PENDING: "Pending review",
    APPROVED: "Approved",
    REJECTED: "Not approved",
    SUSPENDED: "Suspended",
  };

/** Where the listing is in its own life, set by its creator. */
export type ListingLifecycleStatus = "DRAFT" | "ACTIVE" | "FILLED" | "CLOSED";

export const LIFECYCLE_STATUS_LABELS: Record<ListingLifecycleStatus, string> = {
  DRAFT: "Draft",
  ACTIVE: "Active",
  FILLED: "Filled",
  CLOSED: "Closed",
};

export type Furnishing = "UNFURNISHED" | "SEMI_FURNISHED" | "FULLY_FURNISHED";

export const FURNISHING_LABELS: Record<Furnishing, string> = {
  UNFURNISHED: "Unfurnished",
  SEMI_FURNISHED: "Semi-furnished",
  FULLY_FURNISHED: "Fully furnished",
};

export type Facility =
  | "WIFI"
  | "AIR_CONDITIONING"
  | "WASHING_MACHINE"
  | "REFRIGERATOR"
  | "KITCHEN"
  | "WATER_PURIFIER"
  | "GEYSER"
  | "POWER_BACKUP"
  | "LIFT"
  | "PARKING"
  | "SECURITY"
  | "HOUSEKEEPING";

export const FACILITY_LABELS: Record<Facility, string> = {
  WIFI: "Wi-Fi",
  AIR_CONDITIONING: "Air conditioning",
  WASHING_MACHINE: "Washing machine",
  REFRIGERATOR: "Fridge",
  KITCHEN: "Kitchen",
  WATER_PURIFIER: "Water purifier",
  GEYSER: "Geyser",
  POWER_BACKUP: "Power backup",
  LIFT: "Lift",
  PARKING: "Parking",
  SECURITY: "Security",
  HOUSEKEEPING: "Housekeeping",
};

/** Who receives a brokerage fee. Only an authorised agent may collect it. */
export type BrokeragePayableTo = "LISTING_CREATOR" | "THIRD_PARTY_AGENT";

export const BROKERAGE_PAYABLE_TO_LABELS: Record<BrokeragePayableTo, string> = {
  LISTING_CREATOR: "the agent who posted this",
  THIRD_PARTY_AGENT: "another agent",
};

/**
 * Brokerage must always be stated upfront, including when there is none.
 * Making it a required field means a listing cannot be built without it.
 */
export type BrokerageDisclosure =
  | { applicable: false }
  | {
      applicable: true;
      amount: number;
      note: string | null;
      payableTo: BrokeragePayableTo;
    };

export interface ListingPoster {
  id: string;
  displayName: string;
  identityVerification: VerificationState;
  /** Shown on requests to rent together, which come from students. */
  studentVerification: VerificationState | null;
}

export interface ListingPhoto {
  id: string;
  /** An access-checked API address, never a storage location. */
  url: string;
  width: number;
  height: number;
}

interface ListingBase {
  id: string;
  title: string;
  description: string;
  postedBy: ListingPoster;
  photos: ListingPhoto[];
}

export interface ExistingAccommodationListing extends ListingBase {
  type: "EXISTING_ACCOMMODATION";
  creatorType: ListingCreatorType;
  /** Whether the poster's right to offer this property has been checked. */
  listingAuthority: VerificationState;
  society: Society;
  /** Monthly, per person, in whole rupees. */
  rentPerPerson: number;
  totalRent: number | null;
  deposit: number | null;
  brokerage: BrokerageDisclosure;
  bedroomCount: number;
  availableBedrooms: number;
  furnishing: Furnishing | null;
  facilities: Facility[];
  /** ISO date, YYYY-MM-DD. */
  availableFrom: string;
  /** People living there now. */
  currentOccupants: number;
  roommatesWanted: number;
}

export interface RentTogetherListing extends ListingBase {
  type: "LOOKING_TO_RENT_TOGETHER";
  preferredSocieties: Society[];
  /** Monthly, per person, in whole rupees. */
  budgetPerPerson: number;
  desiredBedrooms: number;
  currentGroupSize: number;
  roommatesWanted: number;
  /** ISO date, YYYY-MM-DD. */
  moveInDate: string;
}

export type Listing = ExistingAccommodationListing | RentTogetherListing;

export type InterestStatus = "PENDING" | "ACCEPTED" | "DECLINED" | "WITHDRAWN";

export const INTEREST_STATUS_LABELS: Record<InterestStatus, string> = {
  PENDING: "Waiting for a reply",
  ACCEPTED: "Accepted",
  DECLINED: "Declined",
  WITHDRAWN: "Withdrawn",
};

/** A public listing, as one signed-in member sees it. */
export interface ListingView {
  listing: Listing;
  isYours: boolean;
  yourInterest: InterestStatus | null;
}

export interface ListingPage {
  listings: Listing[];
  total: number;
  limit: number;
  offset: number;
}

// --- The creator's own listings ----------------------------------------------

export type OwnAuthorityStatus =
  "NOT_SUBMITTED" | "PENDING" | "APPROVED" | "REJECTED" | "NEEDS_RESUBMISSION";

export interface OwnAuthority {
  status: OwnAuthorityStatus;
  /** Why it was not approved, written for the creator. */
  reason: string | null;
  ownerConfirmation: "NOT_REQUIRED" | "PENDING" | "CONFIRMED" | "DENIED";
  /** Document types uploaded so far. */
  documents: string[];
}

export interface OwnListingEvent {
  /** ISO date and time. */
  at: string;
  kind: "moderation" | "authority" | "edit";
  summary: string;
  note: string | null;
}

export interface OwnListing {
  listing: Listing;
  lifecycleStatus: ListingLifecycleStatus;
  moderationStatus: ListingModerationStatus;
  /** Why it was rejected or suspended. Only ever shown to its creator. */
  moderationReason: string | null;
  isPublic: boolean;
  authority: OwnAuthority | null;
  submissionRequirements: string[];
  canSubmit: boolean;
  canEdit: boolean;
  pendingInterests: number;
  createdAt: string;
  updatedAt: string;
  history: OwnListingEvent[];
}

export interface OwnListingSummary {
  id: string;
  type: ListingType;
  title: string;
  lifecycleStatus: ListingLifecycleStatus;
  moderationStatus: ListingModerationStatus;
  moderationReason: string | null;
  isPublic: boolean;
  authorityStatus: OwnAuthorityStatus | null;
  pendingInterests: number;
  coverPhoto: ListingPhoto | null;
  updatedAt: string;
}

// --- Interest ------------------------------------------------------------------

export interface MyInterest {
  listingId: string;
  title: string;
  type: ListingType;
  status: InterestStatus;
  /** False once the listing is closed, filled or no longer shown. */
  listingAvailable: boolean;
  acknowledgedBrokerageAmount: number | null;
  createdAt: string;
  respondedAt: string | null;
}

export interface InterestedStudent {
  interestId: string;
  status: InterestStatus;
  createdAt: string;
  respondedAt: string | null;
  acknowledgedBrokerageAmount: number | null;
  /** Their public profile, and the score when the creator has a profile. */
  candidate: DiscoveryCandidate;
}
