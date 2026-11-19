import type { Metadata } from "next";
import { Suspense } from "react";

import { PageSkeleton } from "@/components/app-shell/page-skeleton";
import { EditListing } from "@/components/listings/edit-listing";

export const metadata: Metadata = { title: "Edit listing" };

export default function EditListingPage({
  params,
}: PageProps<"/accommodation/mine/[id]/edit">) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      {params.then(({ id }) => (
        <EditListing id={id} />
      ))}
    </Suspense>
  );
}
