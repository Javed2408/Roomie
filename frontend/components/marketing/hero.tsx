import { ArrowRight, MapPin } from "lucide-react";

import { ProfileCard } from "@/components/discovery/profile-card";
import { ButtonLink } from "@/components/ui/button";
import { Container } from "@/components/ui/container";
import { SampleDataBadge } from "@/components/ui/sample-data-badge";
import type { DiscoveryCandidate } from "@/types/profile";

export function Hero({ preview }: { preview: DiscoveryCandidate }) {
  return (
    <section className="pt-12 pb-16 sm:pt-16 sm:pb-20 lg:pt-20">
      <Container className="grid items-center gap-12 lg:grid-cols-[1.1fr_1fr] lg:gap-16">
        <div>
          <p className="text-primary-strong bg-primary-soft inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium">
            <MapPin aria-hidden="true" className="size-4" />
            For students around SRM Kattankulathur
          </p>
          <h1 className="mt-5 text-4xl leading-[1.1] font-semibold text-balance sm:text-5xl">
            Find people you can actually live with.
          </h1>
          <p className="text-muted mt-5 max-w-xl text-lg leading-relaxed text-pretty">
            Roomie helps students find compatible roommates by budget, society
            and lifestyle, then makes it easier to find a place together.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <ButtonLink href="/register" size="lg">
              Get started
              <ArrowRight aria-hidden="true" className="size-5" />
            </ButtonLink>
            <ButtonLink href="#how-it-works" variant="secondary" size="lg">
              See how it works
            </ButtonLink>
          </div>
          <p className="text-subtle mt-5 text-sm">
            Open to students from any college looking in the area.
          </p>
        </div>

        {/* A real product component, shown with sample data. */}
        <div className="mx-auto w-full max-w-sm lg:mx-0 lg:ml-auto">
          <div className="mb-3 flex items-center justify-between gap-3">
            <p className="text-muted text-sm font-medium">
              What a roommate profile looks like
            </p>
            <SampleDataBadge />
          </div>
          <ProfileCard candidate={preview} compact className="shadow-raised" />
        </div>
      </Container>
    </section>
  );
}
