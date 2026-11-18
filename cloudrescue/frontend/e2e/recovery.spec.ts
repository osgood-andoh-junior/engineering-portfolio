import { expect, test, type Page } from "@playwright/test";

async function openOutage(page: Page) {
  await page.goto("/simulation");
  await page.getByLabel("Fault mode").selectOption("disconnect");
  await page.getByRole("button", { name: "Apply fault" }).click();
  await expect(page.getByRole("region", { name: "Fault controls" }).getByText("Down", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Recovery Center" }).click();
  const incident = page.getByRole("combobox", { name: "Incident", exact: true });
  await expect(incident.locator("option").filter({ hasText: "messaging" })).toHaveCount(1);
  await incident.selectOption({ label: (await incident.locator("option").filter({ hasText: "messaging" }).innerText()).trim() });
}

async function execute(page: Page, action: string) {
  await page.getByRole("combobox", { name: "Intervention", exact: true }).selectOption(action);
  await page.getByRole("button", { name: "Request intervention" }).click();
  const review = page.getByRole("button", { name: /Review approval/ }).first();
  await expect(review).toBeVisible();
  const id = (await review.innerText()).split("#")[1];
  await review.click();
  await page.getByRole("button", { name: "Confirm and execute #" + id }).click();
  return page.getByRole("row").filter({ hasText: new RegExp("#" + id + " ·") });
}

test("compare policies, verify a failed restart, then recover and audit", async ({ page }) => {
  const token = process.env.CLOUDRESCUE_E2E_ADMIN_TOKEN;
  test.skip(!token, "Requires the isolated local stack");
  await page.goto("/");
  await expect(page.getByText("Monitoring active")).toBeVisible();
  await page.goto("/simulation");
  await page.getByLabel("Development admin token").fill(token!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByText("Signed in for this browser session.")).toBeVisible();
  await page.getByRole("button", { name: "Apply fault" }).click();
  await expect(page.getByRole("region", { name: "Fault controls" }).getByText("Degraded", { exact: true })).toBeVisible();
  try {
    await openOutage(page);
    await page.getByRole("button", { name: "Review recommendation" }).click();
    await expect(page.getByRole("heading", { name: "Simulated failover" })).toBeVisible();
    await page.getByRole("link", { name: "Policy Lab" }).click();
    await page.getByRole("button", { name: "Run experiment" }).click();
    await expect(page.getByRole("heading", { name: "Modeled policy comparison" })).toBeVisible();
    await expect(page.getByRole("cell", { name: "No intervention", exact: true })).toBeVisible();
    await page.getByRole("link", { name: "Recovery Center" }).click();
    const incident = page.getByRole("combobox", { name: "Incident", exact: true });
    const option = incident.locator("option").filter({ hasText: "messaging" });
    await expect(option).toHaveCount(1);
    await incident.selectOption({ label: (await option.innerText()).trim() });
    const failed = await execute(page, "restart");
    await expect(failed.getByText("failed", { exact: true })).toBeVisible();
    const succeeded = await execute(page, "reset_fault");
    await expect(succeeded.getByText("succeeded", { exact: true })).toBeVisible();
    await expect(page.getByText("No active incidents.")).toBeVisible();
    await page.getByRole("link", { name: "Audit History" }).click();
    await expect(page.getByRole("cell", { name: /succeeded #/ }).first()).toBeVisible();
    await expect(page.getByRole("cell", { name: /failed #/ }).first()).toBeVisible();
    await page.getByRole("link", { name: "Reliability Analytics" }).click();
    await expect(page.getByRole("heading", { name: "Observed simulator reliability" })).toBeVisible();
  } finally {
    await page.goto("/simulation");
    await page.getByRole("button", { name: "Restore service" }).click();
    await expect(page.getByText("Fault mode updated to healthy.")).toBeVisible();
  }
});
