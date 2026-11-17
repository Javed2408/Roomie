/**
 * Accommodation listing shapes.
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

import type { Society } from "@/types/society";
import type { VerificationState } from "@/types/verification";

export type ListingType = "EXISTING_ACCOMMODATION" | "LOOKING_TO_RENT_TOGETHER";

/**
 * Who is offering a property. Unauthorised brokers are not permitted.
 * - PROPERTY_OWNER: owns the property.
 * - EXISTING_TENANT: lives there and has permission to find a roommate.
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

/** Admin review state. A listing is public only once APPROVED. */
export type ListingModerationStatus =
  "PENDING" | "APPROVED" | "REJECTED" | "SUSPENDED";

export const MODERATION_STATUS_LABELS: Record<ListingModerationStatus, string> =
  {
    PENDING: "Pending review",
    APPROVED: "Approved",
    REJECTED: "Rejected",
    SUSPENDED: "Suspended",
  };

/** Where the listing is in its own life, set by its creator. */
export type ListingLifecycleStatus = "DRAFT" | "ACTIVE" | "FILLED" | "CLOSED";

export type Furnishing = "UNFURNISHED" | "SEMI_FURNISHED" | "FULLY_FURNISHED";

export const FURNISHING_LABELS: Record<Furnishing, string> = {
  UNFURNISHED: "Unfurnished",
  SEMI_FURNISHED: "Semi-furnished",
  FULLY_FURNISHED: "Fully furnished",
};

/**
 * Brokerage must always be stated upfront, including when there is none.
 * Making it a required field means a listing cannot be built without it.
 */
export type BrokerageDisclosure =
  { applicable: false } | { applicable: true; amount: number; note?: string };

export interface ListingPoster {
  id: string;
  displayName: string;
  identityVerification: VerificationState;
}

interface ListingBase {
  id: string;
  title: string;
  description: string;
  postedBy: ListingPoster;
  moderationStatus: ListingModerationStatus;
  /** Why a moderator rejected or suspended it. Shown only to its creator. */
  moderationNote?: string;
  lifecycleStatus: ListingLifecycleStatus;
}

export interface ExistingAccommodationListing extends ListingBase {
  type: "EXISTING_ACCOMMODATION";
  creatorType: ListingCreatorType;
  /** Whether the poster's right to offer this property has been checked. */
  listingAuthority: VerificationState;
  society: Society;
  /** Monthly, per person, in whole rupees. */
  rentPerPerson: number;
  deposit: number | null;
  brokerage: BrokerageDisclosure;
  bedroomCount: number;
  availableSpaces: number;
  furnishing: Furnishing;
  /** ISO date, YYYY-MM-DD. */
  availableFrom: string;
}

export interface RentTogetherListing extends ListingBase {
  type: "LOOKING_TO_RENT_TOGETHER";
  preferredSocieties: Society[];
  /** Monthly, per person, in whole rupees. */
  budgetPerPerson: number;
  desiredBedrooms: number;
  currentGroupSize: number;
  additionalRoommatesNeeded: number;
  /** ISO date, YYYY-MM-DD. */
  moveInDate: string;
}

export type Listing = ExistingAccommodationListing | RentTogetherListing;
