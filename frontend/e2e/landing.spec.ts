import { expect, test } from "@playwright/test";

test("landing page introduces Roomie and its main sections", async ({
  page,
}) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", {
      name: "Find people you can actually live with.",
      level: 1,
    }),
  ).toBeVisible();

  for (const heading of [
    "People first, then the place",
    "Compatibility you can see the reasons for",
    "Find a place, or the people to rent one with",
    "Built for trust, honest about its limits",
    "Start with where you want to live",
    "Ready to find your people?",
  ]) {
    await expect(
      page.getByRole("heading", { name: heading, level: 2 }),
    ).toBeVisible();
  }
});

test("landing page labels sample data and makes no guarantee", async ({
  page,
}) => {
  await page.goto("/");

  // Invented people and places must be marked as such.
  await expect(page.getByText("Sample data").first()).toBeVisible();
  // Nothing on the page may claim to have been verified.
  await expect(page.getByText(/identity verified/i)).toHaveCount(0);
  await expect(
    page.getByText("Roomie cannot guarantee any person, listing or property."),
  ).toBeVisible();
});

test("landing page calls to action lead to registration and login", async ({
  page,
}) => {
  await page.goto("/");

  await page
    .getByRole("banner")
    .getByRole("link", { name: "Get started" })
    .click();
  await expect(page).toHaveURL("/register");
  await expect(
    page.getByRole("heading", { name: "Create your account" }),
  ).toBeVisible();

  await page.goto("/");
  await page.getByRole("link", { name: "I already have an account" }).click();
  await expect(page).toHaveURL("/login");
});

test("landing page does not scroll sideways", async ({ page }) => {
  await page.goto("/");

  const overflow = await page.evaluate(
    () =>
      document.documentElement.scrollWidth -
      document.documentElement.clientWidth,
  );
  expect(overflow).toBe(0);
});

test("unknown addresses show the not-found page", async ({ page }) => {
  const response = await page.goto("/this-page-does-not-exist");

  expect(response?.status()).toBe(404);
  await expect(
    page.getByRole("heading", { name: "We could not find that page" }),
  ).toBeVisible();
});
