import type { Metadata } from "next";
import { Suspense } from "react";

import { PageSkeleton } from "@/components/app-shell/page-skeleton";
import { ListingDetailView } from "@/components/listings/listing-detail-view";

export const metadata: Metadata = { title: "Listing" };

/**
 * One listing. The id comes from the page address, which is only known
 * when someone visits, so it is read inside <Suspense>. The backend then
 * decides whether this person may see the listing at all.
 */
export default function ListingDetailPage({
  params,
}: PageProps<"/accommodation/[id]">) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      {params.then(({ id }) => (
        <ListingDetailView id={id} />
      ))}
    </Suspense>
  );
}
