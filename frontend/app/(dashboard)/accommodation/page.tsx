import { Hand, List, Plus } from "lucide-react";
import type { Metadata } from "next";

import { PageHeader } from "@/components/app-shell/page-header";
import { ListingDirectory } from "@/components/listings/listing-directory";
import { ButtonLink } from "@/components/ui/button";

export const metadata: Metadata = { title: "Accommodation" };

export default function AccommodationPage() {
  return (
    <>
      <PageHeader
        title="Accommodation"
        description="Rooms with space to fill, and students looking to rent a place together. Every post here has been reviewed by Roomie."
      />
      <div className="mb-6 flex flex-wrap gap-3">
        <ButtonLink href="/accommodation/new">
          <Plus aria-hidden="true" className="size-4" />
          Post a listing
        </ButtonLink>
        <ButtonLink href="/accommodation/mine" variant="secondary">
          <List aria-hidden="true" className="size-4" />
          My listings
        </ButtonLink>
        <ButtonLink href="/accommodation/interests" variant="ghost">
          <Hand aria-hidden="true" className="size-4" />
          My interests
        </ButtonLink>
      </div>
      <ListingDirectory />
    </>
  );
}
