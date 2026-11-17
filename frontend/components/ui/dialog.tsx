"use client";

import { X } from "lucide-react";
import { useEffect, useId, useRef, type ReactNode } from "react";

interface DialogProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}

/**
 * A pop-up that sits above the page and must be dealt with first.
 *
 * Built on the browser's own <dialog> element, which provides the important
 * behaviour for free: focus moves into it and stays there, the page behind
 * cannot be clicked, and pressing Escape closes it.
 */
export function Dialog({ isOpen, onClose, title, children }: DialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) {
      return;
    }
    if (isOpen && !dialog.open) {
      dialog.showModal();
    } else if (!isOpen && dialog.open) {
      dialog.close();
    }
  }, [isOpen]);

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={titleId}
      // Fires when the dialog closes for any reason, including Escape.
      onClose={onClose}
      // A click on the dimmed area lands on the <dialog> element itself.
      onClick={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
      className="bg-surface text-foreground rounded-card shadow-raised m-auto w-[calc(100%-2.5rem)] max-w-md p-0 backdrop:bg-black/50"
    >
      {/* Rendered only while open, so each opening starts fresh. */}
      {isOpen && (
        <div className="p-5 sm:p-6">
          <div className="mb-4 flex items-start justify-between gap-4">
            <h2 id={titleId} className="text-xl font-semibold">
              {title}
            </h2>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              className="text-muted hover:bg-surface-muted hover:text-foreground -mt-1.5 -mr-2 flex size-10 shrink-0 items-center justify-center rounded-lg transition-colors duration-150"
            >
              <X aria-hidden="true" className="size-5" />
            </button>
          </div>
          {children}
        </div>
      )}
    </dialog>
  );
}
