import {defineConfig} from '@playwright/test';

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:3000';

export default defineConfig({
  testDir: './e2e',
  use: {baseURL, channel: process.env.PLAYWRIGHT_BROWSER_CHANNEL},
  webServer: {command: 'npm run dev', url: baseURL, reuseExistingServer: true},
  workers: 1,
});
