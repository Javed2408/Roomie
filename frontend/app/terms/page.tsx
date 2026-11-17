import type { Metadata } from "next";

import {
  LegalPage,
  type LegalSection,
} from "@/components/marketing/legal-page";

export const metadata: Metadata = { title: "Terms of Use" };

// DRAFT wording. See the note in components/marketing/legal-page.tsx.
const SECTIONS: LegalSection[] = [
  {
    heading: "Who Roomie is for",
    paragraphs: [
      "Roomie is for students looking for roommates or shared accommodation in the communities it covers. You must give accurate information about yourself when you create a profile.",
    ],
  },
  {
    heading: "What Roomie does and does not do",
    paragraphs: [
      "Roomie helps students find each other and compare what they are looking for. It is not a landlord, a broker or a party to any rental agreement, and it does not collect rent or deposits.",
      "A compatibility score is a guide to help you decide who to talk to. It is not a promise that two people will get along.",
      "Roomie cannot guarantee any person, listing or property. Always meet in person, see a place yourself and confirm the details before you pay anything.",
    ],
  },
  {
    heading: "Listings",
    paragraphs: [
      "A property may be listed only by its owner, by a current tenant who has permission, or by an agent whose authorisation the owner has confirmed. Unauthorised brokers are not allowed.",
      "Before a property listing is shown, its creator must prove their right to list it: proof of ownership for an owner, a valid rental agreement for a tenant, and for an agent the owner's written authorisation, which Roomie confirms with the owner directly.",
      "Any brokerage or similar charge must be stated on the listing upfront. Listings must not include a flat number or exact address.",
      "Nobody may ask for or collect rent, a deposit, brokerage or any other payment in Roomie's name. Roomie never handles payments.",
      "A post from students who are looking to rent together is a request for flatmates, not an offer of a property.",
    ],
  },
  {
    heading: "Verification",
    paragraphs: [
      "Where Roomie shows a verification label, the label names exactly what was checked, such as a person's identity, their student status or their authority to list a property. One label never implies another. A listing appearing on Roomie does not mean it has been verified.",
    ],
  },
  {
    heading: "How to behave",
    paragraphs: [
      "Treat other students with respect. Do not harass anyone, post false or misleading information, ask for money before a viewing, or use Roomie for anything unlawful.",
      "You can block another person or report a profile or listing at any time. Roomie may remove content or suspend accounts that break these terms.",
    ],
  },
];

export default function TermsPage() {
  return (
    <LegalPage
      title="Terms of Use"
      intro="The ground rules for using Roomie, in plain language."
      sections={SECTIONS}
    />
  );
}
