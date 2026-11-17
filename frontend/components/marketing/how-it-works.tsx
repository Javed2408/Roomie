import { Container } from "@/components/ui/container";
import { SectionHeading } from "@/components/marketing/section-heading";

const STEPS = [
  {
    title: "Create your profile",
    description:
      "Share the basics: your college, course, budget and when you want to move in.",
  },
  {
    title: "Choose your societies",
    description:
      "Pick the residential communities you would like to live in, in order of preference.",
  },
  {
    title: "Discover and match",
    description:
      "See students whose preferences overlap with yours. When you both like each other, it is a match.",
  },
  {
    title: "Chat and plan",
    description:
      "Message your matches privately, compare notes and decide whether to share a place.",
  },
];

export function HowItWorks() {
  return (
    <section
      id="how-it-works"
      className="border-border bg-surface scroll-mt-16 border-y py-16 sm:py-20"
    >
      <Container>
        <SectionHeading
          eyebrow="How it works"
          title="People first, then the place"
          description="Most flat hunts start with a property and hope the people work out. Roomie starts with who you would live with."
        />
        <ol className="mt-10 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((step, index) => (
            <li key={step.title}>
              <span
                aria-hidden="true"
                className="font-display bg-primary-soft text-primary-strong flex size-10 items-center justify-center rounded-full text-base font-semibold"
              >
                {index + 1}
              </span>
              <h3 className="mt-4 text-lg font-semibold">{step.title}</h3>
              <p className="text-muted mt-1.5 text-[0.9375rem] leading-relaxed">
                {step.description}
              </p>
            </li>
          ))}
        </ol>
      </Container>
    </section>
  );
}
