import { Ban, EyeOff, Flag, ShieldCheck, type LucideIcon } from "lucide-react";

import { SectionHeading } from "@/components/marketing/section-heading";
import { Alert } from "@/components/ui/alert";
import { Card } from "@/components/ui/card";
import { Container } from "@/components/ui/container";

const COMMITMENTS: Array<{
  icon: LucideIcon;
  title: string;
  description: string;
}> = [
  {
    icon: ShieldCheck,
    title: "Verification that says what it means",
    description:
      "An identity check and a listing-authority check are separate labels. A label only ever covers the one thing that was actually checked.",
  },
  {
    icon: Ban,
    title: "No unauthorised brokers",
    description:
      "Properties may be listed by owners, current tenants with permission, or agents the owner has confirmed. Any brokerage must be disclosed upfront.",
  },
  {
    icon: EyeOff,
    title: "Private by default",
    description:
      "Exact addresses are never shown publicly. Verification documents are visible only to authorised administrators.",
  },
  {
    icon: Flag,
    title: "Block and report",
    description:
      "Block anyone to stop contact immediately, and report profiles or listings for review.",
  },
];

export function Trust() {
  return (
    <section id="trust" className="scroll-mt-16 py-16 sm:py-20">
      <Container>
        <SectionHeading
          eyebrow="Trust and safety"
          title="Built for trust, honest about its limits"
          description="Sharing a home is a big decision. Here is how Roomie is designed to help, and where your own judgement still matters."
        />
        <ul className="mt-10 grid gap-5 sm:grid-cols-2">
          {COMMITMENTS.map(({ icon: Icon, title, description }) => (
            <li key={title}>
              <Card className="h-full">
                <span className="bg-primary-soft text-primary-strong flex size-11 items-center justify-center rounded-full">
                  <Icon aria-hidden="true" className="size-5" />
                </span>
                <h3 className="mt-4 text-lg font-semibold">{title}</h3>
                <p className="text-muted mt-1.5 text-[0.9375rem] leading-relaxed">
                  {description}
                </p>
              </Card>
            </li>
          ))}
        </ul>
        <Alert
          tone="warning"
          title="What Roomie cannot promise"
          className="mt-6"
        >
          Roomie cannot guarantee any person, listing or property. Always meet
          in person, see the place yourself and confirm the details before you
          pay anything.
        </Alert>
      </Container>
    </section>
  );
}
