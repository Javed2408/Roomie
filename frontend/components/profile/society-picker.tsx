"use client";

import { ArrowDown, ArrowUp, Building2, MapPin, Search, X } from "lucide-react";
import { useId, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { FieldMessage } from "@/components/ui/field-message";
import { Spinner } from "@/components/ui/states";
import {
  useDebouncedValue,
  useLocalities,
  useSocietySearch,
} from "@/hooks/use-directory";
import { cn } from "@/lib/cn";
import { SEARCH_PAGE_SIZE } from "@/services/directory";
import { COMMUNITY_TYPE_LABELS, type Society } from "@/types/society";

interface SocietyPickerProps {
  label: string;
  /** The form field name, shared by every checkbox. */
  name: string;
  /** Selected society ids, most preferred first. */
  value: string[];
  onChange: (value: string[]) => void;
  /**
   * Societies already saved on the account, so their names show in the
   * "your order" list before any search has found them.
   */
  savedSocieties: Society[];
  /** The most that can be chosen. */
  max: number;
  hint?: string;
  error?: string;
}

const ICON_BUTTON =
  "text-primary-strong hover:bg-surface flex size-10 shrink-0 items-center justify-center rounded-lg transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-40";

/**
 * Search the society directory, choose several societies and put them in
 * order of preference.
 *
 * Only societies from the directory can be chosen. Nobody can type in their
 * own, because the directory is curated by administrators (PRD 8.4), and
 * the directory only contains societies an administrator has verified.
 */
export function SocietyPicker({
  label,
  name,
  value,
  onChange,
  savedSocieties,
  max,
  hint,
  error,
}: SocietyPickerProps) {
  const [query, setQuery] = useState("");
  const [localityId, setLocalityId] = useState<string | null>(null);
  const settledQuery = useDebouncedValue(query, 250);
  const localities = useLocalities();
  const { search, seen } = useSocietySearch(settledQuery, localityId);
  const searchId = useId();
  const searchRef = useRef<HTMLInputElement>(null);
  const messageId = `${searchId}-message`;

  const known = new Map<string, Society>(
    savedSocieties.map((society) => [society.id, society]),
  );
  for (const [id, society] of seen) {
    known.set(id, society);
  }
  const isFull = value.length >= max;
  const isFiltered = settledQuery.trim() !== "" || localityId !== null;
  const filterableLocalities =
    localities.status === "ready"
      ? localities.localities.filter((locality) => locality.societyCount > 0)
      : [];
  const chosenLocality = filterableLocalities.find(
    (locality) => locality.id === localityId,
  );

  function toggle(id: string) {
    onChange(
      value.includes(id) ? value.filter((item) => item !== id) : [...value, id],
    );
  }

  function move(index: number, direction: -1 | 1) {
    const target = index + direction;
    const moving = value[index];
    const displaced = value[target];
    if (moving === undefined || displaced === undefined) {
      return;
    }
    const next = [...value];
    next[index] = displaced;
    next[target] = moving;
    onChange(next);
  }

  return (
    <fieldset aria-describedby={error || hint ? messageId : undefined}>
      <legend className="text-foreground mb-2 text-sm font-medium">
        {label}
      </legend>

      {value.length > 0 && (
        <ol aria-label="Your order of preference" className="mb-4 space-y-2">
          {value.map((id, index) => {
            const society = known.get(id);
            const societyName = society?.name ?? "A chosen society";
            return (
              <li
                key={id}
                className="bg-primary-soft rounded-control flex items-center gap-2 py-1.5 pr-1.5 pl-3"
              >
                <span
                  aria-hidden="true"
                  className="font-display bg-surface text-primary-strong flex size-7 shrink-0 items-center justify-center rounded-full text-sm font-semibold"
                >
                  {index + 1}
                </span>
                <span className="min-w-0 flex-1 py-1">
                  <span className="text-primary-strong block text-sm font-medium">
                    {societyName}
                  </span>
                  {society && (
                    <span className="text-primary-strong/80 block text-xs">
                      {society.locality.name}
                    </span>
                  )}
                </span>
                <button
                  type="button"
                  onClick={() => move(index, -1)}
                  disabled={index === 0}
                  aria-label={`Move ${societyName} up`}
                  className={ICON_BUTTON}
                >
                  <ArrowUp aria-hidden="true" className="size-4" />
                </button>
                <button
                  type="button"
                  onClick={() => move(index, 1)}
                  disabled={index === value.length - 1}
                  aria-label={`Move ${societyName} down`}
                  className={ICON_BUTTON}
                >
                  <ArrowDown aria-hidden="true" className="size-4" />
                </button>
                <button
                  type="button"
                  onClick={() => toggle(id)}
                  aria-label={`Remove ${societyName}`}
                  className={ICON_BUTTON}
                >
                  <X aria-hidden="true" className="size-4" />
                </button>
              </li>
            );
          })}
        </ol>
      )}

      {filterableLocalities.length > 1 && (
        <div
          role="group"
          aria-label="Filter by area"
          className="mb-3 flex flex-wrap gap-2"
        >
          {[{ id: null, name: "All areas" }, ...filterableLocalities].map(
            (locality) => {
              const isSelected = locality.id === localityId;
              return (
                <button
                  key={locality.id ?? "all"}
                  type="button"
                  aria-pressed={isSelected}
                  onClick={() => setLocalityId(locality.id)}
                  className={cn(
                    "h-10 shrink-0 rounded-full border px-4 text-sm font-medium transition-colors duration-150",
                    isSelected
                      ? "border-primary bg-primary text-on-primary"
                      : "border-border-strong/40 bg-surface text-foreground hover:bg-surface-muted",
                  )}
                >
                  {locality.name}
                </button>
              );
            },
          )}
        </div>
      )}

      <div className="relative">
        <label htmlFor={searchId} className="sr-only">
          Search societies by name or area
        </label>
        <Search
          aria-hidden="true"
          className="text-subtle pointer-events-none absolute top-1/2 left-3.5 size-4 -translate-y-1/2"
        />
        <input
          ref={searchRef}
          id={searchId}
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search by name or area"
          autoComplete="off"
          className="rounded-control bg-surface text-foreground placeholder:text-subtle border-border-strong hover:border-foreground h-11 w-full border pr-11 pl-10 text-base transition-colors duration-150 [&::-webkit-search-cancel-button]:hidden"
        />
        {query !== "" && (
          // Our own clear button: the browser's built-in one cannot be
          // styled to match and is too small to tap easily.
          <button
            type="button"
            onClick={() => {
              setQuery("");
              searchRef.current?.focus();
            }}
            aria-label="Clear search"
            className="text-muted hover:text-foreground absolute top-1/2 right-0.5 flex size-10 -translate-y-1/2 items-center justify-center rounded-lg transition-colors duration-150"
          >
            <X aria-hidden="true" className="size-4" />
          </button>
        )}
      </div>

      <div
        className="border-border rounded-control mt-3 border"
        aria-live="polite"
        aria-busy={search.status === "loading"}
      >
        {search.status === "loading" && (
          <div className="px-3.5 py-4">
            <Spinner label="Searching" />
          </div>
        )}

        {search.status === "error" && (
          <div role="alert" className="space-y-3 px-3.5 py-4">
            <p className="text-danger text-sm">
              The societies could not be loaded. {search.message}
            </p>
            <Button variant="secondary" size="sm" onClick={search.retry}>
              Try again
            </Button>
          </div>
        )}

        {search.status === "ready" && search.societies.length === 0 && (
          <div className="flex items-start gap-3 px-3.5 py-4">
            <Building2
              aria-hidden="true"
              className="text-subtle mt-0.5 size-5 shrink-0"
            />
            {isFiltered ? (
              <p className="text-muted text-sm leading-relaxed">
                No societies match
                {settledQuery.trim() ? ` “${settledQuery.trim()}”` : ""}
                {chosenLocality ? ` in ${chosenLocality.name}` : ""}. Try a
                different spelling or another area. Only societies in
                Roomie&apos;s directory can be chosen.
              </p>
            ) : (
              <p className="text-muted text-sm leading-relaxed">
                No societies are in the directory yet. Roomie adds each one only
                after checking it, so please come back soon.
              </p>
            )}
          </div>
        )}

        {search.status === "ready" && search.societies.length > 0 && (
          <ul className="divide-border divide-y">
            {search.societies.map((society) => {
              const isChosen = value.includes(society.id);
              const isDisabled = !isChosen && isFull;
              return (
                <li key={society.id}>
                  <label
                    className={cn(
                      "flex items-center gap-3 px-3.5 py-3 transition-colors duration-150",
                      isDisabled
                        ? "cursor-not-allowed opacity-60"
                        : "hover:bg-surface-muted cursor-pointer",
                      isChosen && "bg-primary-soft/60",
                    )}
                  >
                    <input
                      type="checkbox"
                      name={name}
                      value={society.id}
                      checked={isChosen}
                      disabled={isDisabled}
                      onChange={() => toggle(society.id)}
                      className="accent-primary size-5 shrink-0 cursor-pointer disabled:cursor-not-allowed"
                    />
                    <span className="min-w-0">
                      <span className="text-foreground block text-sm font-medium">
                        {society.name}
                      </span>
                      <span className="text-subtle flex flex-wrap items-center gap-x-2 text-xs">
                        <span className="inline-flex items-center gap-1">
                          <MapPin aria-hidden="true" className="size-3" />
                          {society.locality.name}
                        </span>
                        {society.communityType && (
                          <span>
                            {COMMUNITY_TYPE_LABELS[society.communityType]}
                          </span>
                        )}
                      </span>
                    </span>
                  </label>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {search.status === "ready" &&
        search.societies.length >= SEARCH_PAGE_SIZE && (
          <p className="text-subtle mt-2 text-xs">
            Showing the first {SEARCH_PAGE_SIZE}. Search by name to narrow this
            down.
          </p>
        )}
      {isFull && (
        <p role="status" className="text-muted mt-2 text-sm">
          You have chosen {max}, the most allowed. Remove one to choose another.
        </p>
      )}
      <p className="text-subtle mt-2 text-xs leading-relaxed">
        Listing a society here does not mean Roomie works with it or represents
        it.
      </p>

      <FieldMessage id={messageId} hint={hint} error={error} />
    </fieldset>
  );
}
