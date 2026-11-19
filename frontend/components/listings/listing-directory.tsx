"use client";

import { Building2, Search, SlidersHorizontal } from "lucide-react";
import { useEffect, useState } from "react";

import { ListingCard } from "@/components/listings/listing-card";
import { Button } from "@/components/ui/button";
import { SelectField } from "@/components/ui/select-field";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/states";
import { TextField } from "@/components/ui/text-field";
import { useDebouncedValue, useLocalities } from "@/hooks/use-directory";
import { cn } from "@/lib/cn";
import { parseWholeNumber } from "@/lib/profile-form";
import { describeApiError } from "@/services/api-client";
import {
  LISTING_PAGE_SIZE,
  browseListings,
  type ListingSearch,
  type ListingSort,
} from "@/services/listings";
import type { ListingPage, ListingType } from "@/types/listing";

type TypeFilter = "ALL" | ListingType;

const TYPE_FILTERS: Array<{ value: TypeFilter; label: string }> = [
  { value: "ALL", label: "All" },
  { value: "EXISTING_ACCOMMODATION", label: "Rooms available" },
  { value: "LOOKING_TO_RENT_TOGETHER", label: "Looking to rent together" },
];

const SORTS: Array<{ value: ListingSort; label: string }> = [
  { value: "newest", label: "Newest first" },
  { value: "rent_low", label: "Lowest rent first" },
  { value: "available_soon", label: "Available soonest" },
];

type Result =
  | { key: string; status: "ready"; page: ListingPage }
  | { key: string; status: "error"; message: string };

function CardSkeleton() {
  return (
    <div className="rounded-card border-border overflow-hidden border">
      <Skeleton className="aspect-[16/10] rounded-none" />
      <div className="space-y-3 p-5">
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-6 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
        <Skeleton className="h-16 w-full" />
      </div>
    </div>
  );
}

/**
 * Approved, active listings with filters and pages. Which listings appear
 * is decided entirely by the backend; this only asks for a slice of them.
 */
