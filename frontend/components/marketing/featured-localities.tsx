import { MapPin } from "lucide-react";

import { SectionHeading } from "@/components/marketing/section-heading";
import { Card } from "@/components/ui/card";
import { Container } from "@/components/ui/container";
import { SampleDataBadge } from "@/components/ui/sample-data-badge";
import { formatInrRange } from "@/lib/format";
import type { LocalitySummary } from "@/types/society";

export function FeaturedLocalities({
  localities,
}: {
  localities: LocalitySummary[];
}) {
  return (
    <section
      id="localities"
      className="border-border bg-surface scroll-mt-16 border-y py-16 sm:py-20"
    >
      <Container>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <SectionHeading
            eyebrow="Where students live"
            title="Start with where you want to live"
            description="Roomie launches around SRM Kattankulathur, organised by locality and society."
          />
          <SampleDataBadge className="self-start sm:self-auto" />
        </div>

        <ul className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {localities.map((locality) => (
            <li key={locality.id}>
              <Card className="bg-background h-full">
                <span className="bg-primary-soft text-primary-strong flex size-10 items-center justify-center rounded-full">
                  <MapPin aria-hidden="true" className="size-5" />
                </span>
                <h3 className="mt-4 text-lg font-semibold">{locality.name}</h3>
                <dl className="mt-3 space-y-2 text-sm">
                  <div>
                    <dt className="text-subtle text-xs">Societies</dt>
                    <dd className="text-foreground font-medium">
                      {locality.societyCount}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-subtle text-xs">
                      Rent per person / month
                    </dt>
                    <dd className="text-foreground font-medium">
                      {formatInrRange(locality.rentFrom, locality.rentTo)}
                    </dd>
                  </div>
                </dl>
              </Card>
            </li>
          ))}
        </ul>
        <p className="text-subtle mt-5 text-sm leading-relaxed">
          The numbers above are placeholders for development. The society
          directory is researched and curated before launch.
        </p>
      </Container>
    </section>
  );
}
