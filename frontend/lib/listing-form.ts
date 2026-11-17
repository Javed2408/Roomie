/**
 * The shape, starting values and validation rules of the create-listing
 * form, plus a helper that turns the form's answers into a `Listing` so it
 * can be previewed exactly as other students will see it.
 *
 * Client-side validation is for fast feedback only. The backend must check
 * everything again, including who is allowed to list a property (Phase 6).
 */

import type { SelectOption } from "@/components/ui/select-field";
import { SOCIETIES } from "@/lib/mock/societies";
import { parseWholeNumber } from "@/lib/profile-form";
import {
  CREATOR_TYPE_LABELS,
  FURNISHING_LABELS,
  type Furnishing,
  type Listing,
  type ListingCreatorType,
  type ListingPoster,
} from "@/types/listing";
import type { Society } from "@/types/society";

// A `type` (not an `interface`) so it fits the form hook's value shape.
export type ListingFormValues = {
  listingType: string;
  title: string;
  description: string;
  // --- Room available ---
  creatorType: string;
  confirmedAuthority: boolean;
  societyId: string;
  rentPerPerson: string;
  deposit: string;
  brokerage: string;
  brokerageAmount: string;
  brokerageNote: string;
  bedroomCount: string;
  availableSpaces: string;
  furnishing: string;
  availableFrom: string;
  // --- Looking to rent together ---
  societyIds: string[];
  budgetPerPerson: string;
  desiredBedrooms: string;
  currentGroupSize: string;
  additionalRoommatesNeeded: string;
  moveInDate: string;
};

type ListingFieldName = keyof ListingFormValues & string;

export const TITLE_MAX_LENGTH = 80;
export const DESCRIPTION_MAX_LENGTH = 1000;

export const EMPTY_LISTING_VALUES: ListingFormValues = {
  listingType: "",
  title: "",
  description: "",
  creatorType: "",
  confirmedAuthority: false,
  societyId: "",
  rentPerPerson: "",
  deposit: "",
  brokerage: "",
  brokerageAmount: "",
  brokerageNote: "",
  bedroomCount: "",
  availableSpaces: "",
  furnishing: "",
  availableFrom: "",
  societyIds: [],
  budgetPerPerson: "",
  desiredBedrooms: "",
  currentGroupSize: "1",
  additionalRoommatesNeeded: "",
  moveInDate: "",
};

const ALL_SOCIETIES: Society[] = Object.values(SOCIETIES);

function toOptions(labels: Record<string, string>): SelectOption[] {
  return Object.entries(labels).map(([value, label]) => ({ value, label }));
}

export const LISTING_OPTIONS = {
  creatorType: toOptions(CREATOR_TYPE_LABELS),
  furnishing: toOptions(FURNISHING_LABELS),
  society: ALL_SOCIETIES.map((society) => ({
    value: society.id,
    label: `${society.name}, ${society.locality.name}`,
  })),
  brokerage: [
    { value: "NONE", label: "No brokerage" },
    { value: "APPLICABLE", label: "Brokerage applies" },
  ],
} satisfies Record<string, SelectOption[]>;

/** Check a whole-number field. Returns an error message or undefined. */
function validateNumber(
  value: string,
  options: { missing: string; min: number; max: number; range: string },
): string | undefined {
  if (!value.trim()) {
    return options.missing;
  }
  const amount = parseWholeNumber(value);
  if (amount === null) {
    return "Use numbers only.";
  }
  if (amount < options.min || amount > options.max) {
    return options.range;
  }
  return undefined;
}

