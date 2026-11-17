/**
 * Lets keyboard and screen-reader users jump past the navigation straight
 * to the page content. Invisible until it receives focus with the Tab key.
 * The page's <main> element must have id="main".
 */
export function SkipLink() {
  return (
    <a
      href="#main"
      className="bg-surface text-foreground shadow-raised rounded-control sr-only z-50 px-4 py-3 text-sm font-medium focus:not-sr-only focus:fixed focus:top-3 focus:left-3"
    >
      Skip to content
    </a>
  );
}
