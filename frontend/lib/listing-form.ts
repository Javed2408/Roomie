/**
 * The shape, starting values and validation rules of the listing form,
 * and conversions between the form, the API input and a saved listing.
 *
 * Client-side validation is for fast feedback only. The backend checks
 * everything again (backend/app/schemas/listing.py), including who is
 * allowed to list a property, which no form answer can decide.
 */

import type { SelectOption } from "@/components/ui/select-field";
import { parseWholeNumber } from "@/lib/profile-form";
import type { ListingInput } from "@/services/listings";
import {
  BROKERAGE_PAYABLE_TO_LABELS,
  CREATOR_TYPE_LABELS,
  FACILITY_LABELS,
  FURNISHING_LABELS,
  type BrokeragePayableTo,
  type Facility,
  type Furnishing,
  type Listing,
  type ListingCreatorType,
} from "@/types/listing";

// A `type` (not an `interface`) so it fits the form hook's value shape.
export type ListingFormValues = {
  listingType: string;
  title: string;
  description: string;
  /** Property: one society. Rent together: up to five, most preferred first. */
  societyIds: string[];
  // --- Room available ---
  creatorType: string;
  confirmedAuthority: boolean;
  rentPerPerson: string;
  totalRent: string;
  deposit: string;
  brokerage: string;
  brokerageAmount: string;
  brokeragePayableTo: string;
  brokerageNote: string;
  bedroomCount: string;
  availableBedrooms: string;
  furnishing: string;
  facilities: string[];
  availableFrom: string;
  currentOccupants: string;
  // --- Looking to rent together ---
  budgetPerPerson: string;
  desiredBedrooms: string;
  currentGroupSize: string;
  moveInDate: string;
  // --- Both ---
  roommatesWanted: string;
};

type ListingFieldName = keyof ListingFormValues & string;

export const TITLE_MAX_LENGTH = 80;
export const DESCRIPTION_MAX_LENGTH = 1000;
export const MAX_SEARCH_SOCIETIES = 5;

export const EMPTY_LISTING_VALUES: ListingFormValues = {
  listingType: "",
  title: "",
  description: "",
  societyIds: [],
  creatorType: "",
  confirmedAuthority: false,
  rentPerPerson: "",
  totalRent: "",
  deposit: "",
  brokerage: "",
  brokerageAmount: "",
  brokeragePayableTo: "",
  brokerageNote: "",
  bedroomCount: "",
  availableBedrooms: "",
  furnishing: "",
  facilities: [],
  availableFrom: "",
  currentOccupants: "",
  budgetPerPerson: "",
  desiredBedrooms: "",
  currentGroupSize: "1",
  moveInDate: "",
  roommatesWanted: "",
};

function toOptions(labels: Record<string, string>): SelectOption[] {
  return Object.entries(labels).map(([value, label]) => ({ value, label }));
}

export const LISTING_OPTIONS = {
  creatorType: toOptions(CREATOR_TYPE_LABELS),
  furnishing: toOptions(FURNISHING_LABELS),
  facilities: toOptions(FACILITY_LABELS),
  brokerage: [
    { value: "NONE", label: "No brokerage" },
    { value: "APPLICABLE", label: "Brokerage applies" },
  ],
  payableTo: Object.entries(BROKERAGE_PAYABLE_TO_LABELS).map(
    ([value, label]) => ({
      value,
      label: label.charAt(0).toUpperCase() + label.slice(1),
    }),
  ),
} satisfies Record<string, SelectOption[]>;

// The same signals the backend refuses: contact details would let someone
// take the conversation off Roomie before anyone's authority is checked.
const PHONE = /(?:\+?91[\s-]?)?(?<!\d)[6-9]\d{4}[\s-]?\d{5}(?!\d)/;
const EMAIL = /[\w.+-]+@[\w-]+\.[\w.-]+/;
const NO_CONTACT = "Remove phone numbers and email addresses.";

function validateNumber(
  value: string,
  options: { missing: string; min: number; max: number; range: string },
): string | undefined {
  if (!value.trim()) {
    return options.missing;
  }
  const amount = parseWholeNumber(value);
  if (amount === null) {
    return "Use whole numbers only.";
  }
  if (amount < options.min || amount > options.max) {
    return options.range;
  }
  return undefined;
}

function optionalNumber(
  value: string,
  options: { min: number; max: number; range: string },
): string | undefined {
  return value.trim()
    ? validateNumber(value, { missing: "", ...options })
    : undefined;
}

function validateDate(value: string, missing: string): string | undefined {
  if (!value) {
    return missing;
  }
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const chosen = new Date(`${value}T00:00:00`);
  if (Number.isNaN(chosen.getTime())) {
    return "Choose a valid date.";
  }
  if (chosen < today) {
    return "The date cannot be in the past.";
  }
  const limit = new Date(today);
  limit.setDate(limit.getDate() + 366);
  if (chosen > limit) {
    return "Choose a date within the next year.";
  }
  return undefined;
}

