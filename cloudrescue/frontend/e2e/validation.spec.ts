import { expect, test } from "@playwright/test";

test("run held-out benchmark and verify audit chain", async ({ page }) => {
  const token = process.env.CLOUDRESCUE_E2E_ADMIN_TOKEN;
  test.skip(!token, "Requires isolated local stack");
  await page.goto("/simulation");
  await page.getByLabel("Development admin token").fill(token!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByText("Signed in for this browser session.")).toBeVisible();
  await page.getByRole("link", { name: "Benchmark Lab" }).click();
  await page.getByRole("button", { name: "Run benchmark" }).click();
  await expect(page.getByRole("heading", { name: "Held-out performance" })).toBeVisible();
  await expect(page.getByText("240 trials · seed 42")).toBeVisible();
  if (process.env.CLOUDRESCUE_CAPTURE_DIR) {
    await page.screenshot({ path: process.env.CLOUDRESCUE_CAPTURE_DIR + "/benchmark-lab.png", fullPage: true });
  }
  const csv = await page.request.get(await page.getByRole("link", { name: "Export CSV" }).getAttribute("href") ?? "");
  expect(csv.ok()).toBeTruthy();
  expect(await csv.text()).toContain("paired_success_delta");
  await page.getByRole("link", { name: "Audit Verification" }).click();
  await page.getByRole("button", { name: "Verify integrity" }).click();
  await expect(page.getByText("Chain links verified.")).toBeVisible();
  await page.getByRole("link", { name: "Security Administration" }).click();
  await expect(page.getByRole("heading", { name: "Authorization events" })).toBeVisible();
});
