import { ArrowLeft } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

import { PageHeader } from "@/components/app-shell/page-header";
import { MyListings } from "@/components/listings/my-listings";

export const metadata: Metadata = { title: "My listings" };

export default function MyListingsPage() {
  return (
    <div className="mx-auto max-w-3xl">
      <Link
        href="/accommodation"
        className="text-muted hover:text-foreground mb-2 -ml-2 inline-flex h-10 items-center gap-1.5 rounded-lg px-2 text-sm font-medium transition-colors duration-150"
      >
        <ArrowLeft aria-hidden="true" className="size-4" />
        All accommodation
      </Link>
      <PageHeader
        title="My listings"
        description="Posts you have created, where each one is in review, and who is interested."
      />
      <MyListings />
    </div>
  );
}
