import { expect, test } from "@playwright/test";

test("dashboard renders collected health checks", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  await expect(page.getByText("Monitoring active")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Response latency" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Request error rate" })).toBeVisible();
  await expect(page.locator(".recharts-surface").first()).toBeVisible();
  await page.getByRole("link", { name: "Services", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Identity Service" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Storage Service" })).toBeVisible();
});

test("an authenticated operator degrades, disconnects and recovers Messaging", async ({ page }) => {
  const token = process.env.CLOUDRESCUE_E2E_ADMIN_TOKEN;
  test.skip(!token, "Provide an admin token and use an isolated local stack");
  const denied = await page.request.put("/api/cloud/services/messaging/fault", {
    headers: {
      Origin: new URL(test.info().project.use.baseURL!).origin,
      "x-cloudrescue-action": "fault",
    },
    data: { mode: "disconnect" },
  });
  expect(denied.status()).toBe(401);
  await page.goto("/simulation");
  await expect(page.getByRole("button", { name: "Apply fault" })).toBeDisabled();
  await page.getByLabel("Development admin token").fill(token!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByText("Signed in for this browser session.")).toBeVisible();
  const controls = page.getByRole("region", { name: "Fault controls" });
  await expect(controls.getByText("Healthy", { exact: true })).toBeVisible();
  let incidentButton = "";
  try {
    await page.getByRole("button", { name: "Apply fault" }).click();
    await expect(controls.getByText("Degraded", { exact: true })).toBeVisible();
    await page.getByLabel("Fault mode").selectOption("disconnect");
    await page.getByRole("button", { name: "Apply fault" }).click();
    await expect(controls.getByText("Down", { exact: true })).toBeVisible();
    await page.getByRole("link", { name: "Incidents", exact: true }).click();
    const open = page.getByRole("row").filter({ hasText: "messaging" }).filter({ hasText: "Open" });
    await expect(open).toHaveCount(1);
    incidentButton = await open.getByRole("button").innerText();
  } finally {
    await page.goto("/simulation");
    await page.getByRole("button", { name: "Restore service" }).click();
    await expect(controls.getByText("Healthy", { exact: true })).toBeVisible();
  }
  await page.getByRole("link", { name: "Incidents", exact: true }).click();
  await page.getByRole("button", { name: incidentButton, exact: true }).click();
  await expect(page.getByText("Recovery confirmed")).toBeVisible();
  await expect(page.getByText("Detection delay")).toBeVisible();
});
