"use client";

import { Check, CircleX, Hand, PartyPopper } from "lucide-react";
import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button, ButtonLink } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { formatInr } from "@/lib/format";
import { describeApiError } from "@/services/api-client";
import { expressInterest, withdrawInterest } from "@/services/listings";
import {
  BROKERAGE_PAYABLE_TO_LABELS,
  type InterestStatus,
  type Listing,
} from "@/types/listing";

/**
 * Lets a student say they are interested in a listing, or take it back.
 *
 * Interest shares your public profile with the creator, nothing more.
 * When the listing charges brokerage, the amount must be acknowledged
 * first; the backend records exactly which amount was shown.
 */
export function InterestPanel({
  listing,
  status,
  onChange,
}: {
  listing: Listing;
  status: InterestStatus | null;
  onChange: (status: InterestStatus | null) => void;
}) {
  const [acknowledged, setAcknowledged] = useState(false);
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const poster = listing.postedBy.displayName;
  const brokerage =
    listing.type === "EXISTING_ACCOMMODATION" && listing.brokerage.applicable
      ? listing.brokerage
      : null;

  async function run(action: () => Promise<void>, next: InterestStatus | null) {
    setIsBusy(true);
    setError(null);
    try {
      await action();
      onChange(next);
      setAcknowledged(false);
    } catch (problem) {
      setError(describeApiError(problem));
    } finally {
      setIsBusy(false);
    }
  }

  const express = () =>
    run(() => expressInterest(listing.id, acknowledged), "PENDING");
  const withdraw = () => run(() => withdrawInterest(listing.id), "WITHDRAWN");

  let body;
  if (status === "PENDING") {
    body = (
      <>
        <p role="status" className="text-foreground flex items-start gap-2">
          <Check
            aria-hidden="true"
            className="text-success mt-0.5 size-5 shrink-0"
          />
          <span>
            Interest sent. {poster} can now see your profile and will reply
            here.
          </span>
        </p>
        <Button
          variant="secondary"
          fullWidth
          className="mt-4"
          onClick={withdraw}
          isLoading={isBusy}
        >
          Withdraw interest
        </Button>
      </>
    );
  } else if (status === "ACCEPTED") {
    body = (
      <p role="status" className="text-foreground flex items-start gap-2">
        <PartyPopper
          aria-hidden="true"
          className="text-success mt-0.5 size-5 shrink-0"
        />
        <span>
          {poster} accepted your interest. You will be able to message each
          other on Roomie once messaging opens; you will get a notification.
        </span>
      </p>
    );
  } else if (status === "DECLINED") {
    body = (
      <p role="status" className="text-muted flex items-start gap-2">
        <CircleX aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
        <span>{poster} decided this is not the right fit this time.</span>
      </p>
    );
  } else {
    body = (
      <>
        {brokerage && (
          <div className="bg-warning-soft mb-4 rounded-lg p-3">
            <Checkbox
              name="acknowledgeBrokerage"
              checked={acknowledged}
              onChange={(event) => setAcknowledged(event.target.checked)}
            >
              I understand a brokerage fee of{" "}
              <strong>{formatInr(brokerage.amount)}</strong> is payable to{" "}
              {BROKERAGE_PAYABLE_TO_LABELS[brokerage.payableTo]}, not to Roomie.
            </Checkbox>
          </div>
        )}
        <Button
          fullWidth
          onClick={express}
          isLoading={isBusy}
          disabled={brokerage !== null && !acknowledged}
        >
          <Hand aria-hidden="true" className="size-4" />
          {status === "WITHDRAWN"
            ? "Express interest again"
            : "I am interested"}
        </Button>
        <p className="text-muted mt-3 text-sm leading-relaxed">
          {poster} sees your profile only if you express interest. Nothing else,
          such as your email address, is shared.
        </p>
      </>
    );
  }

  return (
    <div>
      {body}
      {error && (
        <Alert tone="danger" role="alert" className="mt-3">
          {error}
          {/profile/i.test(error) && (
            <ButtonLink
              href="/onboarding"
              size="sm"
              variant="secondary"
              className="mt-2"
            >
              Finish your profile
            </ButtonLink>
          )}
        </Alert>
      )}
    </div>
  );
}
