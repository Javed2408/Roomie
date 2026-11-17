import { Plus } from "lucide-react";
import type { Metadata } from "next";

import { PageHeader } from "@/components/app-shell/page-header";
import { ListingDirectory } from "@/components/listings/listing-directory";
import { Alert } from "@/components/ui/alert";
import { ButtonLink } from "@/components/ui/button";
import { SampleDataBadge } from "@/components/ui/sample-data-badge";
import { LISTINGS } from "@/lib/mock/listings";

export const metadata: Metadata = { title: "Accommodation" };

export default function AccommodationPage() {
  return (
    <>
      <PageHeader
        title="Accommodation"
        description="Rooms with space to fill, and students looking to rent a place together."
        aside={<SampleDataBadge />}
      />
      <div className="mb-5 flex flex-wrap gap-3">
        <ButtonLink href="/accommodation/new">
          <Plus aria-hidden="true" className="size-4" />
          Post a listing
        </ButtonLink>
        <ButtonLink href="/accommodation/mine" variant="secondary">
          My listings
        </ButtonLink>
      </div>
      <Alert tone="info" className="mb-5">
        These posts are invented examples. No person, listing or property shown
        here has been verified.
      </Alert>
      <ListingDirectory listings={LISTINGS} />
    </>
  );
}
