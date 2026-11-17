import type { ReactNode } from "react";

/** The title and one-line explanation at the top of each sign-in screen. */
export function AuthHeading({
  title,
  description,
}: {
  title: string;
  description: ReactNode;
}) {
  return (
    <div className="mb-8">
      <h1 className="text-2xl font-semibold sm:text-3xl">{title}</h1>
      <p className="text-muted mt-2 leading-relaxed">{description}</p>
    </div>
  );
}
