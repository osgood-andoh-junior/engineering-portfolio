import { expect, test } from "@playwright/test";

test("published topology, live cascade diagnosis, and saved replay", async ({ page }) => {
  const token = process.env.CLOUDRESCUE_E2E_ADMIN_TOKEN;
  test.skip(!token, "Requires the isolated local stack");
  await page.goto("/simulation");
  await page.getByLabel("Development admin token").fill(token!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByText("Signed in for this browser session.")).toBeVisible();
  await page.getByRole("link", { name: "Service Dependencies" }).click();
  await expect(page.getByRole("img", { name: /messaging depends on identity/ })).toBeVisible();
  const edge = page.getByRole("checkbox", { name: "storage depends on identity", exact: true });
  await edge.uncheck();
  await page.getByRole("button", { name: "Publish dependencies" }).click();
  await expect(page.getByRole("img")).not.toHaveAttribute("aria-label", /storage depends on identity/);
  await edge.check();
  await page.getByRole("button", { name: "Publish dependencies" }).click();
  await expect(page.getByRole("img", { name: /storage depends on identity/ })).toBeVisible();

  await page.getByRole("link", { name: "Fault Simulation" }).click();
  await page.getByRole("combobox", { name: "Service", exact: true }).selectOption("identity", { timeout: 10000 });
  await page.getByRole("combobox", { name: /Fault mode/ }).selectOption("disconnect", { timeout: 10000 });
  await page.getByRole("button", { name: "Apply fault" }).click();
  let id = "";
  try {
    await expect(page.getByText("Fault mode updated to connection failure.")).toBeVisible();
    await page.getByRole("link", { name: "Incidents", exact: true }).click();
    const symptom = page.getByRole("row").filter({ hasText: "messaging" }).filter({ hasText: "Open" });
    const button = symptom.getByRole("button");
    await expect(button).toBeVisible();
    id = (await button.innerText()).split("#")[1];
    await button.click();
    await expect(page.getByRole("heading", { name: /identity · 95% rule confidence/ })).toBeVisible();
    await expect(page.getByText(/Recorded fault injections at onset/)).toBeVisible();
  } finally {
    await page.goto("/simulation");
    await page.getByLabel("Service", { exact: true }).selectOption("identity");
    await page.getByRole("button", { name: "Restore service" }).click();
    await expect(page.getByText("Fault mode updated to healthy.")).toBeVisible();
  }
  await page.getByRole("link", { name: "Incident Replay" }).click();
  await expect(page.getByRole("option", { name: "Recorded incident", exact: true })).toBeAttached();
  await page.getByLabel("Scenario", { exact: true }).selectOption("incident");
  await page.getByLabel("Incident ID").fill(id);
  await page.getByRole("button", { name: "Save replay" }).click();
  await expect(page.getByRole("heading", { name: "Recorded incident #" + id })).toBeVisible();
  await expect(page.getByText(/Predicted across replay · identity/)).toBeVisible();
  await page.getByRole("button", { name: "Next frame" }).click();
  await expect(page.getByText(/Frame 2 of/)).toBeVisible();
  await page.getByRole("link", { name: "Diagnostic Evaluation" }).click();
  await expect(page.getByText("100% (5/5)")).toBeVisible();
});