const RENT_RULES = {
  min: 1000,
  max: 100000,
  range: "Enter ₹1,000 to ₹1,00,000.",
};
const ROOM_RULES = { min: 1, max: 6, range: "Enter a number from 1 to 6." };

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
  }
  if (!values.description.trim()) {
    errors.description = "Add a short description.";
  } else if (values.description.length > DESCRIPTION_MAX_LENGTH) {
    errors.description = `Use ${DESCRIPTION_MAX_LENGTH} characters or fewer.`;
  }

  if (values.listingType === "EXISTING_ACCOMMODATION") {
    if (!values.creatorType) {
      errors.creatorType = "Tell us your connection to it.";
    }
    if (!values.confirmedAuthority) {
      errors.confirmedAuthority = "Please confirm before continuing.";
    }
    if (!values.societyId) {
      errors.societyId = "Choose the society.";
    }
    errors.rentPerPerson = validateNumber(values.rentPerPerson, {
      missing: "Enter the rent per person.",
      ...RENT_RULES,
    });
    if (values.deposit.trim()) {
      errors.deposit = validateNumber(values.deposit, {
        missing: "",
        min: 0,
        max: 1000000,
        range: "Enter ₹0 to ₹10,00,000.",
      });
    }
    // Brokerage must always be answered, even when the answer is "none".
    if (!values.brokerage) {
      errors.brokerage = "Say whether brokerage applies.";
    } else if (values.brokerage === "APPLICABLE") {
      errors.brokerageAmount = validateNumber(values.brokerageAmount, {
        missing: "Enter the brokerage amount.",
        min: 1,
        max: 1000000,
        range: "Enter ₹1 to ₹10,00,000.",
      });
    }
    errors.bedroomCount = validateNumber(values.bedroomCount, {
      missing: "Enter the number of bedrooms.",
      ...ROOM_RULES,
    });
    errors.availableSpaces = validateNumber(values.availableSpaces, {
      missing: "Enter how many rooms are free.",
      ...ROOM_RULES,
    });
    const bedrooms = parseWholeNumber(values.bedroomCount);
    const spaces = parseWholeNumber(values.availableSpaces);
    if (
      !errors.bedroomCount &&
      !errors.availableSpaces &&
      bedrooms !== null &&
      spaces !== null &&
      spaces > bedrooms
    ) {
      errors.availableSpaces = "Cannot be more than the bedrooms.";
    }
    if (!values.furnishing) {
      errors.furnishing = "Choose the furnishing.";
    }
    if (!values.availableFrom) {
      errors.availableFrom = "Choose when it is available.";
    }
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
    errors.additionalRoommatesNeeded = validateNumber(
      values.additionalRoommatesNeeded,
      { missing: "Enter how many more you need.", ...ROOM_RULES },
    );
    if (!values.moveInDate) {
      errors.moveInDate = "Choose a move-in date.";
    }
  }

  return errors;
}

/** The fields checked for each listing type, in on-screen order. */
export const LISTING_FIELDS: Record<string, ListingFieldName[]> = {
  EXISTING_ACCOMMODATION: [
    "title",
    "creatorType",
    "societyId",
    "rentPerPerson",
    "deposit",
    "brokerage",
    "brokerageAmount",
    "bedroomCount",
    "availableSpaces",
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
    "additionalRoommatesNeeded",
    "moveInDate",
    "description",
  ],
};

/**
 * Build a `Listing` from valid form values, for the preview screen.
 * A new listing always starts unverified and pending review.
 */
export function buildListingPreview(
  values: ListingFormValues,
  postedBy: ListingPoster,
): Listing {
  const base = {
    id: "listing-preview",
    title: values.title.trim(),
    description: values.description.trim(),
    postedBy,
    moderationStatus: "PENDING",
    lifecycleStatus: "DRAFT",
  } as const;
  const number = (value: string) => parseWholeNumber(value) ?? 0;
  const society = (id: string) =>
    ALL_SOCIETIES.find((item) => item.id === id) ?? ALL_SOCIETIES[0];

  if (values.listingType === "EXISTING_ACCOMMODATION") {
    const chosenSociety = society(values.societyId);
    if (!chosenSociety) {
      throw new Error("The society directory is empty.");
    }
    return {
      ...base,
      type: "EXISTING_ACCOMMODATION",
      // Safe: validation only passes when these hold one of the listed values.
      creatorType: values.creatorType as ListingCreatorType,
      furnishing: values.furnishing as Furnishing,
      listingAuthority: "NOT_VERIFIED",
      society: chosenSociety,
      rentPerPerson: number(values.rentPerPerson),
      deposit: values.deposit.trim() ? number(values.deposit) : null,
      brokerage:
        values.brokerage === "APPLICABLE"
          ? {
              applicable: true,
              amount: number(values.brokerageAmount),
              note: values.brokerageNote.trim() || undefined,
            }
          : { applicable: false },
      bedroomCount: number(values.bedroomCount),
      availableSpaces: number(values.availableSpaces),
      availableFrom: values.availableFrom,
    };
  }

  return {
    ...base,
    type: "LOOKING_TO_RENT_TOGETHER",
    preferredSocieties: values.societyIds
      .map((id) => ALL_SOCIETIES.find((item) => item.id === id))
      .filter((item): item is Society => item !== undefined),
    budgetPerPerson: number(values.budgetPerPerson),
    desiredBedrooms: number(values.desiredBedrooms),
    currentGroupSize: number(values.currentGroupSize),
    additionalRoommatesNeeded: number(values.additionalRoommatesNeeded),
    moveInDate: values.moveInDate,
  };
}
