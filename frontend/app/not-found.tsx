import { Compass } from "lucide-react";
import type { Metadata } from "next";

import { ButtonLink } from "@/components/ui/button";
import { Logo } from "@/components/ui/logo";

export const metadata: Metadata = { title: "Page not found" };

/** Shown for any address that does not match a page. */
export default function NotFound() {
  return (
    <main
      id="main"
      className="mx-auto flex w-full max-w-md flex-1 flex-col items-center justify-center px-5 py-16 text-center"
    >
      <Logo />
      <span className="bg-primary-soft text-primary-strong mt-10 flex size-14 items-center justify-center rounded-full">
        <Compass aria-hidden="true" className="size-7" />
      </span>
      <h1 className="mt-5 text-2xl font-semibold">
        We could not find that page
      </h1>
      <p className="text-muted mt-2 leading-relaxed">
        The link may be out of date, or the page may have moved.
      </p>
      <ButtonLink href="/" className="mt-8">
        Go to the home page
      </ButtonLink>
    </main>
  );
}
