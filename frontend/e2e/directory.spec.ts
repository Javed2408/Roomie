import { expect, test, type Page } from "@playwright/test";

import { PASSWORD, completeProfile, field, registerMember } from "./fixtures";

/*
 * Choosing preferred societies from the real directory.
 *
 * The test backend holds FICTIONAL fixture records (see
 * backend/app/scripts/seed_test_fixtures.py): four that students may see,
 * and three that must never appear (unverified, switched off, or in an
 * unverified area).
 */

const VISIBLE = [
  "Alpha Fixture Residency",
  "Beta Fixture Towers",
  "Gamma Fixture Gardens",
  "Delta Fixture Court",
  "Epsilon Fixture Lane",
  "Zeta Fixture Villas",
];
const NEVER_VISIBLE = [
  "Unverified Fixture Heights",
  "Inactive Fixture Park",
  "Hidden Area Fixture Homes",
];

/** Open the profile editor and wait until the society list has loaded. */
async function openSocietyPicker(page: Page): Promise<void> {
  await page.goto("/profile/edit");
  await expect(page.locator('form[data-ready="true"]')).toBeVisible();
  await expect(
    page.getByRole("checkbox", { name: /Alpha Fixture Residency/ }),
  ).toBeVisible();
}

const searchBox = (page: Page) =>
  field(page, "Search societies by name or area");
const results = (page: Page) => page.getByRole("checkbox", { name: /Fixture/ });

test.beforeEach(async ({ page }) => {
  await completeProfile(page, await registerMember(page));
});

test("only verified, active societies can be chosen", async ({ page }) => {
  await openSocietyPicker(page);

  for (const name of VISIBLE) {
    await expect(
      page.getByRole("checkbox", { name: new RegExp(name) }),
    ).toBeVisible();
  }
  for (const name of NEVER_VISIBLE) {
    await expect(page.getByText(name)).toHaveCount(0);
  }

  // Not even by searching for them directly.
  await searchBox(page).fill("Unverified");
  await expect(page.getByText("No societies match “Unverified”")).toBeVisible();
});

test("search narrows the list and says when nothing matches", async ({
  page,
}) => {
  await openSocietyPicker(page);

  await searchBox(page).fill("gamma");
  await expect(
    page.getByRole("checkbox", { name: /Gamma Fixture Gardens/ }),
  ).toBeVisible();
  await expect(
    page.getByRole("checkbox", { name: /Alpha Fixture Residency/ }),
  ).toHaveCount(0);

  await searchBox(page).fill("no such society anywhere");
  await expect(
    page.getByText("No societies match “no such society anywhere”"),
  ).toBeVisible();

  // Clearing the search brings the full list back and keeps the cursor in
  // the search box.
  await page.getByRole("button", { name: "Clear search" }).click();
  await expect(searchBox(page)).toHaveValue("");
  await expect(searchBox(page)).toBeFocused();
  await expect(
    page.getByRole("checkbox", { name: /Alpha Fixture Residency/ }),
  ).toBeVisible();
});

test("the area filter shows one locality at a time", async ({ page }) => {
  await openSocietyPicker(page);
  const filter = page.getByRole("group", { name: "Filter by area" });

  // The hidden area is not offered as a filter.
  await expect(
    filter.getByRole("button", { name: "Fixture Town Hidden" }),
  ).toHaveCount(0);

  await filter.getByRole("button", { name: "Fixture Town South" }).click();
  await expect(
    filter.getByRole("button", { name: "Fixture Town South" }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(
    page.getByRole("checkbox", { name: /Gamma Fixture Gardens/ }),
  ).toBeVisible();
  await expect(
    page.getByRole("checkbox", { name: /Beta Fixture Towers/ }),
  ).toHaveCount(0);

  // Search and area filter combine.
  await searchBox(page).fill("alpha");
  await expect(
    page.getByText("No societies match “alpha” in Fixture Town South"),
  ).toBeVisible();

  await filter.getByRole("button", { name: "All areas" }).click();
  await expect(
    page.getByRole("checkbox", { name: /Alpha Fixture Residency/ }),
  ).toBeVisible();
});

test("choices can be added, removed, saved and still be there after logging in again", async ({
  page,
}) => {
  const member = await registerMember(page);
  await completeProfile(page, member);
  await openSocietyPicker(page);
  const order = page.getByRole("list", { name: "Your order of preference" });

  // The completed profile starts with two societies. Add a third...
  await page.getByRole("checkbox", { name: /Gamma Fixture Gardens/ }).check();
  await expect(order.getByRole("listitem")).toHaveCount(3);

  // ...remove the first one, even after searching for something else.
  const [firstChoice] = await order.getByRole("listitem").allInnerTexts();
  await searchBox(page).fill("delta");
  await expect(results(page)).toHaveCount(1);
  const firstName = VISIBLE.find((name) => firstChoice?.includes(name)) ?? "";
  await page.getByRole("button", { name: `Remove ${firstName}` }).click();
  await expect(order.getByRole("listitem")).toHaveCount(2);

  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByText("Your profile has been updated.")).toBeVisible();

  // Log out, log back in: the saved choices are exactly what was chosen.
  await page.getByRole("button", { name: /Account menu/ }).click();
  await page.getByRole("button", { name: "Log out" }).click();
  await expect(page).toHaveURL("/login");
  await expect(page.locator('form[data-ready="true"]')).toBeVisible();
  await field(page, "Email").fill(member.email);
  await field(page, "Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).toHaveURL("/dashboard");

  await page.goto("/profile");
  const saved = page
    .getByRole("main")
    .getByRole("heading", { name: "Preferred societies" })
    .locator("..")
    .getByRole("listitem");
  await expect(saved).toHaveCount(2);
  await expect(saved.last()).toContainText("Gamma Fixture Gardens");
  await expect(page.getByText(firstName)).toHaveCount(0);
});

test("no more than five can be chosen", async ({ page }) => {
  await openSocietyPicker(page);
  const order = page.getByRole("list", { name: "Your order of preference" });

  // The profile starts with two. Add more until the limit of five.
  const unchosen = [];
  for (const name of VISIBLE) {
    const box = page.getByRole("checkbox", { name: new RegExp(name) });
    if (!(await box.isChecked())) {
      unchosen.push(box);
    }
  }
  expect(unchosen).toHaveLength(4);
  for (const box of unchosen.slice(0, 3)) {
    await box.check();
  }

  await expect(order.getByRole("listitem")).toHaveCount(5);
  await expect(page.getByText("the most allowed")).toBeVisible();
  // The sixth cannot be ticked.
  await expect(unchosen[3]).toBeDisabled();
});
