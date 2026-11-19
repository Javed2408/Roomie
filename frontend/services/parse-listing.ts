/**
 * Turning the backend's listing responses into the frontend's types,
 * checking every field on the way (see services/parse.ts for why).
 */

import {
  apiAddress,
  list,
  oneOf,
  optionalNumber,
  optionalText,
  parseCandidate,
  parseSociety,
  record,
  required,
  text,
  type Json,
} from "@/services/parse";
import {
  CREATOR_TYPE_LABELS,
  FACILITY_LABELS,
  FURNISHING_LABELS,
  type BrokerageDisclosure,
  type BrokeragePayableTo,
  type Facility,
  type InterestStatus,
  type InterestedStudent,
  type Listing,
  type ListingLifecycleStatus,
  type ListingModerationStatus,
  type ListingPage,
  type ListingPhoto,
  type ListingPoster,
  type ListingType,
  type ListingView,
  type MyInterest,
  type OwnAuthority,
  type OwnAuthorityStatus,
  type OwnListing,
  type OwnListingEvent,
  type OwnListingSummary,
} from "@/types/listing";
import type { VerificationState } from "@/types/verification";

const keysOf = <T extends string>(labels: Record<T, string>) =>
  Object.keys(labels) as T[];

const LISTING_TYPES: ListingType[] = [
  "EXISTING_ACCOMMODATION",
  "LOOKING_TO_RENT_TOGETHER",
];
const CREATOR_TYPES = keysOf(CREATOR_TYPE_LABELS);
const FURNISHINGS = keysOf(FURNISHING_LABELS);
const FACILITIES = keysOf(FACILITY_LABELS);
const PAYEES: BrokeragePayableTo[] = ["LISTING_CREATOR", "THIRD_PARTY_AGENT"];
const PUBLIC_STATES: VerificationState[] = [
  "NOT_VERIFIED",
  "PENDING",
  "VERIFIED",
];
const LIFECYCLE: ListingLifecycleStatus[] = [
  "DRAFT",
  "ACTIVE",
  "FILLED",
  "CLOSED",
];
const MODERATION: ListingModerationStatus[] = [
  "PENDING",
  "APPROVED",
  "REJECTED",
  "SUSPENDED",
];
const INTEREST: InterestStatus[] = [
  "PENDING",
  "ACCEPTED",
  "DECLINED",
  "WITHDRAWN",
];
const AUTHORITY: OwnAuthorityStatus[] = [
  "NOT_SUBMITTED",
  "PENDING",
  "APPROVED",
  "REJECTED",
  "NEEDS_RESUBMISSION",
];

function must<T extends string>(
  value: unknown,
  allowed: readonly T[],
  what: string,
): T {
  return required(oneOf(value, allowed, what), what);
}

function count(value: unknown, what: string): number {
  return optionalNumber(value, what) ?? 0;
}

export function parsePhoto(value: unknown): ListingPhoto {
  const photo = record(value, "photo");
  return {
    id: text(photo.id, "photo.id"),
    url: required(apiAddress(text(photo.url, "photo.url")), "photo.url"),
    width: count(photo.width, "photo.width"),
    height: count(photo.height, "photo.height"),
  };
}

function parsePoster(value: unknown): ListingPoster {
  const poster = record(value, "posted_by");
  return {
    id: text(poster.id, "poster.id"),
    displayName: text(poster.display_name, "poster.display_name"),
    identityVerification: must(
      poster.identity_verification,
      PUBLIC_STATES,
      "poster.identity",
    ),
    studentVerification: oneOf(
      poster.student_verification,
      PUBLIC_STATES,
      "poster.student",
    ),
  };
}

function parseBrokerage(value: unknown): BrokerageDisclosure {
  const brokerage = record(value, "brokerage");
  if (brokerage.applicable !== true) {
    return { applicable: false };
  }
  return {
    applicable: true,
    amount: count(brokerage.amount, "brokerage.amount"),
    note: optionalText(brokerage.note, "brokerage.note"),
    payableTo: must(brokerage.payable_to, PAYEES, "brokerage.payable_to"),
  };
}

export function parseListing(value: unknown): Listing {
  const listing = record(value, "listing");
  const base = {
    id: text(listing.id, "listing.id"),
    title: text(listing.title, "listing.title"),
    description: text(listing.description, "listing.description"),
    postedBy: parsePoster(listing.posted_by),
    photos: list(listing.photos, "listing.photos").map(parsePhoto),
  };
  const type = must(listing.type, LISTING_TYPES, "listing.type");
  if (type === "EXISTING_ACCOMMODATION") {
    return {
      ...base,
      type,
      creatorType: must(listing.creator_type, CREATOR_TYPES, "creator_type"),
      listingAuthority: must(
        listing.listing_authority,
        PUBLIC_STATES,
        "listing_authority",
      ),
      society: parseSociety(listing.society),
      rentPerPerson: count(listing.rent_per_person, "rent_per_person"),
      totalRent: optionalNumber(listing.total_rent, "total_rent"),
      deposit: optionalNumber(listing.deposit, "deposit"),
      brokerage: parseBrokerage(listing.brokerage),
      bedroomCount: count(listing.bedroom_count, "bedroom_count"),
      availableBedrooms: count(
        listing.available_bedrooms,
        "available_bedrooms",
      ),
      furnishing: oneOf(listing.furnishing, FURNISHINGS, "furnishing"),
      facilities: list(listing.facilities, "facilities").map((item) =>
        must<Facility>(item, FACILITIES, "facility"),
      ),
      availableFrom: text(listing.available_from, "available_from"),
      currentOccupants: count(listing.current_group_size, "current_group_size"),
      roommatesWanted: count(listing.required_roommates, "roommates"),
    };
  }
  return {
    ...base,
    type,
    preferredSocieties: list(
      listing.preferred_societies,
      "preferred_societies",
    ).map(parseSociety),
    budgetPerPerson: count(listing.rent_per_person, "rent_per_person"),
    desiredBedrooms: count(listing.bedroom_count, "bedroom_count"),
    currentGroupSize: count(listing.current_group_size, "current_group_size"),
    roommatesWanted: count(listing.required_roommates, "roommates"),
    moveInDate: text(listing.available_from, "available_from"),
  };
}

