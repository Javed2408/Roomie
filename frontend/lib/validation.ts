/**
 * Client-side form validation rules.
 *
 * These give people fast feedback while typing. They are a convenience, not
 * security: the backend must validate everything again (roadmap Phase 3),
 * because anyone can bypass checks that run in their own browser.
 *
 * Each validator returns an error message, or `undefined` when the value is
 * acceptable.
 */

export const PASSWORD_MIN_LENGTH = 8;

// Deliberately simple: "something@something.something". The only real proof
// that an address works is the verification email.
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateEmail(value: string): string | undefined {
  const email = value.trim();
  if (!email) {
    return "Enter your email address.";
  }
  if (!EMAIL_PATTERN.test(email)) {
    return "Enter a valid email address.";
  }
  return undefined;
}

/** For login: only check that something was typed. */
export function validateRequiredPassword(value: string): string | undefined {
  return value ? undefined : "Enter your password.";
}

/** For choosing a new password. */
export function validateNewPassword(value: string): string | undefined {
  if (!value) {
    return "Choose a password.";
  }
  if (value.length < PASSWORD_MIN_LENGTH) {
    return `Use at least ${PASSWORD_MIN_LENGTH} characters.`;
  }
  if (!/[A-Za-z]/.test(value) || !/\d/.test(value)) {
    return "Add a letter and a number.";
  }
  return undefined;
}

export function validatePasswordConfirmation(
  password: string,
  confirmation: string,
): string | undefined {
  if (!confirmation) {
    return "Re-enter your password to confirm it.";
  }
  if (password !== confirmation) {
    return "The two passwords do not match.";
  }
  return undefined;
}
