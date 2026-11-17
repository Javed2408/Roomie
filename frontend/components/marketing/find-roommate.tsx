import { ArrowRight, Check } from "lucide-react";

import { SectionHeading } from "@/components/marketing/section-heading";
import { ButtonLink } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Container } from "@/components/ui/container";

// The weights defined in the PRD (section 8.6). They add up to 100.
const FACTORS = [
  { label: "Budget", weight: 25 },
  { label: "Preferred societies", weight: 25 },
  { label: "Lifestyle", weight: 20 },
  { label: "Move-in date", weight: 15 },
  { label: "Room preference", weight: 10 },
  { label: "Food preference", weight: 5 },
];

const LARGEST_WEIGHT = Math.max(...FACTORS.map((factor) => factor.weight));

const POINTS = [
  "Only see students looking in the societies you chose.",
  "Every profile shows why you might be a good fit, and where you differ.",
  "A match happens only when you both say yes. Nobody sees who liked them otherwise.",
];

export function FindRoommate() {
  return (
    <section id="find-a-roommate" className="scroll-mt-16 py-16 sm:py-20">
      <Container className="grid items-center gap-12 lg:grid-cols-2 lg:gap-16">
        <div>
          <SectionHeading
            eyebrow="Find a roommate"
            title="Compatibility you can see the reasons for"
            description="Whether you already have a room to fill or are still looking, Roomie compares the things that actually cause friction between flatmates."
          />
          <ul className="mt-6 space-y-3">
            {POINTS.map((point) => (
              <li key={point} className="flex items-start gap-3">
                <Check
                  aria-hidden="true"
                  className="text-primary mt-1 size-5 shrink-0"
                />
                <span className="text-foreground leading-relaxed">{point}</span>
              </li>
            ))}
          </ul>
          <ButtonLink href="/register" className="mt-8">
            Find a roommate
            <ArrowRight aria-hidden="true" className="size-4" />
          </ButtonLink>
        </div>

        <Card padding="lg" elevated>
          <h3 className="text-lg font-semibold">What goes into the score</h3>
          <dl className="mt-5 space-y-4">
            {FACTORS.map((factor) => (
              <div key={factor.label}>
                <div className="flex items-baseline justify-between gap-3 text-sm">
                  <dt className="text-foreground font-medium">
                    {factor.label}
                  </dt>
                  <dd className="text-muted tabular-nums">{factor.weight}%</dd>
                </div>
                <div
                  aria-hidden="true"
                  className="bg-surface-muted mt-1.5 h-2 overflow-hidden rounded-full"
                >
                  <div
                    className="bg-primary h-full rounded-full"
                    style={{
                      width: `${(factor.weight / LARGEST_WEIGHT) * 100}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </dl>
          <p className="text-subtle mt-6 text-sm leading-relaxed">
            The score is a guide to help you decide who to talk to. It is not a
            guarantee that two people will get along.
          </p>
        </Card>
      </Container>
    </section>
  );
}
