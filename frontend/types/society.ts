/** Mirrors the `localities` and `societies` tables in DATABASE_SCHEMA.md. */

export interface Locality {
  id: string;
  name: string;
  city: string;
}

export interface Society {
  id: string;
  name: string;
  locality: Locality;
}

/** What kind of place a society record is. `null` means not yet known. */
export type CommunityType = "APARTMENT_COMPLEX" | "VILLA_COMMUNITY";

export const COMMUNITY_TYPE_LABELS: Record<CommunityType, string> = {
  APARTMENT_COMPLEX: "Apartment complex",
  VILLA_COMMUNITY: "Villa community",
};

/** A society as the directory returns it (verified and active only). */
export interface DirectorySociety extends Society {
  communityType: CommunityType | null;
  description: string | null;
}

/** An area students can filter by, with how many societies it has. */
export interface DirectoryLocality extends Locality {
  description: string | null;
  societyCount: number;
}

/** A locality with summary numbers, as shown on the landing page. */
export interface LocalitySummary extends Locality {
  societyCount: number;
  /** Typical monthly rent per person, in whole rupees. */
  rentFrom: number;
  rentTo: number;
}
