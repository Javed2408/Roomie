/**
 * Accommodation listings: browsing, your own listings, photos, evidence of
 * listing authority, and interest.
 *
 * Who sees what, and every status, is decided by the backend
 * (backend/app/services/listing_management.py and listing_interest.py).
 * Nothing sent from here can approve or publish a listing.
 */

import { apiDelete, apiGet, apiPost, apiPut } from "@/services/api-client";
import {
  parseInterestedStudents,
  parseListingPage,
  parseListingView,
  parseMyInterests,
  parseOwnListing,
  parseOwnListingSummaries,
} from "@/services/parse-listing";
import { parseOwnVerification } from "@/services/parse";
import type {
  OwnVerification,
  VerificationDocumentType,
} from "@/types/account";
import type {
  BrokeragePayableTo,
  Facility,
  Furnishing,
  InterestedStudent,
  ListingCreatorType,
  ListingPage,
  ListingType,
  ListingView,
  MyInterest,
  OwnListing,
  OwnListingSummary,
} from "@/types/listing";

/** How many listings one page of results holds. */
export const LISTING_PAGE_SIZE = 12;

export type ListingSort = "newest" | "rent_low" | "available_soon";

export interface ListingSearch {
  type?: ListingType | null;
  societyId?: string | null;
  localityId?: string | null;
  minRent?: number | null;
  maxRent?: number | null;
  /** ISO date: available on or before this day. */
  availableBy?: string | null;
  query?: string | null;
  sort?: ListingSort;
  offset?: number;
  limit?: number;
}

const id = (value: string) => encodeURIComponent(value);

export async function browseListings(
  search: ListingSearch = {},
  signal?: AbortSignal,
): Promise<ListingPage> {
  const params = new URLSearchParams({
    limit: String(search.limit ?? LISTING_PAGE_SIZE),
    offset: String(search.offset ?? 0),
    sort: search.sort ?? "newest",
  });
  const optional: Array<[string, string | number | null | undefined]> = [
    ["type", search.type],
    ["society_id", search.societyId],
    ["locality_id", search.localityId],
    ["min_rent", search.minRent],
    ["max_rent", search.maxRent],
    ["available_by", search.availableBy],
    ["q", search.query?.trim()],
  ];
  for (const [name, value] of optional) {
    if (value !== null && value !== undefined && value !== "") {
      params.set(name, String(value));
    }
  }
  return parseListingPage(
    await apiGet(`/listings?${params.toString()}`, { signal }),
  );
}

export async function fetchListing(
  listingId: string,
  signal?: AbortSignal,
): Promise<ListingView> {
  return parseListingView(
    await apiGet(`/listings/${id(listingId)}`, { signal }),
  );
}

// --- Interest -------------------------------------------------------------

/**
 * Share your profile with the listing's creator. When the listing charges
 * brokerage, the backend refuses unless `acknowledgeBrokerage` is true.
 */
export async function expressInterest(
  listingId: string,
  acknowledgeBrokerage: boolean,
): Promise<void> {
  await apiPost(`/listings/${id(listingId)}/interest`, {
    acknowledge_brokerage: acknowledgeBrokerage,
  });
}

export async function withdrawInterest(listingId: string): Promise<void> {
  await apiDelete(`/listings/${id(listingId)}/interest`);
}

export async function fetchMyInterests(
  signal?: AbortSignal,
): Promise<MyInterest[]> {
  return parseMyInterests(await apiGet("/me/interests", { signal }));
}

// --- Your own listings ----------------------------------------------------

export interface PropertyListingInput {
  listingType: "EXISTING_ACCOMMODATION";
  title: string;
  description: string;
  creatorType: ListingCreatorType;
  societyId: string;
  rentPerPerson: number;
  totalRent: number | null;
  deposit: number | null;
  brokerage:
    | { applicable: false }
    | {
        applicable: true;
        amount: number;
        payableTo: BrokeragePayableTo;
        note: string | null;
      };
  bedroomCount: number;
  availableBedrooms: number;
  furnishing: Furnishing;
  facilities: Facility[];
  availableFrom: string;
  currentOccupants: number;
  roommatesWanted: number;
  /** The creator's declaration. Evidence is still checked by a person. */
  confirmedAuthority: true;
}

export interface SearchListingInput {
  listingType: "LOOKING_TO_RENT_TOGETHER";
  title: string;
  description: string;
  /** Most preferred first. */
  societyIds: string[];
  budgetPerPerson: number;
  desiredBedrooms: number;
  currentGroupSize: number;
  roommatesWanted: number;
  moveInDate: string;
}

export type ListingInput = PropertyListingInput | SearchListingInput;

