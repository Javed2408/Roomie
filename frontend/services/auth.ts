/** Sign-up, sign-in, sign-out, email verification and password reset. */

import {
  ApiError,
  apiGet,
  apiPost,
  describeApiError,
  setCsrfToken,
} from "@/services/api-client";
import { parseSession } from "@/services/parse";
import type { SessionUser } from "@/types/account";

/** What forms receive: success, or a sentence to show the person. */
export type ActionResult = { ok: true } | { ok: false; message: string };

async function attempt(action: () => Promise<unknown>): Promise<ActionResult> {
  try {
    await action();
    return { ok: true };
  } catch (error) {
    return { ok: false, message: describeApiError(error) };
  }
}

/** Remember the session's anti-forgery token and return the user. */
function accept(responseBody: unknown): SessionUser {
  const session = parseSession(responseBody);
  setCsrfToken(session.csrfToken);
  return session.user;
}

/**
 * Who is signed in, or `null` for nobody. Called when a protected page
 * loads. The session itself lives in a cookie that scripts cannot read,
 * which is why the server has to be asked.
 */
export async function fetchSession(
  signal?: AbortSignal,
): Promise<SessionUser | null> {
  try {
    return accept(await apiGet("/auth/session", { signal }));
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      setCsrfToken(null);
      return null;
    }
    throw error;
  }
}

export function register(
  email: string,
  password: string,
  acceptedTerms: boolean,
): Promise<ActionResult> {
  return attempt(async () =>
    accept(
      await apiPost("/auth/register", {
        email,
        password,
        accepted_terms: acceptedTerms,
      }),
    ),
  );
}

export function signIn(email: string, password: string): Promise<ActionResult> {
  return attempt(async () =>
    accept(await apiPost("/auth/login", { email, password })),
  );
}

export async function signOut(): Promise<void> {
  try {
    await apiPost("/auth/logout");
  } finally {
    // Whatever happened, this browser no longer holds a usable token.
    setCsrfToken(null);
  }
}

export function verifyEmail(token: string): Promise<ActionResult> {
  return attempt(() => apiPost("/auth/verify-email", { token }));
}

export function resendVerificationEmail(): Promise<ActionResult> {
  return attempt(() => apiPost("/auth/resend-verification"));
}

/**
 * The backend answers the same way whether or not the address has an
 * account, so this cannot be used to find out who is registered.
 */
export function requestPasswordReset(email: string): Promise<ActionResult> {
  return attempt(() => apiPost("/auth/forgot-password", { email }));
}

export function resetPassword(
  token: string,
  newPassword: string,
): Promise<ActionResult> {
  return attempt(() =>
    apiPost("/auth/reset-password", { token, new_password: newPassword }),
  );
}
