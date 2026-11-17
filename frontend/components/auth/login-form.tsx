"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { AuthHeading } from "@/components/auth/auth-heading";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { PasswordField } from "@/components/ui/password-field";
import { TextField } from "@/components/ui/text-field";
import { useForm } from "@/hooks/use-form";
import { validateEmail, validateRequiredPassword } from "@/lib/validation";
import { fetchAccount } from "@/services/account";
import { signIn } from "@/services/auth";

export function LoginForm() {
  const router = useRouter();

  const form = useForm({
    resetWhenHidden: true,
    initialValues: { email: "", password: "" },
    validate: (values) => ({
      email: validateEmail(values.email),
      password: validateRequiredPassword(values.password),
    }),
    onSubmit: async (values) => {
      const result = await signIn(values.email, values.password);
      if (result.ok) {
        // Someone who has not finished their profile continues setting it
        // up; everyone else goes to their dashboard.
        const account = await fetchAccount().catch(() => null);
        router.push(
          account?.profile?.profileCompleted ? "/dashboard" : "/onboarding",
        );
      }
      return result;
    },
  });

  return (
    <>
      <AuthHeading
        title="Welcome back"
        description="Log in to see your matches and messages."
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

        <PasswordField
          label="Password"
          name="password"
          autoComplete="current-password"
          value={form.values.password}
          onChange={(event) => form.setValue("password", event.target.value)}
          onBlur={() => form.markTouched("password")}
          error={form.errors.password}
          labelAside={
            <Link
              href="/forgot-password"
              // -my-2 py-2 enlarges the tappable area without moving anything.
              className="text-primary hover:text-primary-hover -my-2 py-2 text-sm font-medium underline-offset-4 hover:underline"
            >
              Forgot your password?
            </Link>
          }
        />

        <Button
          type={form.submitType}
          size="lg"
          fullWidth
          isLoading={form.isSubmitting || form.isSuccess}
        >
          Log in
        </Button>
      </form>

      <p className="text-muted mt-6 text-center text-sm">
        New to Roomie?{" "}
        <Link
          href="/register"
          className="text-primary hover:text-primary-hover font-medium underline-offset-4 hover:underline"
        >
          Create an account
        </Link>
      </p>
    </>
  );
}
