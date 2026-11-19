import type { Metadata } from "next";
import { Suspense } from "react";

import { PageSkeleton } from "@/components/app-shell/page-skeleton";
import { ManageListing } from "@/components/listings/manage-listing";

export const metadata: Metadata = { title: "Manage listing" };

/** One of your own listings. The backend answers "not found" for others'. */
export default function ManageListingPage({
  params,
}: PageProps<"/accommodation/mine/[id]">) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      {params.then(({ id }) => (
        <ManageListing id={id} />
      ))}
    </Suspense>
  );
}
