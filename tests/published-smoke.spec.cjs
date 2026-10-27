const { test, expect } = require('@playwright/test');
const expectedFeatureCount = Number(process.env.PLAYWRIGHT_EXPECT_FEATURES || 7);

test('published marketing page loads and dashboard entry point works', async ({ page }) => {
  const response = await page.goto('./');
  expect(response && response.ok()).toBeTruthy();
  await expect(page).toHaveTitle(/Multy/);
  await expect(page.getByRole('heading', { level: 1 })).toContainText('vision');
  await expect(page.locator('#fonctionnalites .feature')).toHaveCount(expectedFeatureCount);
  await page.getByRole('link', { name: /Explorer le tableau de bord/i }).click();
  await expect(page).toHaveURL(/app\.html$/);
  await expect(page.locator('#transactionRows tr')).toHaveCount(6);
});

test('published dashboard search and period controls are interactive', async ({ page }) => {
  await page.goto('./app.html');
  const rows = page.locator('#transactionRows tr');
  await expect(rows).toHaveCount(6);
  await page.locator('#search').fill('Notion');
  await expect(page.locator('#transactionRows tr:visible')).toHaveCount(1);
  await expect(page.locator('#transactionRows tr:visible').first()).toContainText('Notion Labs');
  await page.locator('#search').fill('');
  await page.locator('#period').selectOption('quarter');
  await expect(page.locator('#incomeMetric')).toContainText('52 780,00');
  await expect(page.locator('#toast')).toContainText('Période mise à jour');
});

test('published dashboard fits mobile width and its menu works on phones', async ({ page }, testInfo) => {
  await page.goto('./app.html');
  const metrics = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth
  }));
  expect(metrics.content).toBeLessThanOrEqual(metrics.viewport);
  if (testInfo.project.name.startsWith('mobile')) {
    const toggle = page.locator('#menuToggle');
    await expect(toggle).toBeVisible();
    await toggle.click();
    await expect(page.locator('#sidebar')).toHaveClass(/open/);
    await page.locator('.nav button[data-page="Transactions"]').click();
    await expect(page.locator('#crumb')).toContainText('Transactions');
    await expect(page.locator('#sidebar')).not.toHaveClass(/open/);
  }
});

test('published release matches Moroccan market and discloses demo currency', async ({ page }, testInfo) => {
  await page.goto('./app.html');
  if (testInfo.project.name.startsWith('mobile')) {
    await page.goto('./');
    await expect(page.locator('#marketingMenuToggle')).toBeVisible();
    await page.goto('./app.html');
  }
  await expect(page.locator('body')).toContainText('Montants fictifs en DH');
  await expect(page.locator('body')).not.toContainText('€');
});


test('published authentication page and public Supabase configuration load', async ({ page }) => {
  const authResponse = await page.goto('./auth.html');
  expect(authResponse && authResponse.status()).toBe(200);
  await expect(page).toHaveTitle(/Compte Multy/);
  await expect(page.getByRole('heading', { name: 'Créer votre compte' })).toBeVisible();
  await expect(page.locator('#email')).toBeVisible();
  await expect(page.locator('#password')).toBeVisible();
  const configResponse = await page.request.get('./supabase-config.js');
  expect(configResponse.status()).toBe(200);
  const configText = await configResponse.text();
  expect(configText).toContain('window.MULTY_SUPABASE_CONFIG');
  expect(configText).toContain('https://abxapmbiuijaybwddvrw.supabase.co');
  expect(configText).toContain('sb_publishable_');
  const configuredKey = configText.match(/publishableKey:\s*[\"']([^\"']+)[\"']/i)?.[1] ?? '';
  expect(configuredKey).toMatch(/^sb_publishable_/);
  expect(configuredKey).not.toMatch(/service_role|sb_secret/i);
  await page.reload();
  const config = await page.evaluate(() => window.MULTY_SUPABASE_CONFIG);
  expect(config && config.url).toBe('https://abxapmbiuijaybwddvrw.supabase.co');
  expect(config && config.publishableKey).toMatch(/^sb_publishable_/);
});
