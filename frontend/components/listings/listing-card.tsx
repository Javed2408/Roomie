import { DoorOpen, ImageOff, MapPin, Receipt, Users } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { VerificationStatus } from "@/components/verification/verification-status";
import { cn } from "@/lib/cn";
import { formatDate, formatInr } from "@/lib/format";
import {
  BROKERAGE_PAYABLE_TO_LABELS,
  CREATOR_TYPE_LABELS,
  FACILITY_LABELS,
  FURNISHING_LABELS,
  type BrokerageDisclosure,
  type ExistingAccommodationListing,
  type Listing,
  type RentTogetherListing,
} from "@/types/listing";

export function Fact({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div>
      <dt className="text-subtle text-xs">{label}</dt>
      <dd className="text-foreground text-sm font-medium">{children}</dd>
    </div>
  );
}

/** "Room available" or "Looking to rent together", never confused. */
export function ListingTypeBadge({ listing }: { listing: Listing }) {
  return listing.type === "EXISTING_ACCOMMODATION" ? (
    <Badge tone="primary">
      <DoorOpen aria-hidden="true" className="size-3.5" />
      Room available
    </Badge>
  ) : (
    <Badge tone="info">
      <Users aria-hidden="true" className="size-3.5" />
      Looking to rent together
    </Badge>
  );
}

/** Brokerage is always stated, including when there is none. */
export function BrokerageLine({
  brokerage,
}: {
  brokerage: BrokerageDisclosure;
}) {
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
          <span className="text-muted">
            {" "}
            · paid to {BROKERAGE_PAYABLE_TO_LABELS[brokerage.payableTo]}
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

export function ListingLocation({ listing }: { listing: Listing }) {
  if (listing.type === "EXISTING_ACCOMMODATION") {
    return (
      <p className="text-muted flex items-center gap-1.5 text-sm">
        <MapPin aria-hidden="true" className="size-4 shrink-0" />
        {listing.society.name}, {listing.society.locality.name}
      </p>
    );
  }
  return (
    <p className="text-muted flex items-start gap-1.5 text-sm">
      <MapPin aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
      <span>
        Hoping for{" "}
        {listing.preferredSocieties.map((society) => society.name).join(" or ")}
      </span>
    </p>
  );
}

function PropertyFacts({ listing }: { listing: ExistingAccommodationListing }) {
  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-3">
      <Fact label="Rent per person">
        {formatInr(listing.rentPerPerson)} / month
      </Fact>
      <Fact label="Available from">{formatDate(listing.availableFrom)}</Fact>
      <Fact label="Rooms free">
        {listing.availableBedrooms} of {listing.bedroomCount}
      </Fact>
      <Fact label="Wanted">
        {listing.roommatesWanted}{" "}
        {listing.roommatesWanted === 1 ? "person" : "people"}
      </Fact>
    </dl>
  );
}

function RentTogetherFacts({ listing }: { listing: RentTogetherListing }) {
  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-3">
      <Fact label="Budget per person">
        {formatInr(listing.budgetPerPerson)} / month
      </Fact>
      <Fact label="Move-in">{formatDate(listing.moveInDate)}</Fact>
      <Fact label="Group so far">
        {listing.currentGroupSize}{" "}
        {listing.currentGroupSize === 1 ? "person" : "people"}
      </Fact>
      <Fact label="Still needed">{listing.roommatesWanted} more</Fact>
    </dl>
  );
}

