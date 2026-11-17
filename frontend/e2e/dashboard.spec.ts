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

  // Discover and Matches are real; accommodation and messages are samples.
  await expect(page.getByText("0 matches")).toBeVisible();
  await expect(page.getByText(/(people|person) to discover/)).toBeVisible();
  await expect(page.getByText("Sample data", { exact: true })).toHaveCount(2);
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

test("accommodation keeps the two listing types clearly apart", async ({
  page,
}) => {
  await page.goto("/accommodation");
  const listings = page.getByRole("main").getByRole("listitem");

  await expect(listings).toHaveCount(3);
  // Brokerage is stated on every property, including when there is none.
  await expect(page.getByText("No brokerage")).toBeVisible();
  await expect(page.getByText("Brokerage: ₹8,000")).toBeVisible();
  // Nothing has been verified, so nothing may say it has.
  await expect(page.getByText(/authority verified/i)).toHaveCount(0);
  await expect(page.getByText("Listing authority: not verified")).toHaveCount(
    2,
  );

  await page.getByRole("button", { name: "Looking to rent together" }).click();
  await expect(listings).toHaveCount(1);
  await expect(
    page.getByText("It is not an available property."),
  ).toBeVisible();

  await page.getByRole("button", { name: "Rooms available" }).click();
  await expect(listings).toHaveCount(2);
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
