import { ArrowRight, Check, DoorOpen, Users } from "lucide-react";

import { SectionHeading } from "@/components/marketing/section-heading";
import { ButtonLink } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Container } from "@/components/ui/container";

const POINTS = [
  "Browse by society, so you only see places where you want to live.",
  "Rent, deposit and any brokerage are stated upfront on every listing.",
  "Exact addresses and flat numbers are never shown publicly.",
];

export function FindAccommodation() {
  return (
    <section
      id="find-accommodation"
      className="border-border bg-surface scroll-mt-16 border-y py-16 sm:py-20"
    >
      <Container className="grid items-center gap-12 lg:grid-cols-2 lg:gap-16">
        <div className="order-2 space-y-4 lg:order-1">
          <Card className="bg-background flex items-start gap-4">
            <span className="bg-primary-soft text-primary-strong flex size-11 shrink-0 items-center justify-center rounded-full">
              <DoorOpen aria-hidden="true" className="size-5" />
            </span>
            <div>
              <h3 className="text-lg font-semibold">Room available</h3>
              <p className="text-muted mt-1 text-[0.9375rem] leading-relaxed">
                Someone has a real room or flat with space to fill. You see the
                rent, the society and who is offering it.
              </p>
            </div>
          </Card>
          <Card className="bg-background flex items-start gap-4">
            <span className="bg-info-soft text-info flex size-11 shrink-0 items-center justify-center rounded-full">
              <Users aria-hidden="true" className="size-5" />
            </span>
            <div>
              <h3 className="text-lg font-semibold">
                Looking to rent together
              </h3>
              <p className="text-muted mt-1 text-[0.9375rem] leading-relaxed">
                Students teaming up before they rent. This is a request for
                flatmates, not an available property, and it is always labelled
                that way.
              </p>
            </div>
          </Card>
        </div>

        <div className="order-1 lg:order-2">
          <SectionHeading
            eyebrow="Find accommodation"
            title="Find a place, or the people to rent one with"
            description="Two kinds of posts live side by side, clearly labelled so you always know which one you are looking at."
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
            Find accommodation
            <ArrowRight aria-hidden="true" className="size-4" />
          </ButtonLink>
        </div>
      </Container>
    </section>
  );
}
