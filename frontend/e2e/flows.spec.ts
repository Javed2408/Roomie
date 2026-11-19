import type { Browser } from "@playwright/test";

import {
  discoverablePerson,
  expect,
  field,
  test,
  uniqueTag,
  until,
  type OtherPerson,
} from "./fixtures";

/*
 * Journeys through the signed-in app. Each test starts signed in as a
 * brand-new member with a complete profile (see fixtures.ts).
 *
 * Profiles, Discover and matches are real and saved by the backend.
 * Listings are real too (see listings.spec.ts). Chat and reporting still
 * use sample data and stand-in services until their roadmap phases.
 */

/** Someone else to look at, with a name no other test uses. */
async function someoneElse(
  browser: Browser,
): Promise<OtherPerson & { name: string }> {
  const name = `Meera ${uniqueTag()}`;
  return { ...(await discoverablePerson(browser, name)), name };
}
test.describe("profile", () => {
  test("can be opened for editing, validated and saved", async ({ page }) => {
    await page.goto("/profile");
    await page.getByRole("link", { name: "Edit profile" }).click();
    await expect(page).toHaveURL("/profile/edit");

    // The form starts filled in with the current profile.
    await expect(field(page, "Full name")).toHaveValue("Ananya Rao");

    await field(page, "Full name").fill("");
    await page.getByRole("button", { name: "Save changes" }).click();
    await expect(page.getByText("Enter your name.")).toBeVisible();

    await field(page, "Full name").fill("Ananya R. Rao");
    await page.getByRole("button", { name: "Save changes" }).click();
    await expect(
      page.getByText("Your profile has been updated."),
    ).toBeVisible();

    // The change really was saved: it survives a full page reload.
    await page.reload();
    await expect(field(page, "Full name")).toHaveValue("Ananya R. Rao");
  });

  test("another student's full profile opens from Discover", async ({
    page,
    browser,
  }) => {
    const other = await someoneElse(browser);
    try {
      await page.goto("/discover");
      await page.getByRole("link", { name: "View full profile" }).click();

      await expect(page).toHaveURL(/\/students\/[0-9a-f-]{36}$/);
      await expect(page.getByText("More about home life")).toBeVisible();
      // Nobody here has been verified, and nothing says otherwise.
      await expect(
        page.getByText("Identity: not verified").filter({ visible: true }),
      ).toBeVisible();
    } finally {
      await other.close();
    }
  });
});

test.describe("report and block", () => {
  test("a report needs a reason and makes no promise about timing", async ({
    page,
    browser,
  }) => {
    const other = await someoneElse(browser);
    await page.goto(`/students/${other.member.id}`);
    const dialog = page.getByRole("dialog", { name: `Report ${other.name}` });

    await until(
      () => page.getByRole("button", { name: "Report" }).click(),
      () => expect(dialog).toBeVisible({ timeout: 1000 }),
    );

    await dialog.getByRole("button", { name: "Send report" }).click();
    await expect(dialog.getByText("Choose a reason.")).toBeVisible();

    await dialog
      .getByRole("radio", { name: "Scam or request for money" })
      .check();
    await dialog.getByRole("button", { name: "Send report" }).click();

    await expect(dialog.getByText("Thank you for telling us")).toBeVisible();
    await expect(
      dialog.getByText("We cannot promise how quickly"),
    ).toBeVisible();

    await dialog.getByRole("button", { name: "Done" }).click();
    await expect(dialog).toBeHidden();
    await other.close();
  });

  test("blocking asks for confirmation and can be undone", async ({
    page,
    browser,
  }) => {
    const other = await someoneElse(browser);
    await page.goto(`/students/${other.member.id}`);
    const dialog = page.getByRole("dialog", { name: `Block ${other.name}?` });

    await until(
      () => page.getByRole("button", { name: "Block", exact: true }).click(),
      () => expect(dialog).toBeVisible({ timeout: 1000 }),
    );

    // Escape cancels without blocking.
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
    await expect(page.getByText("You have blocked")).toHaveCount(0);

    await page.getByRole("button", { name: "Block", exact: true }).click();
    await dialog.getByRole("button", { name: "Block", exact: true }).click();
    await expect(
      page.getByText(`You have blocked ${other.name}`),
    ).toBeVisible();

    await page.getByRole("button", { name: "Unblock" }).click();
    await expect(page.getByText("You have blocked")).toHaveCount(0);
    await other.close();
  });
});

// Listings have their own file: listings.spec.ts.

// Messaging is built in roadmap Phase 7; until then this is sample data.
test.describe("messages", () => {
  test("a message can be written and appears in the thread", async ({
    page,
  }) => {
    await page.goto("/messages");
    await page.getByRole("link", { name: /Meera Iyer/ }).click();
    await expect(page).toHaveURL("/messages/conversation-meera");

    const messages = page.getByRole("list", { name: "Messages" });
    await expect(messages.getByRole("listitem")).toHaveCount(3);

    // An empty message is not sent.
    await page.getByRole("button", { name: "Send message" }).click();
    await expect(page.getByText("Write a message first.")).toBeVisible();

    await page
      .getByRole("textbox", { name: "Message Meera" })
      .fill("Saturday works!");
    await page.getByRole("button", { name: "Send message" }).click();

    await expect(messages.getByRole("listitem")).toHaveCount(4);
    await expect(messages.getByText("Saturday works!")).toBeVisible();
    await expect(
      page.getByRole("textbox", { name: "Message Meera" }),
    ).toHaveValue("");
  });

  test("a new match starts with an empty conversation", async ({ page }) => {
    await page.goto("/messages/conversation-kavya");

    await expect(page.getByText("You and Kavya matched.")).toBeVisible();
  });
});

test.describe("legal pages", () => {
  for (const { url, title } of [
    { url: "/terms", title: "Terms of Use" },
    { url: "/privacy", title: "Privacy Policy" },
  ]) {
    test(`${title} is marked as a draft`, async ({ page }) => {
      await page.goto(url);

      await expect(
        page.getByRole("heading", { name: title, level: 1 }),
      ).toBeVisible();
      await expect(page.getByText("Draft, not yet in force")).toBeVisible();
    });
  }

  test("the register screen links to both", async ({ page }) => {
    await page.goto("/register");

    await expect(
      page.getByRole("link", { name: /Terms of Use/ }),
    ).toHaveAttribute("href", "/terms");
    await expect(
      page.getByRole("link", { name: /Privacy Policy/ }),
    ).toHaveAttribute("href", "/privacy");
  });
});

test.describe("dark mode", () => {
  test.use({ colorScheme: "dark" });

  test("follows the device setting", async ({ page }) => {
    await page.goto("/dashboard");

    const background = await page.evaluate(
      () => getComputedStyle(document.body).backgroundColor,
    );
    expect(background).toBe("rgb(20, 19, 18)");
    await expect(
      page.getByRole("heading", { name: /Welcome back/, level: 1 }),
    ).toBeVisible();
  });
});