function toBody(input: ListingInput): Record<string, unknown> {
  if (input.listingType === "LOOKING_TO_RENT_TOGETHER") {
    return {
      listing_type: input.listingType,
      title: input.title,
      description: input.description,
      society_ids: input.societyIds,
      budget_per_person: input.budgetPerPerson,
      desired_bedrooms: input.desiredBedrooms,
      current_group_size: input.currentGroupSize,
      roommates_wanted: input.roommatesWanted,
      move_in_date: input.moveInDate,
    };
  }
  const brokerage = input.brokerage;
  return {
    listing_type: input.listingType,
    title: input.title,
    description: input.description,
    creator_type: input.creatorType,
    society_id: input.societyId,
    rent_per_person: input.rentPerPerson,
    total_rent: input.totalRent,
    deposit: input.deposit,
    brokerage_applicable: brokerage.applicable,
    brokerage_amount: brokerage.applicable ? brokerage.amount : null,
    brokerage_payable_to: brokerage.applicable ? brokerage.payableTo : null,
    brokerage_note: brokerage.applicable ? brokerage.note : null,
    bedroom_count: input.bedroomCount,
    available_bedrooms: input.availableBedrooms,
    furnishing: input.furnishing,
    facilities: input.facilities,
    available_from: input.availableFrom,
    current_occupants: input.currentOccupants,
    roommates_wanted: input.roommatesWanted,
    confirmed_authority: input.confirmedAuthority,
  };
}

export async function fetchMyListings(
  signal?: AbortSignal,
): Promise<OwnListingSummary[]> {
  return parseOwnListingSummaries(await apiGet("/me/listings", { signal }));
}

export async function fetchMyListing(
  listingId: string,
  signal?: AbortSignal,
): Promise<OwnListing> {
  return parseOwnListing(
    await apiGet(`/me/listings/${id(listingId)}`, { signal }),
  );
}

/** Saved as a draft: nobody else sees it until it is submitted and approved. */
export async function createListing(input: ListingInput): Promise<OwnListing> {
  return parseOwnListing(await apiPost("/me/listings", toBody(input)));
}

/** An approved listing goes back to review (and is hidden) after an edit. */
export async function updateListing(
  listingId: string,
  input: ListingInput,
): Promise<OwnListing> {
  return parseOwnListing(
    await apiPut(`/me/listings/${id(listingId)}`, toBody(input)),
  );
}

/** Only a draft that was never submitted can be deleted; others are closed. */
export async function deleteDraft(listingId: string): Promise<void> {
  await apiDelete(`/me/listings/${id(listingId)}`);
}

export async function submitForReview(listingId: string): Promise<OwnListing> {
  return parseOwnListing(await apiPost(`/me/listings/${id(listingId)}/submit`));
}

/** Mark as filled, reopen or close. Never changes the review status. */
export async function changeLifecycle(
  listingId: string,
  status: "ACTIVE" | "FILLED" | "CLOSED",
): Promise<OwnListing> {
  return parseOwnListing(
    await apiPost(`/me/listings/${id(listingId)}/lifecycle`, { status }),
  );
}

// --- Photos ---------------------------------------------------------------

export async function addListingPhoto(
  listingId: string,
  file: File,
): Promise<OwnListing> {
  const form = new FormData();
  form.append("file", file);
  return parseOwnListing(
    await apiPost(`/me/listings/${id(listingId)}/photos`, form),
  );
}

export async function removeListingPhoto(
  listingId: string,
  photoId: string,
): Promise<OwnListing> {
  return parseOwnListing(
    await apiDelete(`/me/listings/${id(listingId)}/photos/${id(photoId)}`),
  );
}

// --- Evidence of listing authority ----------------------------------------

/**
 * Upload one piece of evidence of the right to list this property. Agents
 * also give the owner's name and contact, so Roomie can confirm with the
 * owner directly. Uploading never verifies anything by itself.
 */
export async function submitAuthorityEvidence(
  listingId: string,
  file: File,
  documentType: VerificationDocumentType,
  owner?: { name: string; contact: string },
): Promise<OwnVerification> {
  const form = new FormData();
  form.append("document_type", documentType);
  if (owner) {
    form.append("owner_name", owner.name);
    form.append("owner_contact", owner.contact);
  }
  form.append("file", file);
  return parseOwnVerification(
    await apiPost(`/me/listings/${id(listingId)}/authority-verification`, form),
  );
}

// --- People interested in your listing ------------------------------------

export async function fetchInterestedStudents(
  listingId: string,
  signal?: AbortSignal,
): Promise<InterestedStudent[]> {
  return parseInterestedStudents(
    await apiGet(`/me/listings/${id(listingId)}/interests`, { signal }),
  );
}

export async function respondToInterest(
  listingId: string,
  interestId: string,
  status: "ACCEPTED" | "DECLINED",
): Promise<InterestedStudent[]> {
  return parseInterestedStudents(
    await apiPost(`/me/listings/${id(listingId)}/interests/${id(interestId)}`, {
      status,
    }),
  );
}
