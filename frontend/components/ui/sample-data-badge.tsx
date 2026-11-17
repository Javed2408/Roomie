import { FlaskConical } from "lucide-react";

import { Badge } from "@/components/ui/badge";

/**
 * Must appear on every section that shows invented data from `lib/mock/`,
 * so nobody mistakes a placeholder for a real person, society or listing.
 */
export function SampleDataBadge({ className }: { className?: string }) {
  return (
    <Badge tone="warning" className={className}>
      <FlaskConical aria-hidden="true" className="size-3.5" />
      Sample data
    </Badge>
  );
}
