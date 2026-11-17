import Link from "next/link";

import { ButtonLink } from "@/components/ui/button";
import { Container } from "@/components/ui/container";
import { Logo } from "@/components/ui/logo";

const SECTION_LINKS = [
  { href: "/#how-it-works", label: "How it works" },
  { href: "/#find-a-roommate", label: "Find a roommate" },
  { href: "/#find-accommodation", label: "Find accommodation" },
  { href: "/#trust", label: "Trust" },
];

/** The top bar on public pages. Stays visible while scrolling. */
export function SiteHeader() {
  return (
    <header className="border-border bg-background/90 sticky top-0 z-30 border-b backdrop-blur">
      <Container className="flex h-16 items-center justify-between gap-4">
        <Logo />

        <nav aria-label="Page sections" className="hidden lg:block">
          <ul className="flex items-center gap-1">
            {SECTION_LINKS.map((link) => (
              <li key={link.href}>
                <Link
                  href={link.href}
                  className="text-muted hover:text-foreground hover:bg-surface-muted rounded-lg px-3 py-2 text-sm font-medium transition-colors duration-150"
                >
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div className="flex items-center gap-1.5">
          {/* Hidden on the very narrowest phones, where it would not fit. */}
          <ButtonLink
            href="/login"
            variant="ghost"
            size="sm"
            className="max-[359px]:hidden"
          >
            Log in
          </ButtonLink>
          <ButtonLink href="/register" size="sm">
            Get started
          </ButtonLink>
        </div>
      </Container>
    </header>
  );
}
