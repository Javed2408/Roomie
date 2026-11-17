"use client";

import Link from "next/link";

import { AuthHeading } from "@/components/auth/auth-heading";
import { SuccessPanel } from "@/components/auth/success-panel";
import { Alert } from "@/components/ui/alert";
import { Button, ButtonLink } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { PasswordField } from "@/components/ui/password-field";
import { TextField } from "@/components/ui/text-field";
import { useForm } from "@/hooks/use-form";
import {
  PASSWORD_MIN_LENGTH,
  validateEmail,
  validateNewPassword,
  validatePasswordConfirmation,
} from "@/lib/validation";
import { register } from "@/services/auth";

// Written out so TypeScript treats `acceptedTerms` as "true or false"
// rather than as the fixed starting value `false`.
type RegisterValues = {
  email: string;
  password: string;
  confirmPassword: string;
  acceptedTerms: boolean;
};

/** Opens in a new tab, so reading the terms does not clear the form. */
function LegalLink({ href, children }: { href: string; children: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener"
      className="text-primary hover:text-primary-hover font-medium underline underline-offset-4"
    >
      {children}
      <span className="sr-only"> (opens in a new tab)</span>
    </a>
  );
}

export function RegisterForm() {
  const form = useForm<RegisterValues>({
    resetWhenHidden: true,
    initialValues: {
      email: "",
      password: "",
      confirmPassword: "",
      acceptedTerms: false,
    },
    validate: (values) => ({
      email: validateEmail(values.email),
      password: validateNewPassword(values.password),
      confirmPassword: validatePasswordConfirmation(
        values.password,
        values.confirmPassword,
      ),
      acceptedTerms: values.acceptedTerms
        ? undefined
        : "Please accept the terms to continue.",
    }),
    onSubmit: (values) =>
      register(values.email, values.password, values.acceptedTerms),
  });

  if (form.isSuccess) {
    return (
      <SuccessPanel
        title="Your account is ready"
        actions={
          <ButtonLink href="/onboarding" size="lg" fullWidth>
            Set up your profile
          </ButtonLink>
        }
      >
        <p>
          We have sent a link to{" "}
          <span className="text-foreground font-medium break-all">
            {form.values.email.trim()}
          </span>
          . Open it to confirm that the address is yours.
        </p>
        <p>You can start setting up your profile while you wait.</p>
      </SuccessPanel>
    );
  }

  return (
    <>
      <AuthHeading
        title="Create your account"
        description="It takes a minute. You will set up your profile next."
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
          hint="A college email is not required."
          value={form.values.email}
          onChange={(event) => form.setValue("email", event.target.value)}
          onBlur={() => form.markTouched("email")}
          error={form.errors.email}
        />

        <PasswordField
          label="Password"
          name="password"
          autoComplete="new-password"
          hint={`${PASSWORD_MIN_LENGTH}+ characters, with a letter and a number.`}
          value={form.values.password}
          onChange={(event) => form.setValue("password", event.target.value)}
          onBlur={() => form.markTouched("password")}
          error={form.errors.password}
        />

        <PasswordField
          label="Confirm password"
          name="confirmPassword"
          autoComplete="new-password"
          value={form.values.confirmPassword}
          onChange={(event) =>
            form.setValue("confirmPassword", event.target.value)
          }
          onBlur={() => form.markTouched("confirmPassword")}
          error={form.errors.confirmPassword}
        />

        <Checkbox
          name="acceptedTerms"
          checked={form.values.acceptedTerms}
          onChange={(event) =>
            form.setValue("acceptedTerms", event.target.checked)
          }
          error={form.errors.acceptedTerms}
        >
          I agree to Roomie&apos;s{" "}
          <LegalLink href="/terms">Terms of Use</LegalLink> and{" "}
          <LegalLink href="/privacy">Privacy Policy</LegalLink>.
        </Checkbox>

        <Button
          type={form.submitType}
          size="lg"
          fullWidth
          isLoading={form.isSubmitting}
        >
          Create account
        </Button>
      </form>

      <p className="text-muted mt-6 text-center text-sm">
        Already have an account?{" "}
        <Link
          href="/login"
          className="text-primary hover:text-primary-hover font-medium underline-offset-4 hover:underline"
        >
          Log in
        </Link>
      </p>
    </>
  );
}
