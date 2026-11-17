"use client";

import { Check, Hand } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";

/**
 * Lets a student say they are interested in a listing.
 *
 * Phase 1 shell: the interest is remembered only by this component. In
 * roadmap Phase 6 it is saved, the poster is notified, and duplicates and
 * interest in your own listing are prevented by the backend.
 */
export function InterestButton({ posterName }: { posterName: string }) {
  const [hasInterest, setHasInterest] = useState(false);

  return (
    <div>
      {hasInterest ? (
        <Button
          variant="secondary"
          fullWidth
          onClick={() => setHasInterest(false)}
        >
          <Check aria-hidden="true" className="size-4" />
          Interest sent · Withdraw
        </Button>
      ) : (
        <Button fullWidth onClick={() => setHasInterest(true)}>
          <Hand aria-hidden="true" className="size-4" />I am interested
        </Button>
      )}
      <p role="status" className="text-muted mt-3 text-sm leading-relaxed">
        {hasInterest
          ? `In the finished app ${posterName} would now see your profile and could choose to start a conversation. Nothing was sent in this preview.`
          : `${posterName} sees your profile only if you express interest. You can chat once they accept.`}
      </p>
    </div>
  );
}
