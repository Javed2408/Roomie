import type { Metadata } from "next";

import { PageHeader } from "@/components/app-shell/page-header";
import { DiscoveryDeck } from "@/components/discovery/discovery-deck";

export const metadata: Metadata = { title: "Discover" };

export default function DiscoverPage() {
  return (
    <>
      <PageHeader
        title="Discover"
        description="Students looking for roommates. People who chose the same societies as you come first. Like the people you would consider living with."
      />
      <DiscoveryDeck />
    </>
  );
}
