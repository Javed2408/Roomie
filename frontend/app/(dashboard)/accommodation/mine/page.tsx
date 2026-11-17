import { ArrowLeft, Building2, Plus } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

import { PageHeader } from "@/components/app-shell/page-header";
import { MyListingRow } from "@/components/listings/my-listing-row";
import { ButtonLink } from "@/components/ui/button";
import { SampleDataBadge } from "@/components/ui/sample-data-badge";
import { EmptyState } from "@/components/ui/states";
import { MY_LISTINGS } from "@/lib/mock/listings";

export const metadata: Metadata = { title: "My listings" };

export default function MyListingsPage() {
  return (
    <div className="mx-auto max-w-2xl">
      <Link
        href="/accommodation"
        className="text-muted hover:text-foreground mb-2 -ml-2 inline-flex h-10 items-center gap-1.5 rounded-lg px-2 text-sm font-medium transition-colors duration-150"
      >
        <ArrowLeft aria-hidden="true" className="size-4" />
        All accommodation
      </Link>
      <PageHeader
        title="My listings"
        description="Posts you have created, and where each one is in review."
        aside={<SampleDataBadge />}
      />

      {MY_LISTINGS.length === 0 ? (
        <EmptyState
          icon={Building2}
          title="You have not posted anything yet"
          description="Post a room you have available, or tell others you are looking to rent together."
          action={
            <ButtonLink href="/accommodation/new">Post a listing</ButtonLink>
          }
        />
      ) : (
        <>
          <ul className="space-y-5">
            {MY_LISTINGS.map((listing) => (
              <li key={listing.id}>
                <MyListingRow listing={listing} />
              </li>
            ))}
          </ul>
          <ButtonLink href="/accommodation/new" className="mt-6">
            <Plus aria-hidden="true" className="size-4" />
            Post a listing
          </ButtonLink>
        </>
      )}
    </div>
  );
}
