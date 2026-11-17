"use client";

import { Activity, ChevronDown, LogOut, ShieldCheck, User } from "lucide-react";
import Link from "next/link";
import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";

import { useSession } from "@/components/session/session-provider";
import { Avatar } from "@/components/ui/avatar";
import { cn } from "@/lib/cn";

const ITEM_CLASSES =
  "text-foreground hover:bg-surface-muted flex h-11 w-full items-center gap-3 rounded-lg px-3 text-left text-sm font-medium transition-colors duration-150";

/**
 * The profile button in the header and the small menu it opens.
 * Closes when you press Escape, click elsewhere or choose an item.
 */
export function UserMenu() {
  const { account, signOut } = useSession();
  const [isOpen, setIsOpen] = useState(false);
  const [isSigningOut, setIsSigningOut] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelId = useId();

  // Until a profile exists, the email address stands in for the name.
  const displayName = account.profile?.fullName ?? account.user.email;
  const secondLine = account.profile?.collegeName ?? "Profile not set up yet";

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    function handlePointerDown(event: PointerEvent) {
      if (
        event.target instanceof Node &&
        !containerRef.current?.contains(event.target)
      ) {
        setIsOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
        // Return focus to the button so keyboard users keep their place.
        buttonRef.current?.focus();
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  // Close the menu when the page is navigated away from. Next.js keeps
  // hidden pages in memory, so without this the menu could still be open
  // when someone comes back with the browser's Back button.
  useLayoutEffect(() => {
    return () => setIsOpen(false);
  }, []);

  const close = () => setIsOpen(false);

  return (
    <div ref={containerRef} className="relative">
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setIsOpen((current) => !current)}
        aria-expanded={isOpen}
        aria-controls={panelId}
        aria-label={`Account menu for ${displayName}`}
        className="hover:bg-surface-muted flex h-11 max-w-56 items-center gap-2 rounded-full pr-2 pl-1 transition-colors duration-150"
      >
        <Avatar name={displayName} size="sm" />
        <span className="text-foreground hidden truncate text-sm font-medium sm:block">
          {displayName}
        </span>
        <ChevronDown
          aria-hidden="true"
          className={cn(
            "text-muted size-4 shrink-0 transition-transform duration-150",
            isOpen && "rotate-180",
          )}
        />
      </button>

      {isOpen && (
        <div
          id={panelId}
          className="border-border bg-surface shadow-raised rounded-card absolute right-0 z-40 mt-2 w-64 border p-2"
        >
          <div className="border-border mb-2 border-b px-3 pt-1.5 pb-3">
            <p className="text-foreground truncate text-sm font-semibold">
              {displayName}
            </p>
            <p className="text-subtle truncate text-sm">{secondLine}</p>
          </div>
          <ul>
            <li>
              <Link href="/profile" onClick={close} className={ITEM_CLASSES}>
                <User aria-hidden="true" className="text-muted size-4" />
                Your profile
              </Link>
            </li>
            <li>
              <Link
                href="/profile/verification"
                onClick={close}
                className={ITEM_CLASSES}
              >
                <ShieldCheck aria-hidden="true" className="text-muted size-4" />
                Verification
              </Link>
            </li>
            <li>
              <Link href="/status" onClick={close} className={ITEM_CLASSES}>
                <Activity aria-hidden="true" className="text-muted size-4" />
                System status
              </Link>
            </li>
            <li>
              {/* A button, not a link: logging out changes something on
                  the server (it ends the session), so it must be a POST. */}
              <button
                type="button"
                disabled={isSigningOut}
                onClick={() => {
                  setIsSigningOut(true);
                  void signOut();
                }}
                className={cn(ITEM_CLASSES, "disabled:opacity-60")}
              >
                <LogOut aria-hidden="true" className="text-muted size-4" />
                {isSigningOut ? "Logging out…" : "Log out"}
              </button>
            </li>
          </ul>
        </div>
      )}
    </div>
  );
}
