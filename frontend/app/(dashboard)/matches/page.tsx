import type { Metadata } from "next";

import { PageHeader } from "@/components/app-shell/page-header";
import { MatchesList } from "@/components/matches/matches-list";

export const metadata: Metadata = { title: "Matches" };

export default function MatchesPage() {
  return (
    <>
      <PageHeader
        title="Matches"
        description="People you liked who liked you back."
      />
      <MatchesList />
    </>
  );
}
