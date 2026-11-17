import { API_URL, FRONTEND_URL } from "./settings";
import {
  completeProfile,
  confirmEmail,
  decideAs,
  discoverablePerson,
  expect,
  test,
  uniqueTag,
} from "./fixtures";
import type { Page } from "@playwright/test";

/*
 * Discover, likes, passes and matches, with real accounts.
 *
 * Every test starts as a new member, "Ananya Rao", with a complete profile
 * (see fixtures.ts). Other people are created in browsers of their own.
 * Tests run in parallel and all their people share one test database, so
 * a test never assumes it knows everyone in the deck: it gives the people
 * it cares about unique names, and where order matters, a budget nobody
 * else has.
 */

/** A budget (min = max) that no other test will pick by chance. */
function uniqueBudget(): [number, number] {
  const amount = 20000 + Math.floor(Math.random() * 80000);
  return [amount, amount];
}

const isDiscoveryRequest = (url: URL) => url.pathname === "/api/v1/discovery";

/** Answer Discover's request ourselves, to show a particular state. */
async function answerDiscovery(
  page: Page,
  status: number,
  body: unknown,
): Promise<void> {
  await page.unroute(isDiscoveryRequest);
  await page.route(isDiscoveryRequest, (route) =>
    route.fulfill({
      status,
      json: body,
      // The API is on another port, so the browser checks these.
      headers: {
        "Access-Control-Allow-Origin": FRONTEND_URL,
        "Access-Control-Allow-Credentials": "true",
      },
    }),
  );
}

test("a mutual like makes one match that both people see", async ({
  page,
  member,
  browser,
}) => {
  await confirmEmail(page, member);
  const name = `Priya ${uniqueTag()}`;
  const priya = await discoverablePerson(browser, name);
  try {
    // Priya likes Ananya first. Ananya is not told.
    expect((await decideAs(priya, member, "like")).matched).toBe(false);

    await page.goto(`/students/${priya.member.id}`);
    await expect(page.getByRole("heading", { name, level: 1 })).toBeAttached();
    await expect(
      page.getByRole("heading", { name: "How this score was worked out" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: `Would you live with Priya?` }),
    ).toBeVisible();

    // Ananya likes Priya back: a match, straight away.
    await page.getByRole("button", { name: "Like", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "You matched with Priya" });
    await expect(dialog).toBeVisible();
    await dialog.getByRole("link", { name: "See your matches" }).click();

    await expect(page).toHaveURL("/matches");
    const match = page
      .getByRole("main")
      .getByRole("listitem")
      .filter({ hasText: name });
    await expect(match).toHaveCount(1);
    await expect(match.getByText("New match")).toBeVisible();
    await expect(match.getByText("100% compatibility")).toBeVisible();

    // Priya has a notification, and sees the same single match.
    await priya.page.goto("/dashboard");
    await expect(
      priya.page.getByText("You and Ananya liked each other."),
    ).toBeVisible();
    await priya.page.goto("/matches");
    await expect(
      priya.page.getByRole("heading", { name: "Ananya Rao", level: 2 }),
    ).toHaveCount(1);
  } finally {
    await priya.close();
  }
});

test("Discover shows the best match first and saves likes and passes", async ({
  page,
  member,
  browser,
}) => {
  await confirmEmail(page, member);
  const budget = uniqueBudget();
  await completeProfile(page, member, "Ananya Rao", { budget });
  const bestName = `Best ${uniqueTag()}`;
  const best = await discoverablePerson(browser, bestName, { budget });
  const other = await discoverablePerson(browser, `Other ${uniqueTag()}`);
  try {
    await page.goto("/discover");
    const card = page.getByTestId("discovery-card");

    // Same societies and the same budget: first in the deck.
    await expect(card.getByRole("heading", { name: bestName })).toBeVisible();
    await expect(card.getByText("Shares your societies")).toBeVisible();
    await expect(card.getByText("100% compatibility")).toBeVisible();

    await page.getByRole("button", { name: "Like", exact: true }).click();
    await expect(card.getByRole("heading", { name: bestName })).toHaveCount(0);

    // The next person is passed on by dragging the card to the left. (Other
    // tests' people share names, so they are told apart by profile link.)
    const nextLink = (await page
      .getByRole("link", { name: "View full profile" })
      .getAttribute("href"))!;
    // The next person's name is brought back into view after a decision.
    await expect(card.getByRole("heading").first()).toBeInViewport();
    // hover() waits until the card has stopped moving.
    await card.hover({ position: { x: 150, y: 60 } });
    const box = (await card.boundingBox())!;
    await page.mouse.down();
    await page.mouse.move(box.x + 150 - 220, box.y + 60, { steps: 12 });
    await page.mouse.up();
    await expect(page.locator(`a[href="${nextLink}"]`)).toHaveCount(0);

    // Both decisions were saved: neither person comes back.
    const response = await page.request.get(`${API_URL}/discovery?limit=50`);
    const remaining = (await response.json()) as {
      items: Array<{ student: { id: string } }>;
    };
    const ids = remaining.items.map((item) => item.student.id);
    expect(ids).not.toContain(best.member.id);
    expect(ids).not.toContain(nextLink.split("/").pop());
    await page.reload();
    await expect(page.getByRole("heading", { name: bestName })).toHaveCount(0);
  } finally {
    await best.close();
    await other.close();
  }
});

test("before confirming their email, a student can look but not like", async ({
  page,
  browser,
}) => {
  const other = await discoverablePerson(browser, `Someone ${uniqueTag()}`);
  try {
    await page.goto("/discover");

    await expect(
      page.getByText("Confirm your email address to like or pass."),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Like", exact: true }),
    ).toBeDisabled();
    await expect(
      page.getByRole("button", { name: "Pass", exact: true }),
    ).toBeDisabled();
  } finally {
    await other.close();
  }
});

test("Discover asks for a finished profile first", async ({ page, member }) => {
  // Clearing the budget and move-in date makes the profile incomplete.
  const response = await page.request.put(`${API_URL}/me/preferences`, {
    data: {},
    headers: member.headers,
  });
  expect(response.ok()).toBe(true);

  await page.goto("/discover");

  await expect(
    page.getByRole("heading", { name: "Finish your profile first" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Finish your profile" }).click();
  await expect(page).toHaveURL("/onboarding");
});

test("Discover explains an empty deck and a failed load", async ({ page }) => {
  await answerDiscovery(page, 200, {
    items: [],
    next_cursor: null,
    remaining: 0,
  });
  await page.goto("/discover");
  await expect(
    page.getByRole("heading", { name: "You're all caught up" }),
  ).toBeVisible();

  await answerDiscovery(page, 500, {
    error: { code: "internal_error", message: "Roomie is having a moment." },
  });
  await page.getByRole("button", { name: "Check again" }).click();
  await expect(
    page.getByRole("heading", { name: "Discover could not load" }),
  ).toBeVisible();
  await expect(page.getByText("Roomie is having a moment.")).toBeVisible();

  // Once the backend answers properly again, "Try again" recovers.
  await page.unroute(isDiscoveryRequest);
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(
    page.getByRole("heading", { name: "Discover could not load" }),
  ).toHaveCount(0);
});

test("a profile that cannot be seen says so", async ({ page }) => {
  for (const id of ["00000000-0000-0000-0000-000000000000", "nobody"]) {
    await page.goto(`/students/${id}`);
    await expect(
      page.getByRole("heading", { name: "This profile is not available" }),
    ).toBeVisible();
  }
});
