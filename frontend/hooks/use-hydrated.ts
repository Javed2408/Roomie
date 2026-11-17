"use client";

import { useSyncExternalStore } from "react";

// Nothing ever changes after the first browser render, so there is nothing
// to subscribe to.
const subscribe = () => () => {};

/**
 * False while the page is plain HTML from the server, true once React has
 * taken over in the browser ("hydration") and buttons actually work.
 *
 * Use it to keep a control harmless during that short gap.
 */
export function useHydrated(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );
}
