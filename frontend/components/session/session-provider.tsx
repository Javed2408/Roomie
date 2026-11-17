"use client";

import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { PageSkeleton } from "@/components/app-shell/page-skeleton";
import { ErrorState } from "@/components/ui/states";
import { fetchAccount } from "@/services/account";
import { describeApiError } from "@/services/api-client";
import { fetchSession, signOut as signOutRequest } from "@/services/auth";
import type { Account } from "@/types/account";

type SessionState =
  | { status: "loading" }
  | { status: "signed-out" }
  | { status: "error"; message: string }
  | { status: "signed-in"; account: Account };

interface SessionContextValue {
  account: Account;
  /** Replace the account after a save, with what the backend returned. */
  setAccount: (account: Account) => void;
  /** Fetch the account again, e.g. after uploading a document. */
  refreshAccount: () => Promise<void>;
  signOut: () => Promise<void>;
}

const SessionContext = createContext<SessionContextValue | null>(null);

/**
 * The signed-in person's account. Only usable inside <RequireSession>,
 * which guarantees somebody is signed in before its children render.
 */
export function useSession(): SessionContextValue {
  const value = useContext(SessionContext);
  if (value === null) {
    throw new Error("useSession must be used inside <RequireSession>.");
  }
  return value;
}

/**
 * Wraps every page that needs a signed-in person.
 *
 * On load it asks the backend who is signed in. While waiting it shows a
 * placeholder; if nobody is signed in it sends the visitor to the login
 * page; otherwise it shows the page and makes the account available to
 * it through `useSession()`.
 *
 * This is a convenience for people, not the security boundary: the
 * backend checks the session on every request, so skipping this
 * component would reveal empty screens, not anyone's data.
 */
export function RequireSession({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<SessionState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      try {
        const user = await fetchSession(controller.signal);
        if (user === null) {
          setState({ status: "signed-out" });
          return;
        }
        const account = await fetchAccount(controller.signal);
        setState({ status: "signed-in", account });
      } catch (error) {
        if (!controller.signal.aborted) {
          setState({ status: "error", message: describeApiError(error) });
        }
      }
    }

    void load();
    return () => controller.abort();
  }, [attempt]);

  const isSignedOut = state.status === "signed-out";
  useEffect(() => {
    if (isSignedOut) {
      router.replace("/login");
    }
  }, [isSignedOut, router]);

  const setAccount = useCallback((account: Account) => {
    setState({ status: "signed-in", account });
  }, []);

  const refreshAccount = useCallback(async () => {
    setAccount(await fetchAccount());
  }, [setAccount]);

  const signOut = useCallback(async () => {
    try {
      await signOutRequest();
    } finally {
      // A full page load, not a client-side move: it throws away every
      // page kept in memory, so nothing of this person's is left behind
      // for whoever uses the browser next.
      // (Next.js recommends exactly this for logging out, so its usual
      // advice to use the router does not apply here.)
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.assign("/login");
    }
  }, []);

  const account = state.status === "signed-in" ? state.account : null;
  const value = useMemo(
    () => (account ? { account, setAccount, refreshAccount, signOut } : null),
    [account, setAccount, refreshAccount, signOut],
  );

  if (state.status === "error") {
    return (
      <div className="mx-auto w-full max-w-md px-5 py-16">
        <ErrorState
          title="We could not load your account"
          description={state.message}
          onRetry={() => {
            setState({ status: "loading" });
            setAttempt((current) => current + 1);
          }}
        />
      </div>
    );
  }

  if (value === null) {
    // Loading, or about to be redirected to the login page.
    return (
      <div className="mx-auto w-full max-w-5xl px-5 py-10">
        <PageSkeleton />
      </div>
    );
  }

  return (
    <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
  );
}