const RENT_RULES = {
  min: 1000,
  max: 100000,
  range: "Enter ₹1,000 to ₹1,00,000.",
};
const BIG_AMOUNT = {
  min: 1,
  max: 1000000,
  range: "Enter ₹1 to ₹10,00,000.",
};
const ROOM_RULES = { min: 1, max: 10, range: "Enter a number from 1 to 10." };

export function validateListing(
  values: ListingFormValues,
): Partial<Record<ListingFieldName, string>> {
  const errors: Partial<Record<ListingFieldName, string>> = {};

  if (!values.listingType) {
    errors.listingType = "Choose what you are posting.";
    return errors;
  }

  if (!values.title.trim()) {
    errors.title = "Give your post a title.";
  } else if (values.title.length > TITLE_MAX_LENGTH) {
    errors.title = `Use ${TITLE_MAX_LENGTH} characters or fewer.`;
  } else if (PHONE.test(values.title) || EMAIL.test(values.title)) {
    errors.title = NO_CONTACT;
  }
  if (!values.description.trim()) {
    errors.description = "Add a short description.";
  } else if (values.description.length > DESCRIPTION_MAX_LENGTH) {
    errors.description = `Use ${DESCRIPTION_MAX_LENGTH} characters or fewer.`;
  } else if (PHONE.test(values.description) || EMAIL.test(values.description)) {
    errors.description = NO_CONTACT;
  }
  errors.roommatesWanted = validateNumber(values.roommatesWanted, {
    missing: "Enter how many more people you want.",
    ...ROOM_RULES,
  });

  if (values.listingType === "EXISTING_ACCOMMODATION") {
    if (!values.creatorType) {
      errors.creatorType = "Tell us your connection to the property.";
    }
    if (!values.confirmedAuthority) {
      errors.confirmedAuthority = "Please confirm before continuing.";
    }
    if (values.societyIds.length !== 1) {
      errors.societyIds = "Choose the society the property is in.";
    }
    errors.rentPerPerson = validateNumber(values.rentPerPerson, {
      missing: "Enter the rent per person.",
      ...RENT_RULES,
    });
    errors.totalRent = optionalNumber(values.totalRent, {
      min: 1000,
      max: 1000000,
      range: "Enter ₹1,000 to ₹10,00,000.",
    });
    errors.deposit = optionalNumber(values.deposit, {
      ...BIG_AMOUNT,
      min: 0,
      range: "Enter ₹0 to ₹10,00,000.",
    });
    // Brokerage must always be answered, even when the answer is "none".
    if (!values.brokerage) {
      errors.brokerage = "Say whether brokerage applies.";
    } else if (values.brokerage === "APPLICABLE") {
      errors.brokerageAmount = validateNumber(values.brokerageAmount, {
        missing: "Enter the brokerage amount.",
        ...BIG_AMOUNT,
      });
      if (!values.brokeragePayableTo) {
        errors.brokeragePayableTo = "Say who receives the brokerage.";
      } else if (
        values.brokeragePayableTo === "LISTING_CREATOR" &&
        values.creatorType !== "AUTHORIZED_AGENT"
      ) {
        errors.brokeragePayableTo =
          "Only an authorised agent can collect brokerage. Owners and tenants cannot charge it themselves.";
      }
      if (
        PHONE.test(values.brokerageNote) ||
        EMAIL.test(values.brokerageNote)
      ) {
        errors.brokerageNote = NO_CONTACT;
      }
    }
    errors.bedroomCount = validateNumber(values.bedroomCount, {
      missing: "Enter the number of bedrooms.",
      ...ROOM_RULES,
    });
    errors.availableBedrooms = validateNumber(values.availableBedrooms, {
      missing: "Enter how many rooms are free.",
      ...ROOM_RULES,
    });
    const bedrooms = parseWholeNumber(values.bedroomCount);
    const free = parseWholeNumber(values.availableBedrooms);
    if (
      !errors.bedroomCount &&
      !errors.availableBedrooms &&
      bedrooms !== null &&
      free !== null &&
      free > bedrooms
    ) {
      errors.availableBedrooms = "Cannot be more than the bedrooms.";
    }
    errors.currentOccupants = validateNumber(values.currentOccupants, {
      missing: "Enter how many people live there now.",
      min: 0,
      max: 10,
      range: "Enter a number from 0 to 10.",
    });
    if (!values.furnishing) {
      errors.furnishing = "Choose the furnishing.";
    }
    errors.availableFrom = validateDate(
      values.availableFrom,
      "Choose when it is available.",
    );
  } else {
    if (values.societyIds.length === 0) {
      errors.societyIds = "Choose at least one society.";
    }
    errors.budgetPerPerson = validateNumber(values.budgetPerPerson, {
      missing: "Enter the budget per person.",
      ...RENT_RULES,
    });
    errors.desiredBedrooms = validateNumber(values.desiredBedrooms, {
      missing: "Enter the bedrooms you want.",
      ...ROOM_RULES,
    });
    errors.currentGroupSize = validateNumber(values.currentGroupSize, {
      missing: "Enter your group size.",
      ...ROOM_RULES,
    });
    errors.moveInDate = validateDate(
      values.moveInDate,
      "Choose a move-in date.",
    );
  }

  return errors;
}

