"use client";

import { useSearchParams } from "next/navigation";

import { AuthHeading } from "@/components/auth/auth-heading";
import { SuccessPanel } from "@/components/auth/success-panel";
import { Alert } from "@/components/ui/alert";
import { Button, ButtonLink } from "@/components/ui/button";
import { PasswordField } from "@/components/ui/password-field";
import { useForm } from "@/hooks/use-form";
import {
  PASSWORD_MIN_LENGTH,
  validateNewPassword,
  validatePasswordConfirmation,
} from "@/lib/validation";
import { resetPassword } from "@/services/auth";

/**
 * Reads the reset token from the link (`/reset-password?token=...`).
 * Because it reads the URL, the page wraps this component in <Suspense>.
 */
export function ResetPasswordForm() {
  const token = useSearchParams().get("token");

  const form = useForm({
    resetWhenHidden: true,
    initialValues: { password: "", confirmPassword: "" },
    validate: (values) => ({
      password: validateNewPassword(values.password),
      confirmPassword: validatePasswordConfirmation(
        values.password,
        values.confirmPassword,
      ),
    }),
    onSubmit: (values) => resetPassword(token ?? "", values.password),
  });

  // Someone opened the page without following a reset link.
  if (!token) {
    return (
      <>
        <AuthHeading
          title="This link is not valid"
          description="The password reset link is missing or incomplete. Request a new one and try again."
        />
        <div className="flex flex-col gap-3">
          <ButtonLink href="/forgot-password" size="lg" fullWidth>
            Request a new link
          </ButtonLink>
          <ButtonLink href="/login" variant="ghost" size="lg" fullWidth>
            Back to log in
          </ButtonLink>
        </div>
      </>
    );
  }

  if (form.isSuccess) {
    return (
      <SuccessPanel
        title="Password updated"
        actions={
          <ButtonLink href="/login" size="lg" fullWidth>
            Continue to log in
          </ButtonLink>
        }
      >
        <p>
          Your password has been changed and you have been logged out
          everywhere. Log in with your new password.
        </p>
      </SuccessPanel>
    );
  }

  return (
    <>
      <AuthHeading
        title="Choose a new password"
        description="Pick something you have not used before on Roomie."
      />

      <form {...form.formProps} className="space-y-3">
        {form.formError && (
          <Alert tone="danger" role="alert">
            {form.formError}
          </Alert>
        )}

        <PasswordField
          label="New password"
          name="password"
          autoComplete="new-password"
          hint={`${PASSWORD_MIN_LENGTH}+ characters, with a letter and a number.`}
          value={form.values.password}
          onChange={(event) => form.setValue("password", event.target.value)}
          onBlur={() => form.markTouched("password")}
          error={form.errors.password}
        />

        <PasswordField
          label="Confirm new password"
          name="confirmPassword"
          autoComplete="new-password"
          value={form.values.confirmPassword}
          onChange={(event) =>
            form.setValue("confirmPassword", event.target.value)
          }
          onBlur={() => form.markTouched("confirmPassword")}
          error={form.errors.confirmPassword}
        />

        <Button
          type={form.submitType}
          size="lg"
          fullWidth
          isLoading={form.isSubmitting}
        >
          Update password
        </Button>
      </form>
    </>
  );
}
