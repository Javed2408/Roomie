import fs from "node:fs";
import path from "node:path";

import {
  test as base,
  expect,
  type Browser,
  type Locator,
  type Page,
} from "@playwright/test";

import { API_URL, FRONTEND_URL, OUTBOX_DIR } from "./settings";

export { expect };

export const PASSWORD = "roomie2027";

/** A short random tag, to make names unique between parallel tests. */
export function uniqueTag(): string {
  return Math.random().toString(36).slice(2, 7);
}

/** A fresh address every time, so tests never collide with each other. */
export function uniqueEmail(): string {
  const random = Math.random().toString(36).slice(2, 8);
  return `e2e-${Date.now()}-${random}@example.com`;
}

/** A form field by its label, ignoring pages Next.js keeps hidden. */
export function field(page: Page, label: string | RegExp): Locator {
  return page.getByLabel(label, { exact: true }).filter({ visible: true });
}

/**
 * Do something, then check it worked, retrying both until it does.
 *
 * Right after a page loads there is a short gap before its buttons are
 * wired up. A click in that gap does nothing, so the first interaction on
 * a page is retried rather than assumed to land.
 */
export async function until(
  action: () => Promise<void>,
  check: () => Promise<void>,
): Promise<void> {
  await expect(async () => {
    await action();
    await check();
  }).toPass({ timeout: 15_000, intervals: [250, 500, 1000] });
}

export interface Member {
  id: string;
  email: string;
  /** Headers for making changes through the API as this member. */
  headers: Record<string, string>;
}

/**
 * Create an account straight through the API (much faster than filling in
 * the form) and leave the browser signed in as that person. The session
 * cookie lands in the browser because `page.request` shares its cookies.
 */
export async function registerMember(page: Page): Promise<Member> {
  const email = uniqueEmail();
  const response = await page.request.post(`${API_URL}/auth/register`, {
    data: { email, password: PASSWORD, accepted_terms: true },
    headers: { Origin: FRONTEND_URL },
  });
  expect(response.status(), await response.text()).toBe(201);
  const body = (await response.json()) as {
    csrf_token: string;
    user: { id: string };
  };
  return {
    id: body.user.id,
    email,
    headers: { "X-CSRF-Token": body.csrf_token, Origin: FRONTEND_URL },
  };
}

interface ProfileOptions {
  /** Monthly budget; the default is ₹8,000 to ₹12,000. */
  budget?: [number, number];
}

/** Give a member a complete, published profile through the API. */
export async function completeProfile(
  page: Page,
  member: Member,
  fullName = "Ananya Rao",
  { budget = [8000, 12000] }: ProfileOptions = {},
): Promise<void> {
  const societies = (await (
    await page.request.get(`${API_URL}/societies`)
  ).json()) as Array<{ id: string }>;
  const steps: Array<[string, "put" | "post", unknown]> = [
    [
      "/me/profile",
      "put",
      {
        full_name: fullName,
        college_name: "SRM IST, Kattankulathur",
        course: "B.Tech",
        department: "Computer Science",
        academic_year: 2,
        bio: "Second-year CS student. Tidy, friendly and a night owl.",
      },
    ],
    [
      "/me/preferences",
      "put",
      {
        min_budget: budget[0],
        max_budget: budget[1],
        move_in_date: "2027-01-05",
        room_type: "PRIVATE_ROOM",
        food_preference: "VEGETARIAN",
        sleep_schedule: "NIGHT_OWL",
      },
    ],
    [
      "/me/societies",
      "put",
      { society_ids: societies.slice(0, 2).map((society) => society.id) },
    ],
    ["/me/profile/publish", "post", undefined],
  ];
  for (const [url, method, data] of steps) {
    const response = await page.request[method](`${API_URL}${url}`, {
      data,
      headers: member.headers,
    });
    expect(response.ok(), `${url}: ${await response.text()}`).toBe(true);
  }
}

/**
 * Find the secret link in the newest email "sent" to an address.
 *
 * The test backend does not send email: it writes each one to a file. A
 * real person would click the link in their inbox; the test reads it here.
 */
export async function emailedLink(
  email: string,
  pathPrefix: string,
): Promise<string> {
  let link: string | undefined;
  await expect(async () => {
    const files = fs.existsSync(OUTBOX_DIR)
      ? fs.readdirSync(OUTBOX_DIR).filter((name) => name.includes(email))
      : [];
    const bodies = files
      .sort()
      .reverse()
      .map((name) => fs.readFileSync(path.join(OUTBOX_DIR, name), "utf8"));
    const match = bodies
      .map((body) => body.match(new RegExp(`${pathPrefix}\\?token=[\\w-]+`)))
      .find(Boolean);
    expect(match, `no ${pathPrefix} email for ${email} yet`).toBeTruthy();
    link = match?.[0];
  }).toPass({ timeout: 10_000 });
  return link ?? "";
}

/**
 * Confirm a member's email address, as clicking the emailed link would.
 * Until then they cannot like or pass, and nobody can discover them.
 */
export async function confirmEmail(page: Page, member: Member): Promise<void> {
  const link = await emailedLink(member.email, "/verify-email");
  const token = new URL(link, FRONTEND_URL).searchParams.get("token");
  const response = await page.request.post(`${API_URL}/auth/verify-email`, {
    data: { token },
    headers: member.headers,
  });
  expect(response.ok(), await response.text()).toBe(true);
}

/** A second person, in a browser of their own, ready to be discovered. */
export interface OtherPerson {
  member: Member;
  page: Page;
  close: () => Promise<void>;
}

export async function discoverablePerson(
  browser: Browser,
  fullName: string,
  options: ProfileOptions = {},
): Promise<OtherPerson> {
  const context = await browser.newContext();
  const page = await context.newPage();
  const member = await registerMember(page);
  await completeProfile(page, member, fullName, options);
  await confirmEmail(page, member);
  return { member, page, close: () => context.close() };
}

/** Like or pass on someone through the API, as `person`. */
export async function decideAs(
  person: OtherPerson,
  target: Member,
  decision: "like" | "pass",
): Promise<{ matched: boolean }> {
  const response = await person.page.request.post(
    `${API_URL}/discovery/${target.id}/${decision}`,
    { headers: person.member.headers },
  );
  expect(response.ok(), await response.text()).toBe(true);
  return (await response.json()) as { matched: boolean };
}

/**
 * `test` for pages that need a signed-in person. Before each test it
 * creates a brand-new member with a complete profile and signs the
 * browser in as them, so every test starts from the same known state.
 */
export const test = base.extend<{ member: Member }>({
  member: [
    async ({ page }, use) => {
      const member = await registerMember(page);
      await completeProfile(page, member);
      await use(member);
    },
    { auto: true },
  ],
});
