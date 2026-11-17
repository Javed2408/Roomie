import type { Metadata } from "next";

import {
  LegalPage,
  type LegalSection,
} from "@/components/marketing/legal-page";

export const metadata: Metadata = { title: "Privacy Policy" };

// DRAFT wording. See the note in components/marketing/legal-page.tsx.
const SECTIONS: LegalSection[] = [
  {
    heading: "What Roomie collects",
    paragraphs: [
      "Your email address and password, the profile details you choose to give (such as your name, college and course), and your accommodation and lifestyle preferences.",
      "Roomie asks only for information that is needed to help you find a roommate or a place to live. Optional fields are marked as optional.",
    ],
  },
  {
    heading: "What other students can see",
    paragraphs: [
      "Other students see your public profile: your name, college, course, budget range, preferred societies, move-in date and the lifestyle answers you gave.",
      "Your date of birth, contact details and exact address are never shown on your public profile. Your gender is shown only if you choose to show it.",
      "Roomie does not show other students who liked them unless both people like each other.",
    ],
  },
  {
    heading: "Addresses and locations",
    paragraphs: [
      "Listings show the society and locality only. Exact addresses and flat numbers are never shown publicly.",
    ],
  },
  {
    heading: "Verification documents",
    paragraphs: [
      "If you submit a document to verify your identity or your authority to list a property, it is stored privately and can be seen only by authorised Roomie administrators. It is never shown to other students.",
      "How long these documents are kept, and when they are deleted, will be set out here before verification is switched on.",
    ],
  },
  {
    heading: "Messages, reports and blocking",
    paragraphs: [
      "Messages can be read only by the two people in the conversation. If a conversation is reported, authorised moderators may review the reported content.",
      "When you block someone, they are not told. When you report someone, they are not told who made the report.",
    ],
  },
  {
    heading: "What Roomie does not do",
    paragraphs: [
      "Roomie does not guess personal characteristics from your photo or from what you write, and it does not sell your personal information.",
    ],
  },
];

export default function PrivacyPage() {
  return (
    <LegalPage
      title="Privacy Policy"
      intro="What Roomie knows about you, who can see it, and what stays private."
      sections={SECTIONS}
    />
  );
}