/** Every detail of a listing, for its own page and the creator's preview. */
export function ListingFullDetails({ listing }: { listing: Listing }) {
  if (listing.type === "LOOKING_TO_RENT_TOGETHER") {
    return (
      <dl className="grid grid-cols-2 gap-x-4 gap-y-4 sm:grid-cols-3">
        <Fact label="Budget per person">
          {formatInr(listing.budgetPerPerson)} / month
        </Fact>
        <Fact label="Move-in">{formatDate(listing.moveInDate)}</Fact>
        <Fact label="Looking for">{listing.desiredBedrooms} bedrooms</Fact>
        <Fact label="Group so far">
          {listing.currentGroupSize}{" "}
          {listing.currentGroupSize === 1 ? "person" : "people"}
        </Fact>
        <Fact label="Still needed">{listing.roommatesWanted} more</Fact>
      </dl>
    );
  }
  return (
    <div className="space-y-4">
      <dl className="grid grid-cols-2 gap-x-4 gap-y-4 sm:grid-cols-3">
        <Fact label="Rent per person">
          {formatInr(listing.rentPerPerson)} / month
        </Fact>
        <Fact label="Whole flat">
          {listing.totalRent === null
            ? "Not stated"
            : `${formatInr(listing.totalRent)} / month`}
        </Fact>
        <Fact label="Deposit">
          {listing.deposit === null ? "Not stated" : formatInr(listing.deposit)}
        </Fact>
        <Fact label="Available from">{formatDate(listing.availableFrom)}</Fact>
        <Fact label="Bedrooms">
          {listing.availableBedrooms} free of {listing.bedroomCount}
        </Fact>
        <Fact label="Living there now">
          {listing.currentOccupants}{" "}
          {listing.currentOccupants === 1 ? "person" : "people"}
        </Fact>
        <Fact label="Wanted">
          {listing.roommatesWanted}{" "}
          {listing.roommatesWanted === 1 ? "person" : "people"}
        </Fact>
        <Fact label="Furnishing">
          {listing.furnishing
            ? FURNISHING_LABELS[listing.furnishing]
            : "Not stated"}
        </Fact>
      </dl>
      <BrokerageLine brokerage={listing.brokerage} />
      {listing.facilities.length > 0 && (
        <div>
          <h3 className="text-subtle text-xs">Facilities</h3>
          <ul className="mt-1.5 flex flex-wrap gap-1.5">
            {listing.facilities.map((facility) => (
              <li key={facility}>
                <Badge>{FACILITY_LABELS[facility]}</Badge>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

/** Who posted it and which checks have actually been passed. */
export function PosterLine({ listing }: { listing: Listing }) {
  const isExisting = listing.type === "EXISTING_ACCOMMODATION";
  return (
    <div className="space-y-2">
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
        {isExisting ? (
          <VerificationStatus
            kind="LISTING_AUTHORITY"
            state={listing.listingAuthority}
          />
        ) : (
          listing.postedBy.studentVerification && (
            <VerificationStatus
              kind="STUDENT"
              state={listing.postedBy.studentVerification}
            />
          )
        )}
      </div>
    </div>
  );
}

function Cover({ listing }: { listing: Listing }) {
  const photo = listing.photos[0];
  return (
    <div className="bg-surface-muted rounded-t-card relative aspect-[16/10] overflow-hidden">
      {photo ? (
        // Photos come from the API with an access check on every request,
        // so a plain <img> sends the session cookie with it.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={photo.url}
          alt=""
          loading="lazy"
          className="size-full object-cover"
        />
      ) : (
        <div className="text-subtle flex size-full flex-col items-center justify-center gap-1.5">
          {listing.type === "EXISTING_ACCOMMODATION" ? (
            <ImageOff aria-hidden="true" className="size-7" />
          ) : (
            <Users aria-hidden="true" className="size-7" />
          )}
          <span className="text-xs">
            {listing.type === "EXISTING_ACCOMMODATION"
              ? "No photos yet"
              : "No property yet"}
          </span>
        </div>
      )}
      {listing.photos.length > 1 && (
        <span className="absolute right-2 bottom-2 rounded-full bg-black/60 px-2 py-0.5 text-xs text-white">
          {listing.photos.length} photos
        </span>
      )}
    </div>
  );
}

/**
 * One accommodation post. The two listing types get clearly different
 * labels so a search request is never mistaken for an available property.
 */
export function ListingCard({
  listing,
  href,
  className,
}: {
  listing: Listing;
  /** When given, the title links to this address (the detail page). */
  href?: string;
  className?: string;
}) {
  const isExisting = listing.type === "EXISTING_ACCOMMODATION";

  return (
    <Card
      padding="none"
      className={cn(
        "group relative flex h-full flex-col transition-shadow duration-150 hover:shadow-md",
        className,
      )}
    >
      <Cover listing={listing} />
      <div className="flex-1 space-y-3.5 p-5">
        <div className="space-y-2">
          <ListingTypeBadge listing={listing} />
          <h3 className="text-lg leading-snug font-semibold">
            {href ? (
              // The link covers the whole card, so the card is one target.
              <Link
                href={href}
                className="group-hover:text-primary after:rounded-card focus-visible:after:ring-primary after:absolute after:inset-0 focus-visible:outline-none focus-visible:after:ring-2"
              >
                {listing.title}
              </Link>
            ) : (
              listing.title
            )}
          </h3>
          <ListingLocation listing={listing} />
        </div>

        {isExisting ? (
          <PropertyFacts listing={listing} />
        ) : (
          <RentTogetherFacts listing={listing} />
        )}
        {isExisting && <BrokerageLine brokerage={listing.brokerage} />}

        {!isExisting && (
          <p className="text-subtle text-xs leading-relaxed">
            A request from students who want to rent together. It is not an
            available property.
          </p>
        )}
      </div>

      <div className="border-border border-t px-5 py-4">
        <PosterLine listing={listing} />
      </div>
    </Card>
  );
}
