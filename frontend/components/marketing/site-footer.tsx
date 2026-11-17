import Link from "next/link";

import { Container } from "@/components/ui/container";
import { Logo } from "@/components/ui/logo";

const LINK_GROUPS = [
  {
    title: "Product",
    links: [
      { href: "/#how-it-works", label: "How it works" },
      { href: "/#find-a-roommate", label: "Find a roommate" },
      { href: "/#find-accommodation", label: "Find accommodation" },
      { href: "/#trust", label: "Trust and safety" },
    ],
  },
  {
    title: "Account",
    links: [
      { href: "/register", label: "Create an account" },
      { href: "/login", label: "Log in" },
    ],
  },
  {
    title: "Legal",
    links: [
      { href: "/terms", label: "Terms of Use" },
      { href: "/privacy", label: "Privacy Policy" },
      { href: "/status", label: "System status" },
    ],
  },
];

export function SiteFooter() {
  return (
    <footer className="border-border border-t py-12">
      <Container className="grid gap-10 md:grid-cols-[1.5fr_2fr]">
        <div>
          <Logo />
          <p className="text-muted mt-4 max-w-xs text-sm leading-relaxed">
            Find compatible people first, then make it easier to find a place
            together.
          </p>
        </div>

        <nav
          aria-label="Footer"
          className="grid grid-cols-2 gap-8 sm:grid-cols-3"
        >
          {LINK_GROUPS.map((group) => (
            <div key={group.title}>
              <h2 className="text-foreground font-sans text-sm font-semibold">
                {group.title}
              </h2>
              <ul className="mt-3 space-y-1">
                {group.links.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="text-muted hover:text-foreground inline-block py-1.5 text-sm transition-colors duration-150"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>
      </Container>

      <Container className="mt-10">
        <p className="border-border text-subtle border-t pt-6 text-sm leading-relaxed">
          Roomie is in development. Profiles, societies and listings shown on
          this site are sample data, and nothing shown has been verified.
        </p>
      </Container>
    </footer>
  );
}
