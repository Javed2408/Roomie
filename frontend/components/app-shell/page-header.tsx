import type { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  description?: string;
  /** Shown to the right of the title, e.g. a button or a label. */
  aside?: ReactNode;
}

/** The title block at the top of each signed-in page. */
export function PageHeader({ title, description, aside }: PageHeaderProps) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-x-4 gap-y-3 sm:mb-8">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold text-balance">{title}</h1>
        {description && (
          <p className="text-muted mt-1.5 max-w-2xl leading-relaxed text-pretty">
            {description}
          </p>
        )}
      </div>
      {aside && <div className="shrink-0">{aside}</div>}
    </div>
  );
}
