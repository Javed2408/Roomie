"use client";

import {
  useLayoutEffect,
  useRef,
  useState,
  type ChangeEvent,
  type FormEvent,
} from "react";

import { useHydrated } from "@/hooks/use-hydrated";

/**
 * A form's values: text fields are strings, checkboxes are booleans, and
 * multi-select fields (such as preferred societies) are lists of strings.
 */
type FormValues = Record<string, string | boolean | string[]>;

type FormErrors<Values> = Partial<Record<keyof Values, string>>;

/** The names of the fields in `Values` whose value is a string. */
type TextFieldName<Values> = {
  [Key in keyof Values]: Values[Key] extends string ? Key : never;
}[keyof Values] &
  string;

type TextElement = HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement;

/** What `onSubmit` reports back when the request did not succeed. */
export type SubmitResult = { ok: true } | { ok: false; message: string };

interface UseFormOptions<Values extends FormValues> {
  initialValues: Values;
  /** Return an error message for each invalid field. */
  validate: (values: Values) => FormErrors<Values>;
  /** Called only when every field is valid. */
  onSubmit: (values: Values) => Promise<SubmitResult>;
  /**
   * Clear the form whenever its page is navigated away from.
   *
   * Next.js keeps a page you leave in memory (hidden) so that coming back
   * is instant, which means a form normally keeps what was typed. That is
   * helpful for a long draft, but wrong for sign-in forms: a password
   * should not linger once you have moved on. Those forms set this to true.
   *
   * Whatever this is set to, a form that was submitted successfully is
   * always cleared when hidden, so a stale "success" never reappears.
   */
  resetWhenHidden?: boolean;
}

export interface UseFormResult<Values extends FormValues> {
  values: Values;
  /** Errors for fields the person has already left, or all after a submit. */
  errors: FormErrors<Values>;
  /** A problem with the whole request, e.g. "email already registered". */
  formError: string | null;
  isSubmitting: boolean;
  isSuccess: boolean;
  setValue: <Key extends keyof Values>(name: Key, value: Values[Key]) => void;
  markTouched: (name: keyof Values) => void;
  /**
   * Everything a text input, select or textarea needs, in one go:
   * `<TextField label="Email" {...form.text("email")} />`
   */
  text: (name: TextFieldName<Values>) => {
    name: string;
    value: string;
    onChange: (event: ChangeEvent<TextElement>) => void;
    onBlur: () => void;
    error: string | undefined;
  };
  /**
   * For multi-step forms: check only the named fields. If any are invalid,
   * their errors are shown, focus moves to the first one inside `container`,
   * and the result is false.
   */
  validateFields: (
    names: Array<keyof Values & string>,
    container: HTMLElement | null,
  ) => boolean;
  /** Spread onto the <form> element: `<form {...form.formProps}>`. */
  formProps: {
    onSubmit: (event: FormEvent<HTMLFormElement>) => void;
    noValidate: true;
    method: "post";
    "data-ready": boolean;
  };
  /** Use as the submit button's `type`. See the note on `isReady` below. */
  submitType: "submit" | "button";
}

/**
 * Shared behaviour for Roomie's forms:
 *
 * - An error appears once someone leaves a field, not while they are still
 *   typing their first attempt.
 * - Submitting shows every error and moves focus to the first invalid field.
 * - What the person typed is always kept when validation fails.
 */
