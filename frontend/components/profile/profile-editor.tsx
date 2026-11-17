"use client";

import { ProfileStepFields } from "@/components/profile/profile-fields";
import { useSession } from "@/components/session/session-provider";
import { Alert } from "@/components/ui/alert";
import { Button, ButtonLink } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useForm } from "@/hooks/use-form";
import {
  PROFILE_STEPS,
  accountToFormValues,
  saveWholeProfile,
  validateProfile,
  type ProfileFormValues,
} from "@/lib/profile-form";
import { describeApiError } from "@/services/api-client";

/** Every section of the profile on one page, with a single Save button. */
export function ProfileEditor() {
  const { account, setAccount } = useSession();

  const form = useForm<ProfileFormValues>({
    initialValues: accountToFormValues(account),
    validate: validateProfile,
    onSubmit: async (values) => {
      try {
        setAccount(await saveWholeProfile(values));
        return { ok: true };
      } catch (error) {
        return { ok: false, message: describeApiError(error) };
      }
    },
  });

  return (
    <form {...form.formProps} className="space-y-5">
      {PROFILE_STEPS.map((step) => (
        <Card key={step.id} padding="lg">
          <h2 className="text-lg font-semibold">{step.title}</h2>
          <p className="text-muted mt-1 mb-5 text-sm leading-relaxed">
            {step.description}
          </p>
          <ProfileStepFields stepId={step.id} form={form} />
        </Card>
      ))}

      {form.formError && (
        <Alert tone="danger" role="alert" title="Your changes were not saved">
          {form.formError}
        </Alert>
      )}
      {form.isSuccess && (
        <Alert tone="success" role="status" title="Saved">
          Your profile has been updated.
        </Alert>
      )}

      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <ButtonLink href="/profile" variant="secondary">
          Back to profile
        </ButtonLink>
        <Button type={form.submitType} isLoading={form.isSubmitting}>
          Save changes
        </Button>
      </div>
    </form>
  );
}