export function parseListingPage(value: unknown): ListingPage {
  const page = record(value, "listing page");
  return {
    listings: list(page.items, "listings").map(parseListing),
    total: count(page.total, "total"),
    limit: count(page.limit, "limit"),
    offset: count(page.offset, "offset"),
  };
}

export function parseListingView(value: unknown): ListingView {
  const view = record(value, "listing view");
  return {
    listing: parseListing(view.listing),
    isYours: view.is_yours === true,
    yourInterest: oneOf(view.your_interest, INTEREST, "your_interest"),
  };
}

function parseAuthority(value: unknown): OwnAuthority | null {
  if (value === null || value === undefined) {
    return null;
  }
  const authority = record(value, "authority");
  return {
    status: must(authority.status, AUTHORITY, "authority.status"),
    reason: optionalText(authority.reason, "authority.reason"),
    ownerConfirmation: must(
      authority.owner_confirmation,
      ["NOT_REQUIRED", "PENDING", "CONFIRMED", "DENIED"] as const,
      "owner_confirmation",
    ),
    documents: list(authority.documents, "documents").map((item) =>
      text(item, "document type"),
    ),
  };
}

function parseEvent(value: unknown): OwnListingEvent {
  const event: Json = record(value, "history event");
  return {
    at: text(event.at, "event.at"),
    kind: must(
      event.kind,
      ["moderation", "authority", "edit"] as const,
      "kind",
    ),
    summary: text(event.summary, "event.summary"),
    note: optionalText(event.note, "event.note"),
  };
}

export function parseOwnListing(value: unknown): OwnListing {
  const own = record(value, "own listing");
  return {
    listing: parseListing(own.listing),
    lifecycleStatus: must(own.lifecycle_status, LIFECYCLE, "lifecycle"),
    moderationStatus: must(own.moderation_status, MODERATION, "moderation"),
    moderationReason: optionalText(own.moderation_reason, "reason"),
    isPublic: own.is_public === true,
    authority: parseAuthority(own.authority),
    submissionRequirements: list(
      own.submission_requirements,
      "requirements",
    ).map((item) => text(item, "requirement")),
    canSubmit: own.can_submit === true,
    canEdit: own.can_edit === true,
    pendingInterests: count(own.pending_interests, "pending_interests"),
    createdAt: text(own.created_at, "created_at"),
    updatedAt: text(own.updated_at, "updated_at"),
    history: list(own.history, "history").map(parseEvent),
  };
}

export function parseOwnListingSummaries(value: unknown): OwnListingSummary[] {
  return list(value, "my listings").map((item) => {
    const row = record(item, "my listing");
    return {
      id: text(row.id, "id"),
      type: must(row.type, LISTING_TYPES, "type"),
      title: text(row.title, "title"),
      lifecycleStatus: must(row.lifecycle_status, LIFECYCLE, "lifecycle"),
      moderationStatus: must(row.moderation_status, MODERATION, "moderation"),
      moderationReason: optionalText(row.moderation_reason, "reason"),
      isPublic: row.is_public === true,
      authorityStatus: oneOf(row.authority_status, AUTHORITY, "authority"),
      pendingInterests: count(row.pending_interests, "pending_interests"),
      coverPhoto:
        row.cover_photo === null || row.cover_photo === undefined
          ? null
          : parsePhoto(row.cover_photo),
      updatedAt: text(row.updated_at, "updated_at"),
    };
  });
}

export function parseMyInterests(value: unknown): MyInterest[] {
  return list(value, "my interests").map((item) => {
    const row = record(item, "my interest");
    return {
      listingId: text(row.listing_id, "listing_id"),
      title: text(row.title, "title"),
      type: must(row.type, LISTING_TYPES, "type"),
      status: must(row.status, INTEREST, "status"),
      listingAvailable: row.listing_available === true,
      acknowledgedBrokerageAmount: optionalNumber(
        row.acknowledged_brokerage_amount,
        "acknowledged_brokerage_amount",
      ),
      createdAt: text(row.created_at, "created_at"),
      respondedAt: optionalText(row.responded_at, "responded_at"),
    };
  });
}

export function parseInterestedStudents(value: unknown): InterestedStudent[] {
  return list(value, "interested students").map((item) => {
    const row = record(item, "interested student");
    // Shaped like a discovery candidate, so the same profile card is used.
    const candidate = parseCandidate({
      student: row.student,
      compatibility: row.compatibility ?? {
        score: null,
        summary: "",
        factors: [],
        unavailable: [],
        area_overlap: "UNKNOWN",
        shared_societies: [],
      },
    });
    return {
      interestId: text(row.interest_id, "interest_id"),
      status: must(row.status, INTEREST, "status"),
      createdAt: text(row.created_at, "created_at"),
      respondedAt: optionalText(row.responded_at, "responded_at"),
      acknowledgedBrokerageAmount: optionalNumber(
        row.acknowledged_brokerage_amount,
        "acknowledged_brokerage_amount",
      ),
      candidate: row.compatibility
        ? candidate
        : { ...candidate, compatibility: undefined },
    };
  });
}
