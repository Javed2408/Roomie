import type { APIRequestContext, Page } from "@playwright/test";
import { request as playwrightRequest } from "@playwright/test";

import {
  confirmEmail,
  discoverablePerson,
  expect,
  field,
  test,
  uniqueTag,
  until,
} from "./fixtures";
import { ADMIN_EMAIL, ADMIN_PASSWORD, API_URL, FRONTEND_URL } from "./settings";

/*
 * Real listings, end to end: a creator posts a room, adds evidence and a
 * photo and submits it; an administrator approves it through the API (the
 * admin screens arrive in Phase 8); a student finds it and expresses
 * interest; the creator accepts.
 */

// A real 1x1 PNG, so the backend's image checks accept it.
const PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
  "base64",
);
const PDF = Buffer.from(
  "%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n",
  "utf8",
);

/** A date `days` from today, as the date inputs expect it. */
function daysFromNow(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

async function startPost(page: Page, choice: RegExp, heading: string) {
  await page.goto("/accommodation/new");
  await until(
    () => page.getByRole("button", { name: choice }).click(),
    () =>
      expect(page.getByRole("heading", { name: heading })).toBeVisible({
        timeout: 1000,
      }),
  );
}

/** Fill in the "room available" form as a tenant and save the draft. */
async function createTenantListing(page: Page, title: string): Promise<string> {
  await startPost(page, /I have a room available/, "About the room");
  await field(page, "Title").fill(title);
  await field(page, "Your connection to the property").selectOption(
    "EXISTING_TENANT",
  );
  await page.getByRole("checkbox", { name: /Alpha Fixture Residency/ }).check();
  await field(page, "Rent per person (₹ / month)").fill("9000");
  await page.getByRole("radio", { name: "No brokerage" }).check();
  await field(page, "Bedrooms in the flat").fill("3");
  await field(page, "Bedrooms free").fill("1");
  await field(page, "People living there now").fill("2");
  await field(page, "Flatmates wanted").fill("1");
  await field(page, "Furnishing").selectOption("SEMI_FURNISHED");
  await field(page, "Available from").fill(daysFromNow(14));
  await page.getByRole("checkbox", { name: "Wi-Fi" }).check();
  await field(page, "Description").fill("Sunny room, quiet flatmates.");
  await page.getByRole("checkbox", { name: /I confirm I own/ }).check();
  await page.getByRole("button", { name: "Save draft" }).click();

  await expect(page).toHaveURL(/\/accommodation\/mine\/[\w-]+$/);
  await expect(
    page.getByRole("heading", { name: title, level: 1 }),
  ).toBeVisible();
  return page.url().split("/").at(-1) ?? "";
}

/** An API session signed in as the fixture administrator. */
async function adminApi(): Promise<{
  api: APIRequestContext;
  headers: Record<string, string>;
}> {
  const api = await playwrightRequest.newContext();
  const response = await api.post(`${API_URL}/auth/login`, {
    data: { email: ADMIN_EMAIL, password: ADMIN_PASSWORD },
    headers: { Origin: FRONTEND_URL },
  });
  expect(response.ok(), await response.text()).toBe(true);
  const { csrf_token } = (await response.json()) as { csrf_token: string };
  return { api, headers: { "X-CSRF-Token": csrf_token, Origin: FRONTEND_URL } };
}

/** Approve a tenant's evidence and then the listing, as a reviewer would. */
async function approveTenantListing(listingId: string): Promise<void> {
  const { api, headers } = await adminApi();
  const detail = (await (
    await api.get(`${API_URL}/admin/listings/${listingId}`)
  ).json()) as { authority_verification_id: string };
  const review = await api.post(
    `${API_URL}/admin/verifications/listing-authority/${detail.authority_verification_id}/review`,
    {
      data: {
        status: "APPROVED",
        tenant_permission_basis: "AGREEMENT_PERMITS_SHARING",
        rental_agreement_valid_until: daysFromNow(300),
      },
      headers,
    },
  );
  expect(review.ok(), await review.text()).toBe(true);
  const moderation = await api.post(
    `${API_URL}/admin/listings/${listingId}/moderation`,
    { data: { status: "APPROVED" }, headers },
  );
  expect(moderation.ok(), await moderation.text()).toBe(true);
  await api.dispose();
}

test.describe("listings", () => {
  test("the form requires brokerage, sensible rooms and the declaration", async ({
    page,
    member,
  }) => {
    await confirmEmail(page, member);
    await startPost(page, /I have a room available/, "About the room");

    await field(page, "Title").fill("Call 9876543210 for a room");
    await field(page, "Bedrooms in the flat").fill("2");
    await field(page, "Bedrooms free").fill("3");
    await page.getByRole("button", { name: "Save draft" }).click();

    await expect(
      page
        .getByText("Remove phone numbers and email addresses.")
        .filter({ visible: true }),
    ).toBeVisible();
    await expect(
      page
        .getByText("Say whether brokerage applies.")
        .filter({ visible: true }),
    ).toBeVisible();
    await expect(
      page
        .getByText("Cannot be more than the bedrooms.")
        .filter({ visible: true }),
    ).toBeVisible();
    await expect(
      page
        .getByText("Please confirm before continuing.")
        .filter({ visible: true }),
    ).toBeVisible();

    // A tenant cannot collect brokerage themselves.
    await field(page, "Your connection to the property").selectOption(
      "EXISTING_TENANT",
    );
    await page.getByRole("radio", { name: "Brokerage applies" }).check();
    await field(page, "Paid to").selectOption("LISTING_CREATOR");
    await page.getByRole("button", { name: "Save draft" }).click();
    await expect(
      page
        .getByText(/Only an authorised agent can collect brokerage/)
        .filter({ visible: true }),
    ).toBeVisible();
  });

  test("from draft to approved listing, interest and acceptance", async ({
    page,
    member,
    browser,
  }) => {
    test.slow();
    await confirmEmail(page, member);
    const title = `Room in a 3BHK ${uniqueTag()}`;
    const listingId = await createTenantListing(page, title);

    // A draft is private and cannot be submitted without evidence.
    await expect(
      page.getByText("Not public").filter({ visible: true }),
    ).toBeVisible();
    await expect(
      page
        .getByText("Upload your current rental agreement.")
        .filter({ visible: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Submit for review" }),
    ).toBeDisabled();

    // Evidence, then a photo.
    await field(page, "File").setInputFiles({
      name: "agreement.pdf",
      mimeType: "application/pdf",
      buffer: PDF,
    });
    await page.getByRole("button", { name: "Upload evidence" }).click();
    await expect(
      page.getByText(/Uploaded\. It stays private/).filter({ visible: true }),
    ).toBeVisible();
    await field(page, "Add a photo").setInputFiles({
      name: "room.png",
      mimeType: "image/png",
      buffer: PNG,
    });
    await page.getByRole("button", { name: "Upload photo" }).click();
    await expect(page.getByRole("img", { name: "Photo 1" })).toBeVisible();

    await page.getByRole("button", { name: "Submit for review" }).click();
    await expect(
      page
        .getByText(/Submitted\. You will get a notification/)
        .filter({ visible: true }),
    ).toBeVisible();
    await expect(
      page.getByText("Pending review").filter({ visible: true }).first(),
    ).toBeVisible();

    // Another student cannot see it until Roomie approves it.
    const student = await discoverablePerson(browser, `Kavya ${uniqueTag()}`);
    await student.page.goto(`/accommodation/${listingId}`);
    await expect(
      student.page.getByRole("heading", {
        name: "This listing is not available",
      }),
    ).toBeVisible();

    await approveTenantListing(listingId);

    // Now it is public, with honest badges.
    await student.page.goto("/accommodation");
    await student.page.getByRole("searchbox", { name: "Search" }).fill(title);
    await student.page.getByRole("link", { name: title }).click();
    await expect(student.page).toHaveURL(`/accommodation/${listingId}`);
    await expect(
      student.page.getByText("No brokerage").filter({ visible: true }),
    ).toBeVisible();
    await expect(
      student.page
        .getByText("Listing authority verified")
        .filter({ visible: true }),
    ).toBeVisible();
    await expect(
      student.page
        .getByText("Identity: not verified")
        .filter({ visible: true }),
    ).toBeVisible();

    await student.page.getByRole("button", { name: "I am interested" }).click();
    await expect(
      student.page.getByText(/Interest sent/).filter({ visible: true }),
    ).toBeVisible();

    // The creator sees the student and accepts.
    await page.reload();
    await expect(
      page
        .getByText("Visible to students", { exact: true })
        .filter({ visible: true }),
    ).toBeVisible();
    await page.getByRole("button", { name: /^Accept / }).click();
    await expect(
      page.getByText(/has been told/).filter({ visible: true }),
    ).toBeVisible();

    await student.page.goto("/accommodation/interests");
    await expect(
      student.page
        .getByText("Accepted", { exact: true })
        .filter({ visible: true }),
    ).toBeVisible();
    await student.close();
  });

  test("a rent-together post is a request, not a property", async ({
    page,
    member,
  }) => {
    await confirmEmail(page, member);
    await startPost(page, /find a place together/, "About your search");

    const title = `Two friends need a third ${uniqueTag()}`;
    await field(page, "Title").fill(title);
    await page.getByRole("checkbox", { name: /Beta Fixture Towers/ }).check();
    await field(page, "Budget per person (₹ / month)").fill("10000");
    await field(page, "Bedrooms wanted").fill("3");
    await field(page, "People in your group now").fill("2");
    await field(page, "More people needed").fill("1");
    await field(page, "Move-in date").fill(daysFromNow(30));
    await field(page, "Description").fill("Easygoing second-years.");
    await page.getByRole("button", { name: "Save draft" }).click();

    await expect(page).toHaveURL(/\/accommodation\/mine\/[\w-]+$/);
    await expect(
      page
        .getByText("It is not an available property.")
        .filter({ visible: true }),
    ).toBeVisible();
    // No evidence or photos: there is no property to prove.
    await expect(
      page.getByText("Evidence of listing authority").filter({ visible: true }),
    ).toHaveCount(0);
    await expect(
      page.getByText("Ready to submit").filter({ visible: true }),
    ).toBeVisible();

    // An unsubmitted draft can be deleted.
    await page.getByRole("button", { name: "Delete draft" }).click();
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "Delete draft" })
      .click();
    await expect(page).toHaveURL("/accommodation/mine");
    await expect(page.getByText(title).filter({ visible: true })).toHaveCount(
      0,
    );
  });

  test("a profile photo can be added and removed", async ({ page }) => {
    await page.goto("/profile");
    const add = page.getByRole("button", { name: "Add a photo" });
    await expect(add).toBeVisible();
    await page
      .locator('input[type="file"]')
      .setInputFiles({ name: "me.png", mimeType: "image/png", buffer: PNG });
    await expect(
      page.getByRole("button", { name: "Change photo" }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Remove" }).click();
    await expect(add).toBeVisible();
  });
});
