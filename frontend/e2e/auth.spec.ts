import { expect, test, type Page } from "@playwright/test";

import { PASSWORD, emailedLink, field, uniqueEmail } from "./fixtures";
import { FRONTEND_URL } from "./settings";

/*
 * Sign-up, sign-in, email confirmation and password reset, through the
 * real backend. Each test creates its own brand-new account.
 */

/**
 * Open a page and wait until its form is ready to use.
 *
 * For a moment after loading, a page is plain HTML whose buttons are not
 * wired up yet. The form marks itself with data-ready="true" once it is.
 */
async function openForm(page: Page, url: string): Promise<void> {
  await page.goto(url);
  await expect(
    page.locator('form[data-ready="true"]').filter({ visible: true }),
  ).toBeVisible();
}

/** Fill in and send the registration form. */
async function register(page: Page, email: string): Promise<void> {
  await openForm(page, "/register");
  await field(page, "Email").fill(email);
  await field(page, "Password").fill(PASSWORD);
  await field(page, "Confirm password").fill(PASSWORD);
  await page.getByRole("checkbox", { name: /I agree to Roomie/ }).check();
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(
    page.getByRole("heading", { name: "Your account is ready" }),
  ).toBeVisible();
}

async function logOut(page: Page): Promise<void> {
  await page.getByRole("button", { name: /Account menu/ }).click();
  await page.getByRole("button", { name: "Log out" }).click();
  await expect(page).toHaveURL("/login");
}

test.describe("register", () => {
  test("shows an error for each invalid field and keeps what was typed", async ({
    page,
  }) => {
    await openForm(page, "/register");

    await field(page, "Email").fill("not-an-email");
    await field(page, "Password").fill("short");
    await field(page, "Confirm password").fill("different");
    await page.getByRole("button", { name: "Create account" }).click();

    await expect(page.getByText("Enter a valid email address")).toBeVisible();
    await expect(page.getByText("Use at least 8 characters.")).toBeVisible();
    await expect(
      page.getByText("The two passwords do not match."),
    ).toBeVisible();
    await expect(
      page.getByText("Please accept the terms to continue."),
    ).toBeVisible();

    // Focus moves to the first field that needs fixing...
    await expect(field(page, "Email")).toBeFocused();
    // ...and nothing the person typed is thrown away.
    await expect(field(page, "Email")).toHaveValue("not-an-email");
  });

  test("an error appearing does not move the submit button", async ({
    page,
  }) => {
    await openForm(page, "/register");
    const submit = page.getByRole("button", { name: "Create account" });
    const before = await submit.boundingBox();

    await field(page, "Email").fill("not-an-email");
    await field(page, "Password").focus();
    await expect(page.getByText("Enter a valid email address")).toBeVisible();

    // If the button had jumped, a click already on its way could miss it.
    const after = await submit.boundingBox();
    expect(after?.y).toBe(before?.y);
  });

  test("creates a real account and signs the person in", async ({ page }) => {
    const email = uniqueEmail();
    await register(page, email);
    await expect(page.getByText(email)).toBeVisible();

    // Signed in already: the next step opens without asking to log in.
    await page.getByRole("link", { name: "Set up your profile" }).click();
    await expect(page).toHaveURL("/onboarding");
    await expect(
      page.getByRole("heading", { name: "Student details", level: 1 }),
    ).toBeVisible();
  });

  test("refuses an email that already has an account", async ({ page }) => {
    const email = uniqueEmail();
    await register(page, email);
    await page.context().clearCookies();

    await openForm(page, "/register");
    await field(page, "Email").fill(email);
    await field(page, "Password").fill(PASSWORD);
    await field(page, "Confirm password").fill(PASSWORD);
    await page.getByRole("checkbox", { name: /I agree to Roomie/ }).check();
    await page.getByRole("button", { name: "Create account" }).click();

    await expect(page.getByRole("main").getByRole("alert")).toContainText(
      "An account with this email already exists",
    );
    await expect(field(page, "Email")).toHaveValue(email);
  });

  test("password can be revealed and hidden again", async ({ page }) => {
    await openForm(page, "/register");

    const password = field(page, "Password");
    await password.fill(PASSWORD);
    await expect(password).toHaveAttribute("type", "password");

    await page.getByRole("button", { name: "Show password" }).first().click();
    await expect(password).toHaveAttribute("type", "text");

    await page.getByRole("button", { name: "Hide password" }).click();
    await expect(password).toHaveAttribute("type", "password");
  });
});

