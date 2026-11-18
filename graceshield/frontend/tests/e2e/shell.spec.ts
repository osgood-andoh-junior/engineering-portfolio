import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('storefront navigation, FAQ and unknown information route', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('brighter');
  await page.getByRole('link', { name: 'Frequently asked questions' }).click();
  await page.getByText('Will my shopping bag be saved?', { exact: true }).click();
  await expect(
    page.getByText('Your bag is stored in the configured database', { exact: false }),
  ).toBeVisible();
  const response = await page.goto('/not-a-real-page');
  expect(response?.status()).toBe(404);
  await expect(page.getByRole('heading', { name: 'This chapter is missing.' })).toBeVisible();
});
test('invalid login fields are rejected before transport', async ({ page }) => {
  await page.goto('/login');
  const submitted: string[] = [];
  page.on('request', (r) => {
    if (r.method() === 'POST') submitted.push(r.url());
  });
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByText('Enter a valid email address.')).toBeVisible();
  expect(submitted).toEqual([]);
});
test('keyboard access and mobile navigation focus return', async ({ page }, info) => {
  await page.goto('/');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Skip to content' })).toBeFocused();
  if (info.project.name === 'mobile') {
    await page.getByRole('button', { name: 'Open navigation' }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(page.getByRole('button', { name: 'Open navigation' })).toBeFocused();
  }
});
test('unauthenticated account/admin gates and unavailable-service states are accessible', async ({
  page,
}) => {
  test.setTimeout(90000);
  for (const route of ['/', '/login', '/register', '/faq', '/cart', '/account', '/admin']) {
    await page.goto(route);
    await page.getByRole('heading', { level: 1 }).waitFor();
    if (route === '/admin')
      await expect(
        page.getByRole('heading', { name: 'Administrator access required.' }),
      ).toBeVisible();
    const audit = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
      .analyze();
    expect(audit.violations).toEqual([]);
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    ).toBe(true);
  }
});
