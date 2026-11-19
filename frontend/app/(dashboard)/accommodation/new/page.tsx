import { ArrowLeft } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

import { PageHeader } from "@/components/app-shell/page-header";
import { ListingForm } from "@/components/listings/listing-form";

export const metadata: Metadata = { title: "Post a listing" };

export default function NewListingPage() {
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
        title="Post a listing"
        description="Offer a room, or find people to rent a place with. Every post is reviewed before students can see it."
      />
      <ListingForm />
    </div>
  );
}
