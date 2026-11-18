import { test, expect } from '@playwright/test';

test.describe('configured isolated full-stack environment', () => {
  test.beforeEach(async ({ request }) => {
    if (process.env.RUN_FULL_STACK_E2E === 'true') {
      const response = await request.get('/api/v1/environment');
      expect(response.ok()).toBe(true);
      expect(await response.json()).toEqual({ environment: 'test', isolatedTesting: true });
    }
  });
  test.skip(
    process.env.RUN_FULL_STACK_E2E !== 'true',
    'Requires a running API and migrated/seeded isolated cloud test database. No SQLite or fixture fallback.',
  );
  test('registration, login, guest cart merge and forbidden administration', async ({ page }) => {
    const email = `e2e-${crypto.randomUUID()}@example.com`;
    const password = 'Isolated-e2e-password-123';
    await page.goto('/shop');
    await page
      .getByRole('button', { name: /Add .* to bag/ })
      .first()
      .click();
    await expect(page.getByRole('link', { name: /Shopping bag, [1-9]/ })).toBeVisible();
    await page.goto('/register');
    await page.getByLabel('Full name').fill('Automated Test Customer');
    await page.getByLabel('Email address').fill(email);
    await page.getByLabel('Password', { exact: true }).fill(password);
    await page.getByRole('button', { name: 'Create account', exact: true }).click();
    await expect(page.getByText('Account created.', { exact: false })).toBeVisible();
    await page.goto('/login');
    await page.getByLabel('Email address').fill(email);
    await page.getByLabel('Password', { exact: true }).fill(password);
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    await expect(
      page.getByRole('heading', { name: 'Welcome, Automated Test Customer.' }),
    ).toBeVisible();
    await page.goto('/cart');
    await expect(page.getByRole('link', { name: 'Continue to checkout' })).toBeVisible();
    await page.goto('/admin');
    await expect(
      page.getByRole('heading', { name: 'Administrator access required.' }),
    ).toBeVisible();
  });
  test('verified account prepares an idempotent pending-payment order', async ({ page }) => {
    const email = process.env.E2E_CUSTOMER_EMAIL,
      password = process.env.E2E_CUSTOMER_PASSWORD;
    if (!email || !password)
      throw new Error(
        'Configure a verified test customer in isolated test DB via the test-only fixture setup.',
      );
    await page.goto('/login');
    await page.getByLabel('Email address').fill(email);
    await page.getByLabel('Password', { exact: true }).fill(password);
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    await expect(page.getByRole('heading', { name: /Welcome,/ })).toBeVisible();
    await page.goto('/shop');
    await page
      .getByRole('button', { name: /Add .* to bag/ })
      .first()
      .click();
    await page.goto('/checkout');
    for (const [label, value] of [
      ['First name', 'Sample'],
      ['Last name', 'Customer'],
      ['Email address', email],
      ['Phone number', '0241234567'],
      ['Street address or GhanaPost GPS address', 'Automated test address'],
      ['City or town', 'Accra'],
    ])
      await page.getByLabel(label, { exact: true }).fill(value);
    await page.getByLabel('Region', { exact: true }).selectOption('Greater Accra');
    await page.getByRole('button', { name: 'Prepare pending-payment order' }).click();
    await expect(
      page.getByRole('heading', { name: 'Order prepared — pending payment.' }),
    ).toBeVisible();
    await page.getByRole('link', { name: 'View your orders' }).click();
    await expect(page.getByText('pending payment', { exact: true }).first()).toBeVisible();
  });
  test('admin sees stored records and protected management controls', async ({ page }) => {
    const email = process.env.E2E_ADMIN_EMAIL,
      password = process.env.E2E_ADMIN_PASSWORD;
    if (!email || !password) throw new Error('Configure isolated E2E admin fixture credentials.');
    await page.goto('/login');
    await page.getByLabel('Email address').fill(email);
    await page.getByLabel('Password', { exact: true }).fill(password);
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    await expect(page.getByRole('heading', { name: /Welcome,/ })).toBeVisible();
    await page.goto('/admin');
    await expect(page.getByText('Verified sales (pesewas)', { exact: true })).toBeVisible();
    await page.getByRole('link', { name: 'inventory', exact: true }).click();
    await expect(page.getByRole('table')).toBeVisible();
  });
});
