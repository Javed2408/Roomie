import { CircleAlert, CircleCheck, Info, TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type AlertTone = "info" | "success" | "warning" | "danger";

const TONES: Record<AlertTone, { classes: string; Icon: typeof Info }> = {
  info: { classes: "bg-info-soft text-info", Icon: Info },
  success: { classes: "bg-success-soft text-success", Icon: CircleCheck },
  warning: { classes: "bg-warning-soft text-warning", Icon: TriangleAlert },
  danger: { classes: "bg-danger-soft text-danger", Icon: CircleAlert },
};

interface AlertProps {
  tone?: AlertTone;
  title?: string;
  children: ReactNode;
  /**
   * Set to "alert" for errors that appear after an action, so screen readers
   * announce them immediately. Leave unset for static notes.
   */
  role?: "alert" | "status";
  className?: string;
}

/** A coloured message box for notes, confirmations, warnings and errors. */
export function Alert({
  tone = "info",
  title,
  children,
  role,
  className,
}: AlertProps) {
  const { classes, Icon } = TONES[tone];

  return (
    <div
      role={role}
      className={cn(
        "rounded-control flex items-start gap-3 px-4 py-3 text-sm",
        classes,
        className,
      )}
    >
      <Icon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
      <div className="min-w-0 space-y-0.5 leading-relaxed">
        {title && <p className="font-semibold">{title}</p>}
        <div>{children}</div>
      </div>
    </div>
  );
}
