"use client";

import Link from "next/link";

import { AuthHeading } from "@/components/auth/auth-heading";
import { SuccessPanel } from "@/components/auth/success-panel";
import { Alert } from "@/components/ui/alert";
import { Button, ButtonLink } from "@/components/ui/button";
import { TextField } from "@/components/ui/text-field";
import { useForm } from "@/hooks/use-form";
import { validateEmail } from "@/lib/validation";
import { requestPasswordReset } from "@/services/auth";

export function ForgotPasswordForm() {
  const form = useForm({
    resetWhenHidden: true,
    initialValues: { email: "" },
    validate: (values) => ({ email: validateEmail(values.email) }),
    onSubmit: (values) => requestPasswordReset(values.email),
  });

  if (form.isSuccess) {
    return (
      <SuccessPanel
        title="Check your email"
        actions={
          <ButtonLink href="/login" variant="secondary" size="lg" fullWidth>
            Back to log in
          </ButtonLink>
        }
      >
        {/*
          The wording is deliberately the same whether or not the address
          has an account, so this screen cannot be used to find out who is
          registered.
        */}
        <p>
          If an account exists for{" "}
          <span className="text-foreground font-medium break-all">
            {form.values.email.trim()}
          </span>
          , we have sent it a link to choose a new password. The link works for
          one hour.
        </p>
      </SuccessPanel>
    );
  }

  return (
    <>
      <AuthHeading
        title="Reset your password"
        description="Enter the email you signed up with and we will send you a link to choose a new password."
      />

      <form {...form.formProps} className="space-y-3">
        {form.formError && (
          <Alert tone="danger" role="alert">
            {form.formError}
          </Alert>
        )}

        <TextField
          label="Email"
          name="email"
          type="email"
          autoComplete="email"
          inputMode="email"
          value={form.values.email}
          onChange={(event) => form.setValue("email", event.target.value)}
          onBlur={() => form.markTouched("email")}
          error={form.errors.email}
        />

        <Button
          type={form.submitType}
          size="lg"
          fullWidth
          isLoading={form.isSubmitting}
        >
          Send reset link
        </Button>
      </form>

      <p className="text-muted mt-6 text-center text-sm">
        Remembered it?{" "}
        <Link
          href="/login"
          className="text-primary hover:text-primary-hover font-medium underline-offset-4 hover:underline"
        >
          Back to log in
        </Link>
      </p>
    </>
  );
}
