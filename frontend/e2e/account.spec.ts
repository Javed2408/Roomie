import { expect, test, type Page } from "@playwright/test";

import { completeProfile, field, registerMember } from "./fixtures";

/*
 * Onboarding and verification, saved for real by the backend. These tests
 * use a brand-new member each time and check that what was entered is
 * still there after reloading or signing in again.
 */

const PDF = {
  name: "passport.pdf",
  mimeType: "application/pdf",
  buffer: Buffer.from("%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n"),
};

async function openOnboarding(page: Page): Promise<void> {
  await page.goto("/onboarding");
  await expect(page.locator('form[data-ready="true"]')).toBeVisible();
}

const continueButton = (page: Page) =>
  page.getByRole("button", { name: "Continue" });

test.describe("onboarding", () => {
  test("saves each step and publishes a complete profile", async ({ page }) => {
    await registerMember(page);
    await openOnboarding(page);
    await expect(page.getByText("Step 1 of 6")).toBeVisible();

    // A step cannot be skipped while its required fields are empty.
    await continueButton(page).click();
    await expect(page.getByText("Enter your name.")).toBeVisible();
    await expect(field(page, "Full name")).toBeFocused();

    await field(page, "Full name").fill("Priya Sharma");
    await field(page, "College or university").fill("SRM IST");
    await continueButton(page).click();

    await expect(
      page.getByRole("heading", { name: "About you", level: 1 }),
    ).toBeFocused();
    await field(page, "Bio (optional)").fill("Quiet, tidy and friendly.");
    await continueButton(page).click();

    await expect(
      page.getByRole("heading", { name: "Budget and move-in", level: 1 }),
    ).toBeVisible();
    await field(page, "Minimum budget (₹ / month)").fill("12000");
    await field(page, "Maximum budget (₹ / month)").fill("9000");
    await field(page, "Move-in date").fill("2027-01-10");
    await continueButton(page).click();
    await expect(
      page.getByText("Must be at least your minimum."),
    ).toBeVisible();
    await field(page, "Maximum budget (₹ / month)").fill("14000");
    await continueButton(page).click();

    // Societies come from the backend's directory.
    await expect(
      page.getByRole("heading", { name: "Preferred societies", level: 1 }),
    ).toBeVisible();
    await continueButton(page).click();
    await expect(page.getByText("Choose at least one society.")).toBeVisible();
    await page.getByRole("checkbox", { name: /Beta Fixture Towers/ }).check();
    await page
      .getByRole("checkbox", { name: /Alpha Fixture Residency/ })
      .check();
    await page
      .getByRole("button", { name: "Move Alpha Fixture Residency up" })
      .click();
    const order = page.getByRole("list", { name: "Your order of preference" });
    await expect(order.getByRole("listitem").first()).toContainText(
      "Alpha Fixture Residency",
    );
    await continueButton(page).click();

    // Lifestyle answers are optional.
    await expect(
      page.getByRole("heading", { name: "Lifestyle", level: 1 }),
    ).toBeVisible();
    await page.getByRole("radio", { name: "Vegetarian", exact: true }).check();
    await continueButton(page).click();

    await expect(
      page.getByRole("heading", { name: "Review your profile", level: 1 }),
    ).toBeVisible();
    await expect(page.getByText("Priya Sharma")).toBeVisible();
    await expect(page.getByText("₹12,000 – ₹14,000 / month")).toBeVisible();

    await page.getByRole("button", { name: "Publish profile" }).click();
    await expect(
      page.getByRole("heading", { name: "Your profile is ready" }),
    ).toBeVisible();

    // The profile page now shows what was entered, from the backend.
    await page.goto("/profile");
    await expect(
      page.getByRole("heading", { name: "Priya Sharma", level: 2 }),
    ).toBeVisible();
    await expect(page.getByText("Quiet, tidy and friendly.")).toBeVisible();
    await expect(page.getByText("₹12,000 – ₹14,000")).toBeVisible();
    await expect(page.getByText("Vegetarian")).toBeVisible();
    const societies = page.getByRole("main").getByRole("list").first();
    await expect(societies.getByRole("listitem").first()).toContainText(
      "Alpha Fixture Residency",
    );
  });

  test("progress is kept when the browser is closed halfway", async ({
    page,
  }) => {
    await registerMember(page);
    await openOnboarding(page);

    await field(page, "Full name").fill("Priya Sharma");
    await field(page, "College or university").fill("SRM IST");
    await continueButton(page).click();
    await expect(
      page.getByRole("heading", { name: "About you", level: 1 }),
    ).toBeVisible();
    await continueButton(page).click();
    await expect(
      page.getByRole("heading", { name: "Budget and move-in", level: 1 }),
    ).toBeVisible();

    // Come back later: the wizard resumes at the first unfinished step...
    await openOnboarding(page);
    await expect(
      page.getByRole("heading", { name: "Budget and move-in", level: 1 }),
    ).toBeVisible();
    await expect(page.getByText("Step 3 of 6")).toBeVisible();

    // ...and the earlier answers are still there.
    await page.getByRole("button", { name: "Back" }).click();
    await page.getByRole("button", { name: "Back" }).click();
    await expect(field(page, "Full name")).toHaveValue("Priya Sharma");
  });

  test("two members keep separate profiles", async ({ browser }) => {
    const first = await browser.newContext();
    const second = await browser.newContext();
    try {
      const firstPage = await first.newPage();
      const secondPage = await second.newPage();
      await completeProfile(
        firstPage,
        await registerMember(firstPage),
        "First Person",
      );
      await completeProfile(
        secondPage,
        await registerMember(secondPage),
        "Second Person",
      );

      await firstPage.goto("/profile");
      await secondPage.goto("/profile");

      await expect(
        firstPage.getByRole("heading", { name: "First Person", level: 2 }),
      ).toBeVisible();
      await expect(
        secondPage.getByRole("heading", { name: "Second Person", level: 2 }),
      ).toBeVisible();
      await expect(firstPage.getByText("Second Person")).toHaveCount(0);
    } finally {
      await first.close();
      await second.close();
    }
  });
});

