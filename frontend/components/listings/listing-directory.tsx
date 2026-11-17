"use client";

import { Building2 } from "lucide-react";
import { useState } from "react";

import { ListingCard } from "@/components/listings/listing-card";
import { EmptyState } from "@/components/ui/states";
import { cn } from "@/lib/cn";
import type { Listing, ListingType } from "@/types/listing";

type Filter = "ALL" | ListingType;

const FILTERS: Array<{ value: Filter; label: string }> = [
  { value: "ALL", label: "All" },
  { value: "EXISTING_ACCOMMODATION", label: "Rooms available" },
  { value: "LOOKING_TO_RENT_TOGETHER", label: "Looking to rent together" },
];

/**
 * The accommodation list with a filter for the two listing types.
 * Phase 1 shell: filters sample data in the browser. Search, society
 * filters and pagination come with the listings API in roadmap Phase 6.
 */
export function ListingDirectory({ listings }: { listings: Listing[] }) {
  const [filter, setFilter] = useState<Filter>("ALL");

  const visible =
    filter === "ALL"
      ? listings
      : listings.filter((listing) => listing.type === filter);

  return (
    <div className="space-y-5">
      <div
        role="group"
        aria-label="Filter listings by type"
        className="-mx-5 flex gap-2 overflow-x-auto px-5 pb-1 sm:mx-0 sm:px-0"
      >
        {FILTERS.map((option) => {
          const isSelected = option.value === filter;
          return (
            <button
              key={option.value}
              type="button"
              aria-pressed={isSelected}
              onClick={() => setFilter(option.value)}
              className={cn(
                "h-10 shrink-0 rounded-full border px-4 text-sm font-medium transition-colors duration-150",
                isSelected
                  ? "border-primary bg-primary text-on-primary"
                  : "border-border-strong/40 bg-surface text-foreground hover:bg-surface-muted",
              )}
            >
              {option.label}
            </button>
          );
        })}
      </div>

      {visible.length > 0 ? (
        <ul className="grid gap-5 md:grid-cols-2">
          {visible.map((listing) => (
            <li key={listing.id}>
              <ListingCard
                listing={listing}
                href={`/accommodation/${listing.id}`}
              />
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState
          icon={Building2}
          title="Nothing here yet"
          description="There are no listings of this type right now. Try a different filter."
        />
      )}
    </div>
  );
}
