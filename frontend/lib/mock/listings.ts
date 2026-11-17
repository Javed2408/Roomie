/**
 * SAMPLE DATA — invented listings for building and reviewing screens only.
 *
 * These are not real properties or real people. Every verification field is
 * "NOT_VERIFIED" on purpose: nothing has been checked, so nothing may be
 * shown as verified. `moderationStatus` is "APPROVED" only because the
 * public directory will show approved listings; no review has taken place.
 *
 * Any screen that shows this data must display a "Sample data" label.
 */

import { SOCIETIES } from "@/lib/mock/societies";
import type { Listing, ListingPoster } from "@/types/listing";

export const LISTINGS: Listing[] = [
  {
    id: "listing-1",
    type: "EXISTING_ACCOMMODATION",
    title: "One room free in a 3BHK",
    description:
      "Two of us are staying on and one room opens up in January. Cupboard, bed and study table included.",
    postedBy: {
      id: "user-rohan",
      displayName: "Rohan M.",
      identityVerification: "NOT_VERIFIED",
    },
    creatorType: "EXISTING_TENANT",
    listingAuthority: "NOT_VERIFIED",
    moderationStatus: "APPROVED",
    lifecycleStatus: "ACTIVE",
    society: SOCIETIES.lakeside,
    rentPerPerson: 9500,
    deposit: 19000,
    brokerage: { applicable: false },
    bedroomCount: 3,
    availableSpaces: 1,
    furnishing: "SEMI_FURNISHED",
    availableFrom: "2027-01-05",
  },
  {
    id: "listing-2",
    type: "LOOKING_TO_RENT_TOGETHER",
    title: "Two of us looking for a third",
    description:
      "We are two second-years planning to rent a 3BHK from mid-January. Looking for one more person who keeps reasonable hours.",
    postedBy: {
      id: "user-divya",
      displayName: "Divya K.",
      identityVerification: "NOT_VERIFIED",
    },
    moderationStatus: "APPROVED",
    lifecycleStatus: "ACTIVE",
    preferredSocieties: [SOCIETIES.mapleCourt, SOCIETIES.greenfield],
    budgetPerPerson: 10000,
    desiredBedrooms: 3,
    currentGroupSize: 2,
    additionalRoommatesNeeded: 1,
    moveInDate: "2027-01-15",
  },
  {
    id: "listing-3",
    type: "EXISTING_ACCOMMODATION",
    title: "2BHK, both rooms available",
    description:
      "Second-floor flat with a balcony. Available to two students renting together or separately.",
    postedBy: {
      id: "user-suresh",
      displayName: "Suresh P.",
      identityVerification: "NOT_VERIFIED",
    },
    creatorType: "AUTHORIZED_AGENT",
    listingAuthority: "NOT_VERIFIED",
    moderationStatus: "APPROVED",
    lifecycleStatus: "ACTIVE",
    society: SOCIETIES.palmGrove,
    rentPerPerson: 8000,
    deposit: 16000,
    brokerage: {
      applicable: true,
      amount: 8000,
      note: "One-time, per flat",
    },
    bedroomCount: 2,
    availableSpaces: 2,
    furnishing: "UNFURNISHED",
    availableFrom: "2027-02-01",
  },
];

/** The sample student as a listing poster. */
export const CURRENT_USER_AS_POSTER: ListingPoster = {
  id: "user-current",
  displayName: "Ananya R.",
  identityVerification: "NOT_VERIFIED",
};

/**
 * Listings created by the sample student, one in each review state, so the
 * "My listings" screen can show how each state looks. No real review has
 * happened: "APPROVED" here is example data, not an approval.
 */
export const MY_LISTINGS: Listing[] = [
  {
    id: "my-listing-1",
    type: "LOOKING_TO_RENT_TOGETHER",
    title: "Looking for two flatmates for January",
    description:
      "Second-year CS student looking for one or two easygoing people to rent a 3BHK with.",
    postedBy: CURRENT_USER_AS_POSTER,
    moderationStatus: "APPROVED",
    lifecycleStatus: "ACTIVE",
    preferredSocieties: [SOCIETIES.lakeside, SOCIETIES.mapleCourt],
    budgetPerPerson: 11000,
    desiredBedrooms: 3,
    currentGroupSize: 1,
    additionalRoommatesNeeded: 2,
    moveInDate: "2027-01-05",
  },
  {
    id: "my-listing-2",
    type: "EXISTING_ACCOMMODATION",
    title: "Spare room from February",
    description:
      "My flatmate is leaving in February, so one furnished room opens up.",
    postedBy: CURRENT_USER_AS_POSTER,
    creatorType: "EXISTING_TENANT",
    listingAuthority: "NOT_VERIFIED",
    moderationStatus: "PENDING",
    lifecycleStatus: "ACTIVE",
    society: SOCIETIES.greenfield,
    rentPerPerson: 10500,
    deposit: 21000,
    brokerage: { applicable: false },
    bedroomCount: 2,
    availableSpaces: 1,
    furnishing: "FULLY_FURNISHED",
    availableFrom: "2027-02-10",
  },
  {
    id: "my-listing-3",
    type: "EXISTING_ACCOMMODATION",
    title: "Room near the main gate",
    description: "Call me for the exact flat number and directions.",
    postedBy: CURRENT_USER_AS_POSTER,
    creatorType: "EXISTING_TENANT",
    listingAuthority: "NOT_VERIFIED",
    moderationStatus: "REJECTED",
    moderationNote:
      "The description asks people to call for the exact address. Please remove contact details and resubmit.",
    lifecycleStatus: "CLOSED",
    society: SOCIETIES.sunrise,
    rentPerPerson: 7500,
    deposit: null,
    brokerage: { applicable: false },
    bedroomCount: 2,
    availableSpaces: 1,
    furnishing: "SEMI_FURNISHED",
    availableFrom: "2027-01-20",
  },
];

/** Find any sample listing, public or the student's own, by its id. */
export function findListing(id: string): Listing | undefined {
  return [...LISTINGS, ...MY_LISTINGS].find((listing) => listing.id === id);
}
