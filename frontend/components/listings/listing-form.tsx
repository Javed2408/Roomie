"use client";

import { ArrowLeft, DoorOpen, Users, type LucideIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { SuccessPanel } from "@/components/auth/success-panel";
import { ListingCard } from "@/components/listings/listing-card";
import { SampleSocietyPicker } from "@/components/listings/sample-society-picker";
import { Alert } from "@/components/ui/alert";
import { Button, ButtonLink } from "@/components/ui/button";
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
  LISTING_FIELDS,
  LISTING_OPTIONS,
  TITLE_MAX_LENGTH,
  buildListingPreview,
  validateListing,
  type ListingFormValues,
} from "@/lib/listing-form";
import { SOCIETIES } from "@/lib/mock/societies";
import { submitListing } from "@/services/mock-api";
import type { ListingPoster, ListingType } from "@/types/listing";

type Stage = "type" | "details" | "preview" | "done";
type Form = UseFormResult<ListingFormValues>;

const ALL_SOCIETIES = Object.values(SOCIETIES);

// What each kind of lister must prove before the listing can be approved.
// These match the rules the backend enforces (docs/DATABASE_SCHEMA.md 3.7).
const EVIDENCE_HINT_DEFAULT = "Unauthorised brokers are not allowed on Roomie.";
const EVIDENCE_HINTS: Record<string, string> = {
  PROPERTY_OWNER: "You will be asked for proof of ownership.",
  EXISTING_TENANT: "You will be asked for your rental agreement.",
  AUTHORIZED_AGENT: "Needs ID, owner's authorisation and owner's confirmation.",
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
      "You own or live in a flat with space to fill, or you are an agent the owner has authorised.",
  },
  {
    type: "LOOKING_TO_RENT_TOGETHER",
    icon: Users,
    title: "I am looking to rent together",
    description:
      "You do not have a flat yet and want to find people to rent one with. This is a request, not a property.",
  },
];

function ExistingAccommodationFields({ form }: { form: Form }) {
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
      <SelectField
        label="Society"
        placeholder="Choose a society"
        options={LISTING_OPTIONS.society}
        hint="Never include a flat number or exact address."
        {...form.text("societyId")}
      />
      <div className="grid gap-x-4 gap-y-2 sm:grid-cols-2">
        <TextField
          label="Rent per person (₹ / month)"
          inputMode="numeric"
          {...form.text("rentPerPerson")}
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
        hint="This is shown on your listing either way."
        error={form.errors.brokerage}
      />
      {brokerageApplies && (
        <div className="grid gap-x-4 gap-y-2 sm:grid-cols-2">
          <TextField
            label="Brokerage amount (₹)"
            inputMode="numeric"
            {...form.text("brokerageAmount")}
          />
          <TextField
            label="Brokerage note (optional)"
            hint="For example: one-time, per flat."
            {...form.text("brokerageNote")}
          />
        </div>
      )}
      <div className="grid gap-x-4 gap-y-2 sm:grid-cols-2">
        <TextField
          label="Bedrooms in the flat"
          inputMode="numeric"
          {...form.text("bedroomCount")}
        />
        <TextField
          label="Rooms available"
          inputMode="numeric"
          {...form.text("availableSpaces")}
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
    </>
  );
}