/** The fields checked for each listing type, in on-screen order. */
export const LISTING_FIELDS: Record<string, ListingFieldName[]> = {
  EXISTING_ACCOMMODATION: [
    "title",
    "creatorType",
    "societyIds",
    "rentPerPerson",
    "totalRent",
    "deposit",
    "brokerage",
    "brokerageAmount",
    "brokeragePayableTo",
    "brokerageNote",
    "bedroomCount",
    "availableBedrooms",
    "currentOccupants",
    "roommatesWanted",
    "furnishing",
    "availableFrom",
    "description",
    "confirmedAuthority",
  ],
  LOOKING_TO_RENT_TOGETHER: [
    "title",
    "societyIds",
    "budgetPerPerson",
    "desiredBedrooms",
    "currentGroupSize",
    "roommatesWanted",
    "moveInDate",
    "description",
  ],
};

const whole = (value: string) => parseWholeNumber(value) ?? 0;
const wholeOrNull = (value: string) =>
  value.trim() ? parseWholeNumber(value) : null;

/** Valid form values -> what the API expects. */
export function toListingInput(values: ListingFormValues): ListingInput {
  const title = values.title.trim();
  const description = values.description.trim();
  if (values.listingType === "LOOKING_TO_RENT_TOGETHER") {
    return {
      listingType: "LOOKING_TO_RENT_TOGETHER",
      title,
      description,
      societyIds: values.societyIds,
      budgetPerPerson: whole(values.budgetPerPerson),
      desiredBedrooms: whole(values.desiredBedrooms),
      currentGroupSize: whole(values.currentGroupSize),
      roommatesWanted: whole(values.roommatesWanted),
      moveInDate: values.moveInDate,
    };
  }
  return {
    listingType: "EXISTING_ACCOMMODATION",
    title,
    description,
    // Safe: validation only passes when these hold one of the listed values.
    creatorType: values.creatorType as ListingCreatorType,
    societyId: values.societyIds[0] ?? "",
    rentPerPerson: whole(values.rentPerPerson),
    totalRent: wholeOrNull(values.totalRent),
    deposit: wholeOrNull(values.deposit),
    brokerage:
      values.brokerage === "APPLICABLE"
        ? {
            applicable: true,
            amount: whole(values.brokerageAmount),
            payableTo: values.brokeragePayableTo as BrokeragePayableTo,
            note: values.brokerageNote.trim() || null,
          }
        : { applicable: false },
    bedroomCount: whole(values.bedroomCount),
    availableBedrooms: whole(values.availableBedrooms),
    furnishing: values.furnishing as Furnishing,
    facilities: values.facilities as Facility[],
    availableFrom: values.availableFrom,
    currentOccupants: whole(values.currentOccupants),
    roommatesWanted: whole(values.roommatesWanted),
    confirmedAuthority: true,
  };
}

/** A saved listing -> form values, for editing it. */
export function listingToValues(listing: Listing): ListingFormValues {
  const base = {
    ...EMPTY_LISTING_VALUES,
    listingType: listing.type,
    title: listing.title,
    description: listing.description,
    roommatesWanted: String(listing.roommatesWanted),
  };
  if (listing.type === "LOOKING_TO_RENT_TOGETHER") {
    return {
      ...base,
      societyIds: listing.preferredSocieties.map((society) => society.id),
      budgetPerPerson: String(listing.budgetPerPerson),
      desiredBedrooms: String(listing.desiredBedrooms),
      currentGroupSize: String(listing.currentGroupSize),
      moveInDate: listing.moveInDate,
    };
  }
  const brokerage = listing.brokerage;
  return {
    ...base,
    societyIds: [listing.society.id],
    creatorType: listing.creatorType,
    // The declaration is made again with every edit.
    confirmedAuthority: false,
    rentPerPerson: String(listing.rentPerPerson),
    totalRent: listing.totalRent === null ? "" : String(listing.totalRent),
    deposit: listing.deposit === null ? "" : String(listing.deposit),
    brokerage: brokerage.applicable ? "APPLICABLE" : "NONE",
    brokerageAmount: brokerage.applicable ? String(brokerage.amount) : "",
    brokeragePayableTo: brokerage.applicable ? brokerage.payableTo : "",
    brokerageNote: brokerage.applicable ? (brokerage.note ?? "") : "",
    bedroomCount: String(listing.bedroomCount),
    availableBedrooms: String(listing.availableBedrooms),
    furnishing: listing.furnishing ?? "",
    facilities: listing.facilities,
    availableFrom: listing.availableFrom,
    currentOccupants: String(listing.currentOccupants),
  };
}
