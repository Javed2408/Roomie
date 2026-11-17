import type { Metadata } from "next";

import { PageHeader } from "@/components/app-shell/page-header";
import { ProfileEditor } from "@/components/profile/profile-editor";

export const metadata: Metadata = { title: "Edit profile" };

export default function EditProfilePage() {
  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader
        title="Edit your profile"
        description="Keep this up to date so your matches stay relevant."
      />
      <ProfileEditor />
    </div>
  );
}
