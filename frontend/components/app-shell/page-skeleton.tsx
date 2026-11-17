import { Skeleton } from "@/components/ui/states";

/**
 * Grey placeholder blocks shown while a signed-in page loads. They roughly
 * match a real page, so the layout does not jump when the content arrives.
 */
export function PageSkeleton() {
  return (
    <div role="status" aria-label="Loading page">
      <Skeleton className="h-8 w-56" />
      <Skeleton className="mt-3 h-5 w-80 max-w-full" />
      <div className="mt-8 grid gap-5 md:grid-cols-2">
        <Skeleton className="h-40" />
        <Skeleton className="h-40" />
        <Skeleton className="h-40" />
        <Skeleton className="h-40" />
      </div>
    </div>
  );
}
