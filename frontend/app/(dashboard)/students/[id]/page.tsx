import type { Metadata } from "next";
import { Suspense } from "react";

import { PageSkeleton } from "@/components/app-shell/page-skeleton";
import { StudentProfileView } from "@/components/discovery/student-profile-view";

export const metadata: Metadata = { title: "Student profile" };

/**
 * Another student's full profile, opened from Discover or from a match.
 *
 * The id comes from the page address, which is only known when someone
 * actually visits. Next.js asks for that to happen inside <Suspense>, so
 * the page frame appears at once while the id is read. The profile itself
 * is then loaded from the backend, which decides whether this person may
 * see it.
 */
export default function StudentProfilePage({
  params,
}: PageProps<"/students/[id]">) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      {params.then(({ id }) => (
        <StudentProfileView id={id} />
      ))}
    </Suspense>
  );
}
