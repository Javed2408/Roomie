import { ArrowRight } from "lucide-react";

import { ButtonLink } from "@/components/ui/button";
import { Container } from "@/components/ui/container";

export function CallToAction() {
  return (
    <section className="py-16 sm:py-20">
      <Container>
        <div className="bg-band rounded-card px-6 py-12 text-center sm:px-12 sm:py-16">
          <h2 className="text-2xl font-semibold text-balance text-white sm:text-3xl">
            Ready to find your people?
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-base leading-relaxed text-pretty text-white/85 sm:text-lg">
            Create a profile, choose your societies and see who is looking for
            the same kind of home.
          </p>
          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <ButtonLink href="/register" variant="solid-on-dark" size="lg">
              Create your profile
              <ArrowRight aria-hidden="true" className="size-5" />
            </ButtonLink>
            <ButtonLink href="/login" variant="ghost-on-dark" size="lg">
              I already have an account
            </ButtonLink>
          </div>
        </div>
      </Container>
    </section>
  );
}
