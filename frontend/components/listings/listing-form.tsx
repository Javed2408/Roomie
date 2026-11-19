"use client";

import { ArrowLeft, DoorOpen, Users, type LucideIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { SocietyPicker } from "@/components/profile/society-picker";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { ChoiceGroup } from "@/components/ui/choice-group";
import { SelectField } from "@/components/ui/select-field";
import { TextField } from "@/components/ui/text-field";
import { TextAreaField } from "@/components/ui/textarea-field";
import { useForm, type UseFormResult } from "@/hooks/use-form";
import {
  DESCRIPTION_MAX_LENGTH,
  EMPTY_LISTING_VALUES,
  LISTING_OPTIONS,
  MAX_SEARCH_SOCIETIES,
  TITLE_MAX_LENGTH,
  listingToValues,
  toListingInput,
  validateListing,
  type ListingFormValues,
} from "@/lib/listing-form";
import { ApiError, describeApiError } from "@/services/api-client";
import { createListing, updateListing } from "@/services/listings";
import type { ListingType, OwnListing } from "@/types/listing";
import type { Society } from "@/types/society";

type Form = UseFormResult<ListingFormValues>;

// What each kind of lister must prove before the listing can be approved.
// These match the rules the backend enforces (docs/DATABASE_SCHEMA.md).
const EVIDENCE_HINT_DEFAULT = "Unauthorised brokers are not allowed on Roomie.";
const EVIDENCE_HINTS: Record<string, string> = {
  PROPERTY_OWNER:
    "Next you will upload proof of ownership. Identity verification is also needed.",
  EXISTING_TENANT:
    "Next you will upload your rental agreement, and the landlord's written permission unless the agreement allows sharing.",
  AUTHORIZED_AGENT:
    "Next you will upload the owner's written authorisation and give the owner's contact, so Roomie can confirm with them directly. Identity verification is also needed.",
};

const TYPE_CHOICES: Array<{
  type: ListingType;
  icon: LucideIcon;
  title: string;
  description: string;
}> = [
  {
    type: "EXISTING_ACCOMMODATION",
    icon: DoorOpen,
    title: "I have a room available",
    description:
      "You own the flat, rent it with permission to share, or are an agent the owner has authorised. You will be asked for evidence.",
  },
  {
    type: "LOOKING_TO_RENT_TOGETHER",
    icon: Users,
    title: "Let's find a place together",
    description:
      "You do not have a flat yet and want people to rent one with. This is a request, not a property.",
  },
];

/** Turn the backend's field-by-field complaints into one readable message. */
function saveErrorMessage(error: unknown): string {
  if (
    error instanceof ApiError &&
    error.code === "validation_error" &&
    Array.isArray(error.details)
  ) {
    const messages = error.details
      .map((item: unknown) =>
        typeof item === "object" && item !== null && "message" in item
          ? String(item.message).replace(/^Value error, /, "")
          : null,
      )
      .filter((message): message is string => Boolean(message));
    if (messages.length > 0) {
      return [...new Set(messages)].join(" ");
    }
  }
  return describeApiError(error);
}

function FacilityChoices({ form }: { form: Form }) {
  const chosen = new Set(form.values.facilities);
  return (
    <fieldset>
      <legend className="text-foreground mb-1.5 text-sm font-medium">
        Facilities (optional)
      </legend>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-3">
        {LISTING_OPTIONS.facilities.map((option) => (
          <Checkbox
            key={option.value}
            name="facilities"
            value={option.value}
            checked={chosen.has(option.value)}
            onChange={(event) =>
              form.setValue(
                "facilities",
                event.target.checked
                  ? [...form.values.facilities, option.value]
                  : form.values.facilities.filter(
                      (item) => item !== option.value,
                    ),
              )
            }
          >
            {option.label}
          </Checkbox>
        ))}
      </div>
    </fieldset>
  );
}

function PropertyFields({
  form,
  savedSocieties,
}: {
  form: Form;
  savedSocieties: Society[];
}) {
  const brokerageApplies = form.values.brokerage === "APPLICABLE";
  return (
    <>
      <SelectField
        label="Your connection to the property"
        placeholder="Choose one"
        options={LISTING_OPTIONS.creatorType}
        hint={EVIDENCE_HINTS[form.values.creatorType] ?? EVIDENCE_HINT_DEFAULT}
        {...form.text("creatorType")}
      />
      <SocietyPicker
        label="Society"
        name="societyIds"
        value={form.values.societyIds}
        onChange={(ids) => {
          form.setValue("societyIds", ids);
          form.markTouched("societyIds");
        }}
        savedSocieties={savedSocieties}
        max={1}
        hint="Only verified societies can be chosen. Never write a flat number or exact address anywhere."
        error={form.errors.societyIds}
      />
      <div className="grid gap-x-4 gap-y-2 sm:grid-cols-3">
        <TextField
          label="Rent per person (₹ / month)"
          inputMode="numeric"
          {...form.text("rentPerPerson")}
        />
        <TextField
          label="Whole flat (₹ / month, optional)"
          inputMode="numeric"
          {...form.text("totalRent")}
        />
        <TextField
          label="Deposit (₹, optional)"
          inputMode="numeric"
          {...form.text("deposit")}
        />
      </div>
      <ChoiceGroup
        label="Brokerage"
        name="brokerage"
        options={LISTING_OPTIONS.brokerage}
        value={form.values.brokerage}
        onChange={(value) => {
          form.setValue("brokerage", value);
          form.markTouched("brokerage");
        }}
        hint="Shown on your listing either way, before anyone expresses interest. Roomie never collects payments."
        error={form.errors.brokerage}
      />
      {brokerageApplies && (
        <div className="grid gap-x-4 gap-y-2 sm:grid-cols-2">
          <TextField
            label="Brokerage amount (₹)"
            inputMode="numeric"
            {...form.text("brokerageAmount")}
          />
          <SelectField
            label="Paid to"
            placeholder="Choose one"
            options={LISTING_OPTIONS.payableTo}
            hint="Only an authorised agent may collect it themselves."
            {...form.text("brokeragePayableTo")}
          />
          <div className="sm:col-span-2">
            <TextField
              label="How it is charged (optional)"
              hint="For example: one-time, split between tenants."
              {...form.text("brokerageNote")}
            />
          </div>
        </div>
      )}
      <div className="grid gap-x-4 gap-y-2 sm:grid-cols-2">
        <TextField
          label="Bedrooms in the flat"
          inputMode="numeric"
          {...form.text("bedroomCount")}
        />
        <TextField
          label="Bedrooms free"
          inputMode="numeric"
          {...form.text("availableBedrooms")}
        />
        <TextField
          label="People living there now"
          inputMode="numeric"
          {...form.text("currentOccupants")}
        />
        <TextField
          label="Flatmates wanted"
          inputMode="numeric"
          {...form.text("roommatesWanted")}
        />
        <SelectField
          label="Furnishing"
          placeholder="Choose one"
          options={LISTING_OPTIONS.furnishing}
          {...form.text("furnishing")}
        />
        <TextField
          label="Available from"
          type="date"
          {...form.text("availableFrom")}
        />
      </div>
      <FacilityChoices form={form} />
    </>
  );
}

function RentTogetherFields({
  form,
  savedSocieties,
}: {
  form: Form;
  savedSocieties: Society[];
}) {
  return (
    <>
      <SocietyPicker
        label="Societies you are hoping for"
        name="societyIds"
        value={form.values.societyIds}
        onChange={(ids) => {
          form.setValue("societyIds", ids);
          form.markTouched("societyIds");
        }}
        savedSocieties={savedSocieties}
        max={MAX_SEARCH_SOCIETIES}
        hint={`Up to ${MAX_SEARCH_SOCIETIES}, most preferred first.`}
        error={form.errors.societyIds}
      />
      <div className="grid gap-x-4 gap-y-2 sm:grid-cols-2">
        <TextField
          label="Budget per person (₹ / month)"
          inputMode="numeric"
          {...form.text("budgetPerPerson")}
        />
        <TextField
          label="Bedrooms wanted"
          inputMode="numeric"
          {...form.text("desiredBedrooms")}
        />
        <TextField
          label="People in your group now"
          inputMode="numeric"
          hint="Count yourself."
          {...form.text("currentGroupSize")}
        />
        <TextField
          label="More people needed"
          inputMode="numeric"
          {...form.text("roommatesWanted")}
        />
        <TextField
          label="Move-in date"
          type="date"
          {...form.text("moveInDate")}
        />
      </div>
    </>
  );
}

function savedSocietiesOf(existing: OwnListing | undefined): Society[] {
  if (!existing) {
    return [];
  }
  const listing = existing.listing;
  return listing.type === "EXISTING_ACCOMMODATION"
    ? [listing.society]
    : listing.preferredSocieties;
}

/**
 * Create a listing (choose the type, then fill in the details), or edit
 * one. Saving creates a private draft and opens its management page,
 * where photos and evidence are added and it is submitted for review.
 */
export function ListingForm({ existing }: { existing?: OwnListing }) {
  const router = useRouter();
  const isEdit = existing !== undefined;
  const [stage, setStage] = useState<"type" | "details">(
    isEdit ? "details" : "type",
  );
  const fieldsRef = useRef<HTMLDivElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const isFirstRender = useRef(true);
  const savedSocieties = savedSocietiesOf(existing);

  const form = useForm<ListingFormValues>({
    initialValues: existing
      ? listingToValues(existing.listing)
      : EMPTY_LISTING_VALUES,
    validate: validateListing,
    onSubmit: async (values) => {
      try {
        const input = toListingInput(values);
        const saved = existing
          ? await updateListing(existing.listing.id, input)
          : await createListing(input);
        router.push(`/accommodation/mine/${saved.listing.id}`);
        return { ok: true };
      } catch (error) {
        return { ok: false, message: saveErrorMessage(error) };
      }
    },
  });

  // Move focus to the heading whenever the stage changes.
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    headingRef.current?.focus();
  }, [stage]);

  const isProperty = form.values.listingType === "EXISTING_ACCOMMODATION";

  function chooseType(type: ListingType) {
    form.setValue("listingType", type);
    form.setValue("societyIds", []);
    setStage("details");
  }

  const heading =
    stage === "type"
      ? "What are you posting?"
      : isProperty
        ? "About the room"
        : "About your search";

  return (
    <div>
      <h2
        ref={headingRef}
        tabIndex={-1}
        className="mb-5 text-xl font-semibold outline-none"
      >
        {heading}
      </h2>

      {stage === "type" && (
        <ul className="grid gap-4 sm:grid-cols-2">
          {TYPE_CHOICES.map(({ type, icon: Icon, title, description }) => (
            <li key={type}>
              <button
                type="button"
                onClick={() => chooseType(type)}
                className="rounded-card border-border bg-surface hover:border-primary h-full w-full border p-5 text-left transition-colors duration-150"
              >
                <span className="bg-primary-soft text-primary-strong flex size-11 items-center justify-center rounded-full">
                  <Icon aria-hidden="true" className="size-5" />
                </span>
                <span className="font-display text-foreground mt-4 block text-lg font-semibold">
                  {title}
                </span>
                <span className="text-muted mt-1 block text-sm leading-relaxed">
                  {description}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {stage === "details" && (
        <form {...form.formProps}>
          {existing?.moderationStatus === "APPROVED" && (
            <Alert tone="warning" className="mb-5">
              Your listing is live. Saving changes sends it back for review, and
              it is hidden until Roomie approves the change.
            </Alert>
          )}
          {isEdit && isProperty && (
            <Alert tone="info" className="mb-5">
              Changing the society or your connection to the property means your
              evidence of authority has to be checked again.
            </Alert>
          )}
          <Card padding="lg">
            <div ref={fieldsRef} className="space-y-2">
              <TextField
                label="Title"
                hint={`A short summary, up to ${TITLE_MAX_LENGTH} characters. No phone numbers or emails.`}
                maxLength={TITLE_MAX_LENGTH}
                {...form.text("title")}
              />
              {isProperty ? (
                <PropertyFields form={form} savedSocieties={savedSocieties} />
              ) : (
                <RentTogetherFields
                  form={form}
                  savedSocieties={savedSocieties}
                />
              )}
              <TextAreaField
                label="Description"
                hint={
                  isProperty
                    ? "What is the flat like, and who would suit it? No contact details: people reach you through Roomie."
                    : "Who are you, and what kind of flatmate are you looking for?"
                }
                maxLength={DESCRIPTION_MAX_LENGTH}
                {...form.text("description")}
              />
              {isProperty && (
                <Checkbox
                  name="confirmedAuthority"
                  checked={form.values.confirmedAuthority}
                  onChange={(event) =>
                    form.setValue("confirmedAuthority", event.target.checked)
                  }
                  error={form.errors.confirmedAuthority}
                >
                  I confirm I own this property, or I have the owner&apos;s
                  permission to offer it, and I will provide evidence. I
                  understand this statement alone does not verify anything.
                </Checkbox>
              )}
            </div>
          </Card>

          {form.formError && (
            <Alert tone="danger" role="alert" className="mt-5">
              {form.formError}
            </Alert>
          )}

          <div className="mt-6 flex items-center justify-between gap-3">
            {isEdit ? (
              <Button variant="ghost" onClick={() => router.back()}>
                <ArrowLeft aria-hidden="true" className="size-4" />
                Cancel
              </Button>
            ) : (
              <Button variant="ghost" onClick={() => setStage("type")}>
                <ArrowLeft aria-hidden="true" className="size-4" />
                Back
              </Button>
            )}
            <Button type={form.submitType} isLoading={form.isSubmitting}>
              {isEdit ? "Save changes" : "Save draft"}
            </Button>
          </div>
          {!isEdit && (
            <p className="text-muted mt-3 text-right text-sm">
              Drafts are private. You will add photos
              {isProperty ? " and evidence" : ""} next, then submit for review.
            </p>
          )}
        </form>
      )}
    </div>
  );
}
