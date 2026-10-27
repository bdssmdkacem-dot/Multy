const { test, expect } = require('@playwright/test');

test('marketing page links to the dashboard and billing page', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/Multy/);
  await expect(page.getByRole('heading', { level: 1 })).toContainText('vision');
  await page.getByRole('link', { name: /Voir les fonctionnalit/i }).click();
  await expect(page).toHaveURL(/#fonctionnalites$/);
  await expect(page.locator('#fonctionnalites .feature')).toHaveCount(6);
  await page.getByRole('link', { name: /Ouvrir le tableau de bord/i }).click();
  await expect(page).toHaveURL(/app\.html$/);
  await expect(page.locator('#transactionRows tr')).toHaveCount(6);
  await page.getByRole('link', { name: /Facturation/ }).click();
  await expect(page).toHaveURL(/facturation\.html$/);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Facturation');
});

test('marketing page has no horizontal overflow', async ({ page }) => {
  await page.goto('/');
  const metrics = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, content: document.documentElement.scrollWidth }));
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
  expect(download.suggestedFilename()).toBe('multy-transactions-demo.csv');
});

test('mobile dashboard menu closes after navigation', async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.startsWith('mobile'), 'Phone-specific menu check');
  await page.goto('/app.html');
  await page.locator('#menuToggle').click();
  await expect(page.locator('#sidebar')).toHaveClass(/open/);
  await page.locator('.nav a[href="#transactions"]').click();
  await expect(page).toHaveURL(/app\.html#transactions$/);
  await expect(page.locator('#sidebar')).not.toHaveClass(/open/);
});

test('dashboard has no horizontal page overflow', async ({ page }) => {
  await page.goto('/app.html');
  const metrics = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, content: document.documentElement.scrollWidth }));
  expect(metrics.content).toBeLessThanOrEqual(metrics.viewport);
});

test('billing calculates totals and saves a local invoice draft', async ({ page }) => {
  await page.goto('/facturation.html');
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.getByRole('button', { name: /Nouvelle facture/ }).click();
  await page.locator('#clientName').fill('Client test');
  await page.locator('.line-description').fill('Conseil');
  await page.locator('.line-quantity').fill('2');
  await page.locator('.line-unit').fill('100');
  await expect(page.locator('#totalHt')).toContainText('200');
  await expect(page.locator('#totalVat')).toContainText('40');
  await expect(page.locator('#totalTtc')).toContainText('240');
  await page.getByRole('button', { name: 'Enregistrer le brouillon' }).click();
  await expect(page.locator('#invoiceRows tr')).toHaveCount(5);
  await expect(page.locator('#invoiceRows tr').first()).toContainText('Client test');
  await expect(page.locator('#invoiceRows tr').first()).toContainText('240');
  await expect(page.locator('#invoiceRows tr').first()).toContainText('Brouillon');
  await page.reload();
  await expect(page.locator('#invoiceRows tr')).toHaveCount(5);
  await expect(page.locator('#invoiceRows tr').first()).toContainText('Client test');
});

test('billing filters and searches the invoice list', async ({ page }) => {
  await page.goto('/facturation.html');
  await page.getByRole('tab', { name: 'Payées' }).click();
  await expect(page.locator('#invoiceRows tr')).toHaveCount(1);
  await expect(page.locator('#invoiceRows tr').first()).toContainText('Maison Créative');
  await page.locator('#invoiceSearch').fill('absent');
  await expect(page.locator('#emptyInvoices')).toBeVisible();
});

test('billing page fits the mobile viewport', async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.startsWith('mobile'), 'Phone-specific layout check');
  await page.goto('/facturation.html');
  const metrics = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, content: document.documentElement.scrollWidth }));
  expect(metrics.content).toBeLessThanOrEqual(metrics.viewport);
});
