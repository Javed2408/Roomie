/**
 * SAMPLE DATA — for building and reviewing screens only.
 *
 * The four localities are the candidate areas named in the PRD. The society
 * names, counts and rents below are invented placeholders. They are not real
 * properties and nothing here has been checked or verified. The real
 * directory is curated by an administrator in roadmap Phase 4.
 *
 * Any screen that shows this data must display a "Sample data" label.
 */

import type { Locality, LocalitySummary, Society } from "@/types/society";

const CITY = "Chengalpattu district";

export const LOCALITIES = {
  potheri: { id: "loc-potheri", name: "Potheri", city: CITY },
  srmNagar: { id: "loc-srm-nagar", name: "SRM Nagar", city: CITY },
  kattankulathur: {
    id: "loc-kattankulathur",
    name: "Kattankulathur",
    city: CITY,
  },
  guduvanchery: { id: "loc-guduvanchery", name: "Guduvanchery", city: CITY },
} as const satisfies Record<string, Locality>;

export const SOCIETIES = {
  lakeside: {
    id: "soc-lakeside",
    name: "Lakeside Residency",
    locality: LOCALITIES.potheri,
  },
  greenfield: {
    id: "soc-greenfield",
    name: "Greenfield Towers",
    locality: LOCALITIES.potheri,
  },
  mapleCourt: {
    id: "soc-maple-court",
    name: "Maple Court",
    locality: LOCALITIES.srmNagar,
  },
  palmGrove: {
    id: "soc-palm-grove",
    name: "Palm Grove Apartments",
    locality: LOCALITIES.kattankulathur,
  },
  sunrise: {
    id: "soc-sunrise",
    name: "Sunrise Enclave",
    locality: LOCALITIES.guduvanchery,
  },
} as const satisfies Record<string, Society>;

export const FEATURED_LOCALITIES: LocalitySummary[] = [
  { ...LOCALITIES.potheri, societyCount: 6, rentFrom: 7000, rentTo: 14000 },
  { ...LOCALITIES.srmNagar, societyCount: 4, rentFrom: 6500, rentTo: 12000 },
  {
    ...LOCALITIES.kattankulathur,
    societyCount: 5,
    rentFrom: 6000,
    rentTo: 11000,
  },
  {
    ...LOCALITIES.guduvanchery,
    societyCount: 7,
    rentFrom: 5500,
    rentTo: 10000,
  },
];
