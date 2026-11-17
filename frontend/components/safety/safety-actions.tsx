"use client";

import { Ban, Flag } from "lucide-react";
import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { TextAreaField } from "@/components/ui/textarea-field";
import { submitReport } from "@/services/mock-api";
import {
  REPORT_REASON_LABELS,
  type ReportReason,
  type SafetyTargetKind,
} from "@/types/safety";

const DETAILS_MAX_LENGTH = 1000;
const REASONS = Object.entries(REPORT_REASON_LABELS) as Array<
  [ReportReason, string]
>;

function ReportForm({
  targetName,
  onDone,
}: {
  targetName: string;
  onDone: () => void;
}) {
  const [reason, setReason] = useState<ReportReason | "">("");
  const [details, setDetails] = useState("");
  const [showErrors, setShowErrors] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isSent, setIsSent] = useState(false);

  const reasonError = reason ? undefined : "Choose a reason.";
  const detailsError =
    details.length > DETAILS_MAX_LENGTH
      ? `Use ${DETAILS_MAX_LENGTH} characters or fewer.`
      : undefined;

  async function send() {
    setShowErrors(true);
    if (reasonError || detailsError) {
      return;
    }
    setIsSending(true);
    const result = await submitReport();
    setIsSending(false);
    if (result.ok) {
      setIsSent(true);
    }
  }

  if (isSent) {
    return (
      <div className="space-y-4">
        <Alert tone="success" role="status" title="Thank you for telling us">
          In the finished app this report goes to Roomie&apos;s moderators for
          review. We cannot promise how quickly each report is looked at. In
          this preview nothing was sent.
        </Alert>
        <p className="text-muted text-sm leading-relaxed">
          If you are in immediate danger, contact local emergency services.
        </p>
        <Button fullWidth onClick={onDone}>
          Done
        </Button>
      </div>
    );
  }

  return (
    <form
      // "post" keeps what was typed out of the page address if the browser
      // ever sends this form itself, before the page is ready.
      method="post"
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        void send();
      }}
      className="space-y-4"
    >
      <p className="text-muted text-sm leading-relaxed">
        Tell us what is wrong with {targetName}. They will not be told who
        reported them.
      </p>

      <fieldset>
        <legend className="text-foreground mb-2 text-sm font-medium">
          Reason
        </legend>
        <div className="space-y-1">
          {REASONS.map(([value, label]) => (
            <label
              key={value}
              className="hover:bg-surface-muted flex cursor-pointer items-center gap-3 rounded-lg px-2 py-2.5 transition-colors duration-150"
            >
              <input
                type="radio"
                name="reason"
                value={value}
                checked={reason === value}
                onChange={() => setReason(value)}
                className="accent-primary size-5 shrink-0"
              />
              <span className="text-foreground text-sm">{label}</span>
            </label>
          ))}
        </div>
        <p className="text-danger mt-1 min-h-5 text-sm" role="alert">
          {showErrors ? reasonError : undefined}
        </p>
      </fieldset>

      <TextAreaField
        label="Details (optional)"
        name="details"
        rows={3}
        maxLength={DETAILS_MAX_LENGTH}
        value={details}
        onChange={(event) => setDetails(event.target.value)}
        error={detailsError}
      />

      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <Button variant="secondary" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" isLoading={isSending}>
          Send report
        </Button>
      </div>
    </form>
  );
}

interface SafetyActionsProps {
  /** Who or what the actions apply to, e.g. "Meera Iyer" or "this listing". */
  targetName: string;
  kind: SafetyTargetKind;
}

/**
 * The Report and Block buttons, with their dialogs.
 *
 * Phase 1 shell: a block is remembered only by this component and nothing
 * is sent. Real blocking (which removes two people from each other's
 * Discover and stops messages) and the moderation queue arrive in Phase 8.
 */
export function SafetyActions({ targetName, kind }: SafetyActionsProps) {
  const [openDialog, setOpenDialog] = useState<"report" | "block" | null>(null);
  const [isBlocked, setIsBlocked] = useState(false);
  const close = () => setOpenDialog(null);

  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setOpenDialog("report")}
        >
          <Flag aria-hidden="true" className="size-4" />
          Report
        </Button>
        {kind === "person" &&
          (isBlocked ? (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsBlocked(false)}
            >
              <Ban aria-hidden="true" className="size-4" />
              Unblock
            </Button>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setOpenDialog("block")}
            >
              <Ban aria-hidden="true" className="size-4" />
              Block
            </Button>
          ))}
      </div>
      {isBlocked && (
        <p role="status" className="text-muted mt-2 text-sm">
          You have blocked {targetName} (in this preview only).
        </p>
      )}

      <Dialog
        isOpen={openDialog === "report"}
        onClose={close}
        title={`Report ${targetName}`}
      >
        <ReportForm targetName={targetName} onDone={close} />
      </Dialog>

      <Dialog
        isOpen={openDialog === "block"}
        onClose={close}
        title={`Block ${targetName}?`}
      >
        <div className="space-y-5">
          <p className="text-muted text-sm leading-relaxed">
            You will no longer see each other in Discover, and neither of you
            will be able to message the other. They are not told that you
            blocked them. You can unblock them later.
          </p>
          <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <Button variant="secondary" onClick={close}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={() => {
                setIsBlocked(true);
                close();
              }}
            >
              Block
            </Button>
          </div>
        </div>
      </Dialog>
    </>
  );
}