test.describe("verification", () => {
  test("identity and student status are submitted separately", async ({
    page,
  }) => {
    await completeProfile(page, await registerMember(page));
    await page.goto("/profile/verification");

    const main = page.getByRole("main");
    await expect(main.getByText("Not submitted")).toHaveCount(2);
    await expect(
      page.getByText("Nothing is approved automatically"),
    ).toBeVisible();

    // Upload an identity document.
    const identity = main
      .locator("form")
      .filter({ has: page.getByRole("button", { name: "Upload for review" }) })
      .first();
    await expect(async () => {
      await identity.getByLabel("Document").setInputFiles(PDF);
      await identity.getByRole("button", { name: "Upload for review" }).click();
      await expect(page.getByText("Document received")).toBeVisible({
        timeout: 2000,
      });
    }).toPass({ timeout: 15_000 });

    // Identity is now waiting for a person. It is NOT verified, and the
    // student check has not moved at all.
    await expect(main.getByText("Under review")).toHaveCount(1);
    await expect(main.getByText("Not submitted")).toHaveCount(1);
    await expect(main.getByText("Verified", { exact: true })).toHaveCount(0);
    await expect(page.getByText("passport.pdf")).toBeVisible();

    // Still there after a reload: it was saved by the backend.
    await page.reload();
    await expect(main.getByText("Under review")).toHaveCount(1);
    await expect(page.getByText("passport.pdf")).toBeVisible();
  });

  test("a file of the wrong type is refused before uploading", async ({
    page,
  }) => {
    await completeProfile(page, await registerMember(page));
    await page.goto("/profile/verification");
    const identity = page.getByRole("main").locator("form").first();

    await expect(async () => {
      await identity.getByLabel("Document").setInputFiles({
        name: "notes.txt",
        mimeType: "text/plain",
        buffer: Buffer.from("just some text"),
      });
      await identity.getByRole("button", { name: "Upload for review" }).click();
      await expect(
        page.getByText("Choose a PDF, JPEG or PNG file."),
      ).toBeVisible({ timeout: 2000 });
    }).toPass({ timeout: 15_000 });

    await expect(page.getByRole("main").getByText("Not submitted")).toHaveCount(
      2,
    );
  });

  test("a document can be downloaded only by its owner", async ({
    page,
    browser,
  }) => {
    const member = await registerMember(page);
    await completeProfile(page, member);
    await page.goto("/profile/verification");
    const identity = page.getByRole("main").locator("form").first();
    await expect(async () => {
      await identity.getByLabel("Document").setInputFiles(PDF);
      await identity.getByRole("button", { name: "Upload for review" }).click();
      await expect(page.getByText("Document received")).toBeVisible({
        timeout: 2000,
      });
    }).toPass({ timeout: 15_000 });

    const url = await page
      .getByRole("link", { name: "Download" })
      .getAttribute("href");
    expect(url).toBeTruthy();
    // The address reveals nothing about where the file is kept.
    expect(url).toMatch(/\/verification-documents\/[0-9a-f-]{36}\/content$/);

    // The owner can fetch it...
    const mine = await page.request.get(url ?? "");
    expect(mine.status()).toBe(200);

    // ...a visitor cannot, and nor can another signed-in member.
    const visitor = await browser.newContext();
    const stranger = await browser.newContext();
    try {
      expect((await visitor.request.get(url ?? "")).status()).toBe(401);
      const strangerPage = await stranger.newPage();
      await registerMember(strangerPage);
      expect((await strangerPage.request.get(url ?? "")).status()).toBe(404);
    } finally {
      await visitor.close();
      await stranger.close();
    }
  });
});
