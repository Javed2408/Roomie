import { ArrowLeft } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

import { PageHeader } from "@/components/app-shell/page-header";
import { VerificationCenter } from "@/components/verification/verification-center";

export const metadata: Metadata = { title: "Verification" };

export default function VerificationPage() {
  return (
    <div className="mx-auto max-w-2xl">
      <Link
        href="/profile"
        className="text-muted hover:text-foreground mb-2 -ml-2 inline-flex h-10 items-center gap-1.5 rounded-lg px-2 text-sm font-medium transition-colors duration-150"
      >
        <ArrowLeft aria-hidden="true" className="size-4" />
        Your profile
      </Link>
      <PageHeader
        title="Verification"
        description="Optional checks that help other people trust your profile."
      />
      <VerificationCenter />
    </div>
  );
}
