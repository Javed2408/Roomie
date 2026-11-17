import { PageSkeleton } from "@/components/app-shell/page-skeleton";

/** Shown automatically while a signed-in page is loading. */
export default function DashboardLoading() {
  return <PageSkeleton />;
}