test.describe("login and logout", () => {
  test("requires an email and a password", async ({ page }) => {
    await openForm(page, "/login");

    await page.getByRole("button", { name: "Log in" }).click();

    await expect(page.getByText("Enter your email address.")).toBeVisible();
    await expect(page.getByText("Enter your password.")).toBeVisible();
    await expect(page).toHaveURL("/login");
  });

  test("a wrong password is refused without saying which part was wrong", async ({
    page,
  }) => {
    const email = uniqueEmail();
    await register(page, email);
    await page.context().clearCookies();

    await openForm(page, "/login");
    await field(page, "Email").fill(email);
    await field(page, "Password").fill("wrong-password1");
    await page.getByRole("button", { name: "Log in" }).click();

    await expect(page.getByRole("main").getByRole("alert")).toContainText(
      "The email or password is not correct.",
    );
    await expect(page).toHaveURL("/login");
  });

  test("the session survives a reload and ends on logout", async ({ page }) => {
    const email = uniqueEmail();
    await register(page, email);

    // Still signed in after a full page reload.
    await page.goto("/dashboard");
    await expect(
      page.getByRole("heading", { name: "Welcome to Roomie", level: 1 }),
    ).toBeVisible();
    await page.reload();
    await expect(
      page.getByRole("heading", { name: "Welcome to Roomie", level: 1 }),
    ).toBeVisible();

    await logOut(page);

    // The login form is empty, and protected pages are closed again.
    await expect(field(page, "Password")).toHaveValue("");
    await page.goto("/dashboard");
    await expect(page).toHaveURL("/login");

    // Logging back in works, and leads to finishing the profile.
    await openForm(page, "/login");
    await field(page, "Email").fill(email);
    await field(page, "Password").fill(PASSWORD);
    await page.getByRole("button", { name: "Log in" }).click();
    await expect(page).toHaveURL("/onboarding");
  });

  test("protected pages send visitors to the login page", async ({ page }) => {
    for (const url of ["/dashboard", "/profile", "/onboarding", "/discover"]) {
      await page.goto(url);
      await expect(page, `${url} should require login`).toHaveURL("/login");
    }
  });
});

test.describe("email confirmation", () => {
  test("the emailed link confirms the address", async ({ page }) => {
    const email = uniqueEmail();
    await register(page, email);

    // Until confirmed, signed-in pages show a reminder.
    await page.goto("/dashboard");
    await expect(page.getByText("Confirm your email address")).toBeVisible();

    const link = await emailedLink(email, "/verify-email");
    await page.goto(link);
    await expect(
      page.getByRole("heading", { name: "Email confirmed" }),
    ).toBeVisible();

    await page.getByRole("link", { name: "Continue" }).click();
    await expect(page).toHaveURL("/dashboard");
    await expect(page.getByText("Confirm your email address")).toHaveCount(0);

    // A confirmation link works only once.
    await page.goto(link);
    await expect(
      page.getByRole("heading", { name: "This link did not work" }),
    ).toBeVisible();
  });

  test("a made-up link is refused", async ({ page }) => {
    await page.goto("/verify-email?token=not-a-real-token");

    await expect(
      page.getByRole("heading", { name: "This link did not work" }),
    ).toBeVisible();
  });
});

test.describe("password reset", () => {
  test("gives the same answer for any email", async ({ page }) => {
    await openForm(page, "/forgot-password");

    await field(page, "Email").fill("nobody-at-all@example.com");
    await page.getByRole("button", { name: "Send reset link" }).click();

    await expect(
      page.getByRole("heading", { name: "Check your email" }),
    ).toBeVisible();
    await expect(page.getByText("If an account exists for")).toBeVisible();
  });

  test("the emailed link sets a new password", async ({ page }) => {
    const email = uniqueEmail();
    await register(page, email);
    await page.context().clearCookies();

    await openForm(page, "/forgot-password");
    await field(page, "Email").fill(email);
    await page.getByRole("button", { name: "Send reset link" }).click();
    await expect(
      page.getByRole("heading", { name: "Check your email" }),
    ).toBeVisible();

    const link = await emailedLink(email, "/reset-password");
    expect(link.startsWith("/reset-password?token=")).toBe(true);
    await openForm(page, link);
    await field(page, "New password").fill("brandnew2028");
    await field(page, "Confirm new password").fill("brandnew2028");
    await page.getByRole("button", { name: "Update password" }).click();
    await expect(
      page.getByRole("heading", { name: "Password updated" }),
    ).toBeVisible();

    // The old password no longer works; the new one does.
    await openForm(page, "/login");
    await field(page, "Email").fill(email);
    await field(page, "Password").fill(PASSWORD);
    await page.getByRole("button", { name: "Log in" }).click();
    await expect(page.getByRole("main").getByRole("alert")).toBeVisible();

    await field(page, "Password").fill("brandnew2028");
    await page.getByRole("button", { name: "Log in" }).click();
    await expect(page).toHaveURL("/onboarding");
  });

  test("the reset page without a token asks for a new link", async ({
    page,
  }) => {
    await page.goto("/reset-password");

    await expect(
      page.getByRole("heading", { name: "This link is not valid" }),
    ).toBeVisible();
  });
});

test.describe("before the page is ready", () => {
  // Turning JavaScript off freezes the page in its just-loaded state.
  test.use({ javaScriptEnabled: false });

  test("pressing Log in early never puts the password in the address", async ({
    page,
  }) => {
    await page.goto("/login");

    await page.getByLabel("Email", { exact: true }).fill("student@example.com");
    await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
    await page.getByRole("button", { name: "Log in" }).click();

    // Nothing was sent: same page, and no "?password=..." in the address.
    await expect(page).toHaveURL(`${FRONTEND_URL}/login`);
    await expect(page.locator("form")).toHaveAttribute("method", "post");
  });
});
