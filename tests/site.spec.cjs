const { test, expect } = require('@playwright/test');

test('marketing page loads with working in-page navigation and dashboard links', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/Multy/);
  await expect(page.getByRole('heading', { level: 1 })).toContainText('vision');
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

test('invoice draft page keeps client-side HT, tax, and TTC previews in sync', async ({ page }, testInfo) => {
  await page.route('**/supabase-config.js', route => route.fulfill({
    contentType: 'application/javascript',
    body: 'window.MULTY_SUPABASE_CONFIG = {};'
  }));
  await page.goto('./facturation.html');
  await expect(page.getByRole('heading', { level: 1, name: 'Facturation' })).toBeVisible();
  await expect(page.locator('#setupGate')).toBeVisible();
  // This UI-only test bypasses the authentication overlay; it does not submit live data.
  await page.locator('#setupGate').evaluate(el => { el.hidden = true; });
  await page.locator('.line .desc').fill('Prestation de test');
  await page.locator('.line .qty').fill('2');
  await page.locator('.line .price').fill('50');
  await page.locator('.line .rate').fill('10');
  await expect(page.locator('#subtotal')).toContainText('100,00');
  await expect(page.locator('#taxTotal')).toContainText('10,00');
  await expect(page.locator('#grandTotal')).toContainText('110,00');
  await page.locator('#addLine').click();
  await expect(page.locator('#lineRows .line')).toHaveCount(2);
  await page.locator('#lineRows .line').nth(1).getByRole('button', { name: 'Supprimer la ligne' }).click();
  await expect(page.locator('#lineRows .line')).toHaveCount(1);
  const width = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, content: document.documentElement.scrollWidth }));
  expect(width.content).toBeLessThanOrEqual(width.viewport);
});

test('expense entry page renders its fields and fits mobile width', async ({ page }) => {
  await page.route('**/supabase-config.js', route => route.fulfill({
    contentType: 'application/javascript',
    body: 'window.MULTY_SUPABASE_CONFIG = {};'
  }));
  await page.goto('./depenses.html');
  await expect(page.getByRole('heading', { level: 1, name: 'Suivi des dépenses' })).toBeVisible();
  await expect(page.locator('#gate')).toBeVisible();
  await expect(page.locator('#vendor')).toBeVisible();
  await expect(page.locator('#description')).toBeVisible();
  await expect(page.locator('#category')).toBeVisible();
  await expect(page.locator('#date')).toBeVisible();
  await expect(page.locator('#amount')).toBeVisible();
  const width = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, content: document.documentElement.scrollWidth }));
  expect(width.content).toBeLessThanOrEqual(width.viewport);
});
