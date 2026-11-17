/**
 * Join CSS class names, skipping anything falsy.
 *
 *   cn("px-4", isActive && "bg-primary", className)
 *
 * This lets components build their class list from conditions without
 * leaving stray "false" or "undefined" text in the HTML.
 */
export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}
