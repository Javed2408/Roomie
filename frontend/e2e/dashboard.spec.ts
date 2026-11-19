import { expect, test } from "./fixtures";

/*
 * The signed-in shell and its pages. Each test starts signed in as a new
 * member with a complete profile (see fixtures.ts), and runs twice: on a
 * desktop screen (sidebar) and on a phone (bottom tab bar).
 * `getByRole("navigation", { name: "Main" })` finds whichever is visible.
 */

const SECTIONS = [
  { link: "Discover", url: "/discover", heading: "Discover" },
  { link: "Matches", url: "/matches", heading: "Matches" },
  { link: "Messages", url: "/messages", heading: "Messages" },
  { link: "Accommodation", url: "/accommodation", heading: "Accommodation" },
  { link: "Home", url: "/dashboard", heading: /Welcome back/ },
];

test("main navigation reaches every section", async ({ page }) => {
  await page.goto("/dashboard");
  const nav = page.getByRole("navigation", { name: "Main" });

  for (const section of SECTIONS) {
    await nav.getByRole("link", { name: section.link, exact: true }).click();
    await expect(page).toHaveURL(section.url);
    await expect(
      page.getByRole("heading", { name: section.heading, level: 1 }),
    ).toBeVisible();
    // The current section is marked for screen readers and styled as active.
    await expect(
      nav.getByRole("link", { name: section.link, exact: true }),
    ).toHaveAttribute("aria-current", "page");
  }
});

test("dashboard overview shows real counts, labels sample data and shows progress", async ({
  page,
}) => {
  await page.goto("/dashboard");

  // Discover, Matches and Accommodation are real; messages are samples.
  await expect(page.getByText("0 matches")).toBeVisible();
  await expect(page.getByText(/(people|person) to discover/)).toBeVisible();
  await expect(page.getByText(/posts? to browse/)).toBeVisible();
  await expect(page.getByText("Sample data", { exact: true })).toHaveCount(1);
  await expect(page.getByText("Nothing new.")).toBeVisible();
  await expect(
    page.getByRole("progressbar", { name: "Profile completion" }),
  ).toHaveAttribute("aria-valuenow", "100");
  await expect(page.getByText("5 of 5 steps done")).toBeVisible();
});

test("profile menu opens, closes with Escape and links to the profile", async ({
  page,
}) => {
  await page.goto("/dashboard");
  const menuButton = page.getByRole("button", { name: /Account menu/ });

  await menuButton.click();
  await expect(page.getByRole("button", { name: "Log out" })).toBeVisible();

  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: "Log out" })).toBeHidden();
  await expect(menuButton).toBeFocused();

  await menuButton.click();
  await page.getByRole("link", { name: "Your profile", exact: true }).click();
  await expect(page).toHaveURL("/profile");
  await expect(
    page.getByRole("heading", { name: "Your profile", level: 1 }),
  ).toBeVisible();
  // The profile shown is the signed-in member's own, from the backend.
  await expect(
    page.getByRole("heading", { name: "Ananya Rao", level: 2 }),
  ).toBeVisible();
  // Nothing has been submitted, so nothing is shown as verified.
  await expect(page.getByText("Not submitted")).toHaveCount(2);
});

test("signed-in pages do not scroll sideways", async ({ page }) => {
  for (const url of ["/dashboard", "/discover", "/accommodation", "/profile"]) {
    await page.goto(url);
    const overflow = await page.evaluate(
      () =>
        document.documentElement.scrollWidth -
        document.documentElement.clientWidth,
    );
    expect(overflow, `${url} overflows horizontally`).toBe(0);
  }
});
