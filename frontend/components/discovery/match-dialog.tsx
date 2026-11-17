"use client";

import { Heart } from "lucide-react";

import { Button, ButtonLink } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";

interface MatchDialogProps {
  /** The other person's full name, or null when the dialog is closed. */
  name: string | null;
  onClose: () => void;
  /** Text for the button that closes the dialog. */
  closeLabel?: string;
}

/** Shown straight after a like that turned out to be mutual. */
export function MatchDialog({
  name,
  onClose,
  closeLabel = "Keep discovering",
}: MatchDialogProps) {
  const firstName = name?.split(" ")[0] ?? "";
  return (
    <Dialog
      isOpen={name !== null}
      onClose={onClose}
      title={`You matched with ${firstName}`}
    >
      <div className="space-y-5">
        <div className="flex items-start gap-3">
          <span className="bg-accent-soft text-accent-strong flex size-11 shrink-0 items-center justify-center rounded-full">
            <Heart aria-hidden="true" className="size-5" />
          </span>
          <p className="text-muted text-sm leading-relaxed">
            You and {firstName} liked each other. You can both see the match in
            Matches. Messaging opens in a later update.
          </p>
        </div>
        <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button variant="secondary" onClick={onClose}>
            {closeLabel}
          </Button>
          <ButtonLink href="/matches">See your matches</ButtonLink>
        </div>
      </div>
    </Dialog>
  );
}
