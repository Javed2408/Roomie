/**
 * Display formatting helpers.
 *
 * Dates are formatted by hand instead of with `Intl.DateTimeFormat`, because
 * the server and the browser can disagree on details such as "Sep" versus
 * "Sept", and React reports an error when the two renders differ.
 */

const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
] as const;

/** 12000 -> "₹12,000". Amounts are whole rupees (see DATABASE_SCHEMA.md). */
export function formatInr(amount: number): string {
  return `₹${amount.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

/** (8000, 12000) -> "₹8,000 – ₹12,000" */
export function formatInrRange(min: number, max: number): string {
  return `${formatInr(min)} – ${formatInr(max)}`;
}

/** "2027-01-05" -> "5 Jan 2027". Expects an ISO date (YYYY-MM-DD). */
export function formatDate(isoDate: string): string {
  const [year, month, day] = isoDate.split("-").map(Number);
  const monthName = month ? MONTHS[month - 1] : undefined;
  if (!year || !monthName || !day) {
    return isoDate;
  }
  return `${day} ${monthName} ${year}`;
}

/** "2026-11-10T18:42" -> "10 Nov, 6:42 pm" */
export function formatDateTime(localDateTime: string): string {
  const [datePart = "", timePart = ""] = localDateTime.split("T");
  const [, month, day] = datePart.split("-").map(Number);
  const [hours, minutes] = timePart.split(":").map(Number);
  const monthName = month ? MONTHS[month - 1] : undefined;
  if (!monthName || !day || hours === undefined || minutes === undefined) {
    return localDateTime;
  }
  const hour12 = hours % 12 === 0 ? 12 : hours % 12;
  const suffix = hours < 12 ? "am" : "pm";
  return `${day} ${monthName}, ${hour12}:${String(minutes).padStart(2, "0")} ${suffix}`;
}

/** A Date -> "2026-11-10T18:42", in the device's own time zone. */
export function toLocalDateTime(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/** "Ananya Rao" -> "AR". Used for avatars when there is no photo. */
export function getInitials(fullName: string): string {
  // Letters and digits only, so "Asha (practice)" gives "AP", not "A(".
  const words = fullName
    .trim()
    .split(/\s+/)
    .map((word) => word.replace(/[^\p{L}\p{N}]/gu, ""))
    .filter(Boolean);
  const first = words[0]?.[0] ?? "";
  const last = words.length > 1 ? (words[words.length - 1]?.[0] ?? "") : "";
  return `${first}${last}`.toUpperCase();
}

/** ["a"] -> "a", ["a", "b"] -> "a and b", ["a", "b", "c"] -> "a, b and c" */
export function joinWords(words: string[]): string {
  if (words.length <= 1) {
    return words.join("");
  }
  return `${words.slice(0, -1).join(", ")} and ${words.at(-1)}`;
}

/** "2026-11-17T14:03:00+00:00" -> "17 Nov 2026", in the device's time zone. */
export function formatTimestampDate(isoDateTime: string): string {
  const date = new Date(isoDateTime);
  if (Number.isNaN(date.getTime())) {
    return isoDateTime;
  }
  const pad = (value: number) => String(value).padStart(2, "0");
  return formatDate(
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`,
  );
}

/** 2 -> "2nd year" */
export function formatAcademicYear(year: number): string {
  const suffixes: Record<number, string> = { 1: "st", 2: "nd", 3: "rd" };
  return `${year}${suffixes[year] ?? "th"} year`;
}
