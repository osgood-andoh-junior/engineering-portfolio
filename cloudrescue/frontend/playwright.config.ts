import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  timeout: 180_000,
  expect: { timeout: 60_000 },
  use: {
    baseURL: process.env.CLOUDRESCUE_E2E_URL || "http://127.0.0.1:3000",
    trace: "off",
    channel: process.env.CLOUDRESCUE_BROWSER_CHANNEL || undefined,
  },
});
