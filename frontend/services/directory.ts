/**
 * The public society directory. It only ever contains societies that an
 * administrator has verified and that are switched on.
 */

import { apiGet } from "@/services/api-client";
import { parseDirectorySocieties, parseLocalities } from "@/services/parse";
import type { DirectoryLocality, DirectorySociety } from "@/types/society";

/** How many results one search returns. */
export const SEARCH_PAGE_SIZE = 50;

export async function fetchLocalities(
  signal?: AbortSignal,
): Promise<DirectoryLocality[]> {
  return parseLocalities(await apiGet("/localities", { signal }));
}

interface SocietySearch {
  /** Part of a society's or locality's name. */
  query?: string;
  /** Only societies in this locality. */
  localityId?: string | null;
  signal?: AbortSignal;
}

export async function searchSocieties({
  query,
  localityId,
  signal,
}: SocietySearch): Promise<DirectorySociety[]> {
  const params = new URLSearchParams({ limit: String(SEARCH_PAGE_SIZE) });
  if (query?.trim()) {
    params.set("q", query.trim());
  }
  if (localityId) {
    params.set("locality_id", localityId);
  }
  return parseDirectorySocieties(
    await apiGet(`/societies?${params.toString()}`, { signal }),
  );
}
