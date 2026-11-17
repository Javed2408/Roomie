import { cn } from "@/lib/cn";
import { getInitials } from "@/lib/format";

type AvatarSize = "sm" | "md" | "lg" | "xl";

const SIZE_CLASSES: Record<AvatarSize, string> = {
  sm: "size-9 text-sm",
  md: "size-11 text-base",
  lg: "size-14 text-lg",
  xl: "size-20 text-2xl",
};

// Soft background + readable text pairs, all from the design tokens.
const COLOUR_CLASSES = [
  "bg-primary-soft text-primary-strong",
  "bg-accent-soft text-accent-strong",
  "bg-info-soft text-info",
  "bg-warning-soft text-warning",
  "bg-success-soft text-success",
] as const;

/** Pick a colour from the name, so the same person always gets the same one. */
function colourFor(name: string): string {
  let total = 0;
  for (const character of name) {
    total += character.codePointAt(0) ?? 0;
  }
  return COLOUR_CLASSES[total % COLOUR_CLASSES.length] ?? COLOUR_CLASSES[0];
}

interface AvatarProps {
  name: string;
  size?: AvatarSize;
  className?: string;
}

/**
 * Shows a person's initials. Photo support arrives with profile photo
 * uploads in roadmap Phase 6.
 *
 * The initials are decorative (`aria-hidden`): the person's name is always
 * shown as text next to the avatar, so reading both would be repetitive.
 */
export function Avatar({ name, size = "md", className }: AvatarProps) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "font-display inline-flex shrink-0 items-center justify-center rounded-full font-semibold select-none",
        SIZE_CLASSES[size],
        colourFor(name),
        className,
      )}
    >
      {getInitials(name)}
    </span>
  );
}