export function useForm<Values extends FormValues>({
  initialValues,
  validate,
  onSubmit,
  resetWhenHidden = false,
}: UseFormOptions<Values>): UseFormResult<Values> {
  const [values, setValues] = useState<Values>(initialValues);
  const [touched, setTouched] = useState<Partial<Record<keyof Values, true>>>(
    {},
  );
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Remembered once, so a reset returns to the very first values.
  const [startingValues] = useState(initialValues);
  const hasSucceededRef = useRef(false);

  /*
   * For a moment after a page loads, it is plain HTML and our submit
   * handler is not attached yet. A submit button pressed in that gap would
   * make the browser send the form the old-fashioned way. Two safeguards:
   *
   * 1. Until the page is ready, the button's type is "button", which does
   *    nothing when pressed. It becomes a real submit button afterwards.
   * 2. The form's method is "post". If the browser ever did send it by
   *    itself, the fields would travel in the request body, never in the
   *    page address where a password could end up in browser history.
   */
  const isReady = useHydrated();

  // Increases on every reset. A request that started before a reset can
  // tell it is out of date and must not touch the fresh form.
  const generationRef = useRef(0);

  // The clean-up function below runs when the page is hidden or removed.
  useLayoutEffect(() => {
    return () => {
      if (!resetWhenHidden && !hasSucceededRef.current) {
        return;
      }
      hasSucceededRef.current = false;
      generationRef.current += 1;
      setValues(startingValues);
      setTouched({});
      setHasSubmitted(false);
      setIsSubmitting(false);
      setIsSuccess(false);
      setFormError(null);
    };
  }, [resetWhenHidden, startingValues]);

  const allErrors = validate(values);

  const visibleErrors: FormErrors<Values> = {};
  for (const name of Object.keys(allErrors) as Array<keyof Values>) {
    if (hasSubmitted || touched[name]) {
      visibleErrors[name] = allErrors[name];
    }
  }

  function setValue<Key extends keyof Values>(name: Key, value: Values[Key]) {
    setValues((current) => ({ ...current, [name]: value }));
    setFormError(null);
    // Any edit makes an earlier "saved" message out of date.
    setIsSuccess(false);
  }

  function markTouched(name: keyof Values) {
    setTouched((current) => ({ ...current, [name]: true }));
  }

  function text(name: TextFieldName<Values>) {
    return {
      name,
      // `TextFieldName` guarantees this field holds a string, but TypeScript
      // cannot follow that through a generic lookup, hence the two casts.
      value: values[name] as string,
      onChange: (event: ChangeEvent<TextElement>) =>
        setValue(name, event.target.value as Values[typeof name]),
      onBlur: () => markTouched(name),
      error: visibleErrors[name],
    };
  }

  function focusField(container: HTMLElement | null, name: string) {
    const field = container?.querySelector(`[name="${CSS.escape(name)}"]`);
    if (field instanceof HTMLElement) {
      field.focus();
    }
  }

  function validateFields(
    names: Array<keyof Values & string>,
    container: HTMLElement | null,
  ): boolean {
    const invalid = names.filter((name) => allErrors[name]);
    if (invalid.length === 0) {
      return true;
    }
    setTouched((current) => {
      const next = { ...current };
      for (const name of names) {
        next[name] = true;
      }
      return next;
    });
    const firstInvalid = invalid[0];
    if (firstInvalid !== undefined) {
      focusField(container, firstInvalid);
    }
    return false;
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmitting) {
      return;
    }
    setHasSubmitted(true);

    const firstInvalidName = Object.keys(allErrors).find(
      (name) => allErrors[name as keyof Values],
    );
    if (firstInvalidName !== undefined) {
      focusField(event.currentTarget, firstInvalidName);
      return;
    }

    const generation = generationRef.current;
    const isCurrent = () => generation === generationRef.current;

    setIsSubmitting(true);
    setFormError(null);
    onSubmit(values)
      .then((result) => {
        if (!isCurrent()) {
          return;
        }
        if (result.ok) {
          hasSucceededRef.current = true;
          setIsSuccess(true);
        } else {
          setFormError(result.message);
        }
      })
      .catch((error: unknown) => {
        console.error("Form submission failed", error);
        if (isCurrent()) {
          setFormError("Something went wrong. Please try again.");
        }
      })
      .finally(() => {
        if (isCurrent()) {
          setIsSubmitting(false);
        }
      });
  }

  return {
    values,
    errors: visibleErrors,
    formError,
    isSubmitting,
    isSuccess,
    setValue,
    markTouched,
    text,
    validateFields,
    formProps: {
      onSubmit: handleSubmit,
      noValidate: true,
      method: "post",
      "data-ready": isReady,
    },
    submitType: isReady ? "submit" : "button",
  };
}
