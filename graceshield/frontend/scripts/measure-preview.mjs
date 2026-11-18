import { chromium, devices } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
const browser = await chromium.launch();
const context = await browser.newContext({
  ...devices['iPhone 13'],
  defaultBrowserType: undefined,
});
const page = await context.newPage();
await page.addInitScript(() => {
  window.previewMetrics = { lcpMs: null, cls: 0 };
  new PerformanceObserver((list) => {
    const entries = list.getEntries();
    window.previewMetrics.lcpMs = entries.at(-1).startTime;
  }).observe({ type: 'largest-contentful-paint', buffered: true });
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (!entry.hadRecentInput) window.previewMetrics.cls += entry.value;
    }
  }).observe({ type: 'layout-shift', buffered: true });
});
const session = await context.newCDPSession(page);
await session.send('Network.enable');
await session.send('Network.emulateNetworkConditions', {
  offline: false,
  latency: 150,
  downloadThroughput: 200000,
  uploadThroughput: 93750,
});
await session.send('Emulation.setCPUThrottlingRate', { rate: 4 });
await page.goto('http://127.0.0.1:3000', { waitUntil: 'networkidle' });
await page.evaluate(() => document.fonts.ready);
const metrics = await page.evaluate(() => ({
  ...window.previewMetrics,
  paint: performance
    .getEntriesByType('paint')
    .map((e) => ({ name: e.name, ms: Math.round(e.startTime) })),
  resources: performance
    .getEntriesByType('resource')
    .map((e) => ({ name: new URL(e.name).pathname, bytes: e.transferSize, kind: e.initiatorType })),
  navigation: {
    domContentLoadedMs: Math.round(
      performance.getEntriesByType('navigation')[0].domContentLoadedEventEnd,
    ),
  },
}));
metrics.conditions =
  'One cold local Chromium run; iPhone 13 viewport, 4x CPU throttle, 150ms latency, 1.6Mbps download. No field INP measurement.';
mkdirSync('test-results', { recursive: true });
writeFileSync('test-results/performance.json', JSON.stringify(metrics, null, 2));
console.log(
  JSON.stringify(
    {
      conditions: metrics.conditions,
      lcpMs: Math.round(metrics.lcpMs),
      cls: metrics.cls,
      paint: metrics.paint,
      resourceBytes: metrics.resources.reduce((n, r) => n + r.bytes, 0),
      ...metrics.navigation,
    },
    null,
    2,
  ),
);
await browser.close();
