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
  /** An access-checked photo address; without one, initials are shown. */
  src?: string | null;
  size?: AvatarSize;
  className?: string;
}

/**
 * Shows a person's photo, or their initials when they have none.
 *
 * Both are decorative (`aria-hidden`, empty alt): the person's name is
 * always shown as text next to the avatar, so reading both would be
 * repetitive. Photos come from the API, which checks on every request
 * that the viewer may see them, so a plain <img> with the session cookie
 * is used rather than an image optimiser that would fetch without it.
 */
export function Avatar({ name, src, size = "md", className }: AvatarProps) {
  if (src) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={src}
        alt=""
        aria-hidden="true"
        loading="lazy"
        className={cn(
          "bg-surface-muted shrink-0 rounded-full object-cover",
          SIZE_CLASSES[size],
          className,
        )}
      />
    );
  }
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
