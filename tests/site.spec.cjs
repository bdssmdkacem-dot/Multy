const { test, expect } = require('@playwright/test');

test('marketing page loads with working in-page navigation and dashboard links', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/Multy/);
  await expect(page.getByRole('heading', { level: 1 })).toContainText('vision');
  await expect(page.locator('body')).toContainText('AU MAROC');
  await expect(page.locator('.dash')).toContainText('DH');
  await page.getByRole('link', { name: /Voir les fonctionnalités/i }).click();
  await expect(page).toHaveURL(/#fonctionnalites$/);
  await expect(page.locator('#fonctionnalites .feature')).toHaveCount(6);
  await page.getByRole('link', { name: /Ouvrir le tableau de bord/i }).click();
  await expect(page).toHaveURL(/app\.html$/);
  await expect(page.locator('#transactionRows tr')).toHaveCount(6);
});

test('marketing page has no horizontal overflow', async ({ page }) => {
  await page.goto('/');
  const metrics = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth
  }));
  expect(metrics.content).toBeLessThanOrEqual(metrics.viewport);
});

test('dashboard search filters rows and shows an empty state', async ({ page }) => {
  await page.goto('/app.html');
  const rows = page.locator('#transactionRows tr');
  await expect(rows).toHaveCount(6);
  await page.locator('#search').fill('Notion');
  await expect(page.locator('#transactionRows tr:visible')).toHaveCount(1);
  await expect(page.locator('#transactionRows tr:visible').first()).toContainText('Notion Labs');
  await page.locator('#search').fill('no-such-transaction');
  await expect(page.locator('#emptyState')).toBeVisible();
  await expect(page.locator('#transactionRows tr:visible')).toHaveCount(0);
});

test('dashboard period control updates demo figures', async ({ page }) => {
  await page.goto('/app.html');
  await page.locator('#period').selectOption('quarter');
  await expect(page.locator('#incomeMetric')).toContainText('52 780,00');
  await expect(page.locator('#toast')).toContainText('Période mise à jour');
});

test('dashboard can add a validated demo transaction', async ({ page }) => {
  await page.goto('/app.html');
  let dialogCount = 0;
  page.on('dialog', async dialog => {
    dialogCount += 1;
    await dialog.accept(dialogCount === 1 ? 'Browser test vendor' : '125,50');
  });
  await page.locator('#newBtn').click();
  await expect(page.locator('#transactionRows tr')).toHaveCount(7);
  await expect(page.locator('#transactionRows tr').first()).toContainText('Browser test vendor');
  expect(dialogCount).toBe(2);
});

test('dashboard exports filtered transactions to CSV', async ({ page }) => {
  await page.goto('/app.html');
  await page.locator('#search').fill('Notion');
  const downloadPromise = page.waitForEvent('download');
  await page.locator('#exportBtn').click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe('multy-transactions.csv');
});

test('mobile dashboard menu opens and closes after navigation', async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.startsWith('mobile'), 'Phone-specific menu check');
  await page.goto('/app.html');
  const toggle = page.locator('#menuToggle');
  await expect(toggle).toBeVisible();
  await toggle.click();
  await expect(page.locator('#sidebar')).toHaveClass(/open/);
  await page.locator('.nav button[data-page="Transactions"]').click();
  await expect(page.locator('#crumb')).toHaveText('Transactions');
  await expect(page.locator('#sidebar')).not.toHaveClass(/open/);
});

test('dashboard has no horizontal page overflow', async ({ page }) => {
  await page.goto('/app.html');
  const metrics = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth
  }));
  expect(metrics.content).toBeLessThanOrEqual(metrics.viewport);
});

test('Moroccan demo uses dirhams and clearly discloses demo status', async ({ page }) => {
  await page.goto('/app.html');
  await expect(page.locator('body')).toContainText('Montants fictifs en DH');
  await expect(page.locator('body')).not.toContainText('€');
  await page.locator('#newBtn').click();
  page.once('dialog', dialog => dialog.dismiss());
  await expect(page.locator('#toast')).toBeHidden();
});
