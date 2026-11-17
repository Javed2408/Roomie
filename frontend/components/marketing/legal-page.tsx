import type { ReactNode } from "react";

import { SiteFooter } from "@/components/marketing/site-footer";
import { SiteHeader } from "@/components/marketing/site-header";
import { Alert } from "@/components/ui/alert";
import { Container } from "@/components/ui/container";
import { SkipLink } from "@/components/ui/skip-link";

export interface LegalSection {
  heading: string;
  /** Each string is one paragraph. */
  paragraphs: string[];
}

interface LegalPageProps {
  title: string;
  intro: ReactNode;
  sections: LegalSection[];
}

/**
 * Shared layout for the Terms of Use and Privacy Policy.
 *
 * IMPORTANT: the text on these pages is a plain-language DRAFT written
 * during development. It describes how Roomie is intended to work. It has
 * not been reviewed by a lawyer and must be before the product launches.
 */
export function LegalPage({ title, intro, sections }: LegalPageProps) {
  return (
    <>
      <SkipLink />
      <SiteHeader />
      <main id="main" className="flex-1 py-12 sm:py-16">
        <Container className="max-w-3xl">
          <h1 className="text-3xl font-semibold sm:text-4xl">{title}</h1>
          <p className="text-muted mt-4 text-lg leading-relaxed">{intro}</p>

          <Alert
            tone="warning"
            title="Draft, not yet in force"
            className="mt-6"
          >
            Roomie is still in development. This page is a working draft that
            has not had legal review, and it will change before launch.
          </Alert>

          <div className="mt-10 space-y-10">
            {sections.map((section) => (
              <section key={section.heading}>
                <h2 className="text-xl font-semibold">{section.heading}</h2>
                <div className="text-muted mt-3 space-y-3 leading-relaxed">
                  {section.paragraphs.map((paragraph) => (
                    <p key={paragraph}>{paragraph}</p>
                  ))}
                </div>
              </section>
            ))}
          </div>
        </Container>
      </main>
      <SiteFooter />
    </>
  );
}
