import type { Metadata } from "next";

import { PageHeader } from "@/components/app-shell/page-header";
import { ProfileOverview } from "@/components/profile/profile-overview";

export const metadata: Metadata = { title: "Profile" };

export default function ProfilePage() {
  return (
    <>
      <PageHeader
        title="Your profile"
        description="This is what other students see when you appear in Discover."
      />
      <ProfileOverview />
    </>
  );
}