export function ListingDirectory() {
  const [type, setType] = useState<TypeFilter>("ALL");
  const [query, setQuery] = useState("");
  const [localityId, setLocalityId] = useState("");
  const [minRent, setMinRent] = useState("");
  const [maxRent, setMaxRent] = useState("");
  const [availableBy, setAvailableBy] = useState("");
  const [sort, setSort] = useState<ListingSort>("newest");
  const [offset, setOffset] = useState(0);
  const [attempt, setAttempt] = useState(0);
  const [showFilters, setShowFilters] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const localities = useLocalities();

  const settledQuery = useDebouncedValue(query, 300);
  const settledMin = useDebouncedValue(minRent, 400);
  const settledMax = useDebouncedValue(maxRent, 400);

  const search: ListingSearch = {
    type: type === "ALL" ? null : type,
    query: settledQuery,
    localityId: localityId || null,
    minRent: parseWholeNumber(settledMin),
    maxRent: parseWholeNumber(settledMax),
    availableBy: availableBy || null,
    sort,
    offset,
  };
  const key = JSON.stringify({ ...search, attempt });

  useEffect(() => {
    const controller = new AbortController();
    browseListings(search, controller.signal)
      .then((page) => setResult({ key, status: "ready", page }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setResult({
            key,
            status: "error",
            message: describeApiError(error),
          });
        }
      });
    return () => controller.abort();
    // `key` is built from every value `search` uses.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  // Any filter change starts again from the first page.
  function filterChanged<T>(set: (value: T) => void) {
    return (value: T) => {
      set(value);
      setOffset(0);
    };
  }

  const isFiltered =
    type !== "ALL" ||
    query.trim() !== "" ||
    localityId !== "" ||
    minRent !== "" ||
    maxRent !== "" ||
    availableBy !== "";

  function clearFilters() {
    setType("ALL");
    setQuery("");
    setLocalityId("");
    setMinRent("");
    setMaxRent("");
    setAvailableBy("");
    setOffset(0);
  }

  const current = result?.key === key ? result : null;
  const localityOptions =
    localities.status === "ready"
      ? localities.localities.map((locality) => ({
          value: locality.id,
          label: locality.name,
        }))
      : [];

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="flex-1">
          <TextField
            label="Search"
            type="search"
            placeholder="Title, society or area"
            value={query}
            onChange={(event) => filterChanged(setQuery)(event.target.value)}
            trailing={
              <Search aria-hidden="true" className="text-subtle size-4" />
            }
          />
        </div>
        <div className="sm:w-52">
          <SelectField
            label="Sort"
            options={SORTS}
            value={sort}
            onChange={(event) =>
              filterChanged(setSort)(event.target.value as ListingSort)
            }
          />
        </div>
      </div>

      <div
        role="group"
        aria-label="Filter listings by type"
        className="-mx-5 flex gap-2 overflow-x-auto px-5 pb-1 sm:mx-0 sm:px-0"
      >
        {TYPE_FILTERS.map((option) => {
          const isSelected = option.value === type;
          return (
            <button
              key={option.value}
              type="button"
              aria-pressed={isSelected}
              onClick={() => filterChanged(setType)(option.value)}
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
        <Button
          variant="secondary"
          size="sm"
          aria-expanded={showFilters}
          aria-controls="listing-filters"
          onClick={() => setShowFilters((value) => !value)}
          className="shrink-0 rounded-full"
        >
          <SlidersHorizontal aria-hidden="true" className="size-4" />
          More filters
        </Button>
        {isFiltered && (
          <Button variant="ghost" size="sm" onClick={clearFilters}>
            Clear filters
          </Button>
        )}
      </div>

      <div
        id="listing-filters"
        hidden={!showFilters}
        className="rounded-card border-border bg-surface grid gap-x-4 border p-4 sm:grid-cols-2 lg:grid-cols-4"
      >
        <SelectField
          label="Area"
          placeholder="Any area"
          options={localityOptions}
          value={localityId}
          onChange={(event) => filterChanged(setLocalityId)(event.target.value)}
        />
        <TextField
          label="Min rent (₹)"
          inputMode="numeric"
          value={minRent}
          onChange={(event) => filterChanged(setMinRent)(event.target.value)}
        />
        <TextField
          label="Max rent (₹)"
          inputMode="numeric"
          value={maxRent}
          onChange={(event) => filterChanged(setMaxRent)(event.target.value)}
        />
        <TextField
          label="Available by"
          type="date"
          value={availableBy}
          onChange={(event) =>
            filterChanged(setAvailableBy)(event.target.value)
          }
        />
      </div>

      {current === null ? (
        <ul className="grid gap-5 md:grid-cols-2 xl:grid-cols-3" aria-busy>
          {Array.from({ length: 6 }, (_, index) => (
            <li key={index}>
              <CardSkeleton />
            </li>
          ))}
          <li className="sr-only" role="status">
            Loading listings…
          </li>
        </ul>
      ) : current.status === "error" ? (
        <ErrorState
          title="Listings could not load"
          description={current.message}
          onRetry={() => setAttempt((value) => value + 1)}
        />
      ) : current.page.listings.length === 0 ? (
        <EmptyState
          icon={Building2}
          title={isFiltered ? "No listings match" : "No listings yet"}
          description={
            isFiltered
              ? "Try a wider rent range, another area or a different type."
              : "Approved listings appear here. Post a room, or say you are looking to rent together."
          }
          action={
            isFiltered ? (
              <Button variant="secondary" onClick={clearFilters}>
                Clear filters
              </Button>
            ) : undefined
          }
        />
      ) : (
        <>
          <p role="status" className="text-muted text-sm">
            Showing {current.page.offset + 1}–
            {current.page.offset + current.page.listings.length} of{" "}
            {current.page.total}
          </p>
          <ul className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {current.page.listings.map((listing) => (
              <li key={listing.id} className="animate-card-in">
                <ListingCard
                  listing={listing}
                  href={`/accommodation/${listing.id}`}
                />
              </li>
            ))}
          </ul>
          <nav
            aria-label="Pages"
            className="flex items-center justify-between gap-3"
          >
            <Button
              variant="secondary"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - LISTING_PAGE_SIZE))}
            >
              Previous
            </Button>
            <Button
              variant="secondary"
              disabled={offset + LISTING_PAGE_SIZE >= current.page.total}
              onClick={() => setOffset(offset + LISTING_PAGE_SIZE)}
            >
              Next
            </Button>
          </nav>
        </>
      )}
    </div>
  );
}