function RentTogetherFields({ form }: { form: Form }) {
  return (
    <>
      <SampleSocietyPicker
        label="Societies you are hoping for"
        name="societyIds"
        societies={ALL_SOCIETIES}
        value={form.values.societyIds}
        onChange={(ids) => {
          form.setValue("societyIds", ids);
          form.markTouched("societyIds");
        }}
        hint="Most preferred first."
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
          {...form.text("additionalRoommatesNeeded")}
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

/**
 * Create a listing in three stages: choose the type, fill in the details,
 * then preview it exactly as others will see it before submitting.
 *
 * Phase 1 shell: nothing is saved. The listings API, photo uploads and the
 * admin review queue arrive in roadmap Phases 6 and 8.
 */
export function ListingForm({ poster }: { poster: ListingPoster }) {
  const [stage, setStage] = useState<Stage>("type");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const fieldsRef = useRef<HTMLDivElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const isFirstRender = useRef(true);

  const form = useForm<ListingFormValues>({
    initialValues: EMPTY_LISTING_VALUES,
    validate: validateListing,
    // Submitting is handled by the buttons below, not a form submit.
    onSubmit: async () => ({ ok: true }),
  });

  // Move focus to the heading whenever the stage changes.
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    headingRef.current?.focus();
  }, [stage]);

  const isExisting = form.values.listingType === "EXISTING_ACCOMMODATION";

  function chooseType(type: ListingType) {
    form.setValue("listingType", type);
    setStage("details");
  }

  function goToPreview() {
    const fields = LISTING_FIELDS[form.values.listingType] ?? [];
    if (form.validateFields(fields, fieldsRef.current)) {
      setStage("preview");
    }
  }

  async function submit() {
    setIsSubmitting(true);
    const result = await submitListing();
    setIsSubmitting(false);
    if (result.ok) {
      setStage("done");
    }
  }

  if (stage === "done") {
    return (
      <SuccessPanel
        title="Submitted for review"
        actions={
          <>
            <ButtonLink href="/accommodation/mine" size="lg" fullWidth>
              Go to my listings
            </ButtonLink>
            <ButtonLink
              href="/accommodation"
              variant="ghost"
              size="lg"
              fullWidth
            >
              Browse accommodation
            </ButtonLink>
          </>
        }
      >
        <p>
          In the finished app your post would now be{" "}
          <span className="text-foreground font-medium">pending review</span>{" "}
          and would appear publicly once approved. In this preview nothing was
          saved.
        </p>
      </SuccessPanel>
    );
  }

  const headings: Record<Exclude<Stage, "done">, string> = {
    type: "What are you posting?",
    details: isExisting ? "About the room" : "About your search",
    preview: "Check your post",
  };

  return (
    <div>
      <h2
        ref={headingRef}
        tabIndex={-1}
        className="mb-5 text-xl font-semibold outline-none"
      >
        {headings[stage]}
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
        <form
          {...form.formProps}
          onSubmit={(event) => {
            event.preventDefault();
            goToPreview();
          }}
        >
          <Card padding="lg">
            <div ref={fieldsRef} className="space-y-2">
              <TextField
                label="Title"
                hint={`A short summary, up to ${TITLE_MAX_LENGTH} characters.`}
                {...form.text("title")}
              />
              {isExisting ? (
                <ExistingAccommodationFields form={form} />
              ) : (
                <RentTogetherFields form={form} />
              )}
              <TextAreaField
                label="Description"
                hint={
                  isExisting
                    ? "What is the flat like, and who would suit it?"
                    : "Who are you, and what kind of flatmate are you looking for?"
                }
                maxLength={DESCRIPTION_MAX_LENGTH}
                {...form.text("description")}
              />
              {isExisting && (
                <Checkbox
                  name="confirmedAuthority"
                  checked={form.values.confirmedAuthority}
                  onChange={(event) =>
                    form.setValue("confirmedAuthority", event.target.checked)
                  }
                  error={form.errors.confirmedAuthority}
                >
                  I confirm that I own this property, or have the owner&apos;s
                  permission to list it.
                </Checkbox>
              )}
            </div>
          </Card>

          <div className="mt-6 flex items-center justify-between gap-3">
            <Button variant="ghost" onClick={() => setStage("type")}>
              <ArrowLeft aria-hidden="true" className="size-4" />
              Back
            </Button>
            <Button type={form.submitType}>Preview</Button>
          </div>
        </form>
      )}

      {stage === "preview" && (
        <div>
          <Alert tone="info" className="mb-5">
            This is how your post will look. New posts start as not verified and
            are reviewed before they appear publicly.
          </Alert>
          <div className="max-w-xl">
            <ListingCard listing={buildListingPreview(form.values, poster)} />
          </div>
          <div className="mt-6 flex items-center justify-between gap-3">
            <Button variant="ghost" onClick={() => setStage("details")}>
              <ArrowLeft aria-hidden="true" className="size-4" />
              Edit
            </Button>
            <Button onClick={submit} isLoading={isSubmitting}>
              Submit for review
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
