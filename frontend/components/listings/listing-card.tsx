import { DoorOpen, MapPin, Receipt, Users } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { VerificationStatus } from "@/components/verification/verification-status";
import { formatDate, formatInr } from "@/lib/format";
import {
  CREATOR_TYPE_LABELS,
  FURNISHING_LABELS,
  type BrokerageDisclosure,
  type ExistingAccommodationListing,
  type Listing,
  type RentTogetherListing,
} from "@/types/listing";

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-subtle text-xs">{label}</dt>
      <dd className="text-foreground text-sm font-medium">{children}</dd>
    </div>
  );
}

/** Brokerage is always stated, including when there is none. */
function BrokerageLine({ brokerage }: { brokerage: BrokerageDisclosure }) {
  return (
    <p className="text-foreground flex items-start gap-2 text-sm">
      <Receipt
        aria-hidden="true"
        className="text-subtle mt-0.5 size-4 shrink-0"
      />
      {brokerage.applicable ? (
        <span>
          <span className="font-medium">
            Brokerage: {formatInr(brokerage.amount)}
          </span>
          {brokerage.note && (
            <span className="text-muted"> · {brokerage.note}</span>
          )}
        </span>
      ) : (
        <span className="font-medium">No brokerage</span>
      )}
    </p>
  );
}

function ExistingAccommodationDetails({
  listing,
}: {
  listing: ExistingAccommodationListing;
}) {
  return (
    <>
      <p className="text-muted flex items-center gap-1.5 text-sm">
        <MapPin aria-hidden="true" className="size-4 shrink-0" />
        {listing.society.name}, {listing.society.locality.name}
      </p>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-3">
        <Fact label="Rent per person">
          {formatInr(listing.rentPerPerson)} / month
        </Fact>
        <Fact label="Deposit">
          {listing.deposit === null ? "Not stated" : formatInr(listing.deposit)}
        </Fact>
        <Fact label="Available from">{formatDate(listing.availableFrom)}</Fact>
        <Fact label="Space">
          {listing.availableSpaces} of {listing.bedroomCount} rooms
        </Fact>
        <Fact label="Furnishing">{FURNISHING_LABELS[listing.furnishing]}</Fact>
      </dl>
      <BrokerageLine brokerage={listing.brokerage} />
    </>
  );
}

function RentTogetherDetails({ listing }: { listing: RentTogetherListing }) {
  return (
    <>
      <p className="text-muted flex items-start gap-1.5 text-sm">
        <MapPin aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
        <span>
          Hoping for{" "}
          {listing.preferredSocieties
            .map((society) => society.name)
            .join(" or ")}
        </span>
      </p>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-3">
        <Fact label="Budget per person">
          {formatInr(listing.budgetPerPerson)} / month
        </Fact>
        <Fact label="Move-in">{formatDate(listing.moveInDate)}</Fact>
        <Fact label="Group so far">
          {listing.currentGroupSize}{" "}
          {listing.currentGroupSize === 1 ? "person" : "people"}
        </Fact>
        <Fact label="Still needed">
          {listing.additionalRoommatesNeeded} more
        </Fact>
        <Fact label="Looking for">{listing.desiredBedrooms}BHK</Fact>
      </dl>
    </>
  );
}

/**
 * One accommodation post. The two listing types get clearly different
 * labels so a search request is never mistaken for an available property.
 */
export function ListingCard({
  listing,
  href,
}: {
  listing: Listing;
  /** When given, the title links to this address (the detail page). */
  href?: string;
}) {
  const isExisting = listing.type === "EXISTING_ACCOMMODATION";

  return (
    <Card padding="none" className="flex h-full flex-col">
      <div className="flex-1 space-y-4 p-5">
        <div className="space-y-2.5">
          {isExisting ? (
            <Badge tone="primary">
              <DoorOpen aria-hidden="true" className="size-3.5" />
              Room available
            </Badge>
          ) : (
            <Badge tone="info">
              <Users aria-hidden="true" className="size-3.5" />
              Looking to rent together
            </Badge>
          )}
          <h3 className="text-lg font-semibold">
            {href ? (
              <Link
                href={href}
                className="hover:text-primary underline-offset-4 hover:underline"
              >
                {listing.title}
              </Link>
            ) : (
              listing.title
            )}
          </h3>
        </div>

        {isExisting ? (
          <ExistingAccommodationDetails listing={listing} />
        ) : (
          <RentTogetherDetails listing={listing} />
        )}

        <p className="text-muted text-sm leading-relaxed">
          {listing.description}
        </p>

        {!isExisting && (
          <p className="text-subtle text-xs leading-relaxed">
            This is a request from students who want to rent together. It is not
            an available property.
          </p>
        )}
      </div>

      <div className="border-border space-y-2 border-t px-5 py-4">
        <p className="text-foreground text-sm">
          Posted by{" "}
          <span className="font-medium">{listing.postedBy.displayName}</span>
          {isExisting && (
            <span className="text-muted">
              {" "}
              · {CREATOR_TYPE_LABELS[listing.creatorType]}
            </span>
          )}
        </p>
        <div className="flex flex-col gap-1">
          <VerificationStatus
            kind="IDENTITY"
            state={listing.postedBy.identityVerification}
          />
          {isExisting && (
            <VerificationStatus
              kind="LISTING_AUTHORITY"
              state={listing.listingAuthority}
            />
          )}
        </div>
      </div>
    </Card>
  );
}
