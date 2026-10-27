const { test, expect } = require('@playwright/test');

test('marketing page loads with working in-page navigation and dashboard links', async ({ page }, testInfo) => {
  await page.goto('./');
  await expect(page).toHaveTitle(/Multy/);
  await expect(page.getByRole('heading', { level: 1 })).toContainText('vision');
  await expect(page.locator('body')).toContainText('AU MAROC');
  await expect(page.locator('.dash')).toContainText('DH');
  await page.getByRole('link', { name: /Voir les fonctionnalités/i }).click();
  await expect(page).toHaveURL(/#fonctionnalites$/);
  await expect(page.locator('#fonctionnalites .feature')).toHaveCount(7);
  await expect(page.locator('#fonctionnalites')).toContainText('cabinets comptables');
  await page.getByRole('link', { name: /Ouvrir le tableau de bord/i }).click();
  await expect(page).toHaveURL(/app\.html$/);
  await expect(page.locator('#transactionRows tr')).toHaveCount(6);
  await expect(page.locator('#invoiceMetric')).toContainText('3 740,00 DH');
  if (testInfo.project.name.startsWith('mobile')) await page.locator('#menuToggle').click();
  await page.locator('.nav button[data-page="Facturation"]').click();
  await expect(page).toHaveURL(/facturation\.html$/);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Facturation');
});

test('marketing navigation opens and closes accessibly on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('./');
  const toggle = page.locator('#marketingMenuToggle');
  const nav = page.locator('#marketingNav');
  await expect(toggle).toBeVisible();
  await expect(toggle).toHaveAttribute('aria-controls', 'marketingNav');
  await expect(toggle).toHaveAttribute('aria-expanded', 'false');
  await expect(nav).not.toBeVisible();
  await toggle.click();
  await expect(toggle).toHaveAttribute('aria-expanded', 'true');
  await expect(nav).toBeVisible();
  await nav.getByRole('link', { name: 'Fonctionnalités' }).click();
  await expect(page).toHaveURL(/#fonctionnalites$/);
  await expect(toggle).toHaveAttribute('aria-expanded', 'false');
  await expect(nav).not.toBeVisible();
});

test('marketing page has no horizontal overflow', async ({ page }) => {
  await page.goto('./');
  const metrics = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth
  }));
  expect(metrics.content).toBeLessThanOrEqual(metrics.viewport);
});

test('dashboard search filters rows and shows an empty state', async ({ page }) => {
  await page.goto('./app.html');
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
  await page.goto('./app.html');
  await page.locator('#period').selectOption('quarter');
  await expect(page.locator('#incomeMetric')).toContainText('52 780,00');
  await expect(page.locator('#toast')).toContainText('Période mise à jour');
});

test('dashboard can add a validated demo transaction', async ({ page }) => {
  await page.goto('./app.html');
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
  await page.goto('./app.html');
  await page.locator('#search').fill('Notion');
  const downloadPromise = page.waitForEvent('download');
  await page.locator('#exportBtn').click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe('multy-transactions.csv');
});

test('mobile dashboard menu opens and closes after navigation', async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.startsWith('mobile'), 'Phone-specific menu check');
  await page.goto('./app.html');
  const toggle = page.locator('#menuToggle');
  await expect(toggle).toBeVisible();
  await toggle.click();
  await expect(page.locator('#sidebar')).toHaveClass(/open/);
  await page.locator('.nav button[data-page="Transactions"]').click();
  await expect(page.locator('#crumb')).toHaveText('Transactions');
  await expect(page.locator('#sidebar')).not.toHaveClass(/open/);
});

test('dashboard has no horizontal page overflow', async ({ page }) => {
  await page.goto('./app.html');
  const metrics = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth
  }));
  expect(metrics.content).toBeLessThanOrEqual(metrics.viewport);
});

test('Moroccan demo uses dirhams and clearly discloses demo status', async ({ page }) => {
  await page.goto('./app.html');
  await expect(page.locator('body')).toContainText('Montants fictifs en DH');
  await expect(page.locator('body')).not.toContainText('€');
  page.once('dialog', async dialog => {
    expect(dialog.message()).toContain('Fournisseur');
    await dialog.dismiss();
  });
  await page.locator('#newBtn').click();
});

test('accountant workspace lists and filters client companies', async ({ page }, testInfo) => {
  await page.goto('./app.html');
  if (testInfo.project.name.startsWith('mobile')) await page.locator('#menuToggle').click();
  await page.locator('.nav button[data-page="Entreprises clientes"]').click();
  await expect(page.locator('#accountantWorkspace')).toHaveClass(/active/);
  await expect(page.locator('#companyList .company-row:visible')).toHaveCount(3);
  await page.locator('#companyList .company-row[data-company="atlas"]').click();
  await expect(page.locator('#companyList .company-row[data-company="atlas"]')).toHaveClass(/selected/);
  await expect(page.locator('#companyList .company-row[data-company="atelier"]')).not.toHaveClass(/selected/);
  await expect(page.locator('#companyDetailName')).toHaveText('Atlas Distribution');
  await expect(page.locator('#companyDocs')).toHaveText('2');
  await page.locator('#companySearch').fill('Argan');
  await expect(page.locator('#companyList .company-row:visible')).toHaveCount(1);
  await expect(page.locator('#companyList .company-row:visible').first()).toContainText('Argan & Vie');
});

test('accountant can add a temporary demo company without registration', async ({ page }, testInfo) => {
  await page.goto('./app.html');
  if (testInfo.project.name.startsWith('mobile')) await page.locator('#menuToggle').click();
  await page.locator('.nav button[data-page="Entreprises clientes"]').click();
  page.once('dialog', dialog => dialog.accept('Test Fiduciaire'));
  await page.locator('#addCompanyBtn').click();
  await expect(page.locator('#companyList .company-row')).toHaveCount(4);
  await expect(page.locator('#companyDetailName')).toHaveText('Test Fiduciaire');
  await expect(page.locator('#companyDetailNote')).toContainText('temporairement');
});

test('accountant can review demo documents and filter by status', async ({ page }, testInfo) => {
  await page.goto('./app.html');
  if (testInfo.project.name.startsWith('mobile')) await page.locator('#menuToggle').click();
  await page.locator('.nav button[data-page="Entreprises clientes"]').click();
  await page.locator('#companyList .company-row[data-company="atlas"]').click();
  await page.locator('#reviewCompanyBtn').click();
  await expect(page.locator('#documentReview')).toHaveClass(/active/);
  await expect(page.locator('#documentList .document-row')).toHaveCount(3);
  await page.locator('#documentList .document-row[data-document-id="at-1"] button[data-doc-action="valid"]').click();
  await expect(page.locator('#documentList .document-row[data-document-id="at-1"] .document-status')).toHaveText('Validé');
  await expect(page.locator('#companyDocs')).toHaveText('1');
  await page.locator('#documentFilter').selectOption('review');
  await expect(page.locator('#documentList .document-row')).toHaveCount(1);
  await expect(page.locator('#documentList .document-row').first()).toContainText('Justificatif de paiement');
});

test('account page exposes signup/login modes and has public Supabase configuration', async ({ page }) => {
  await page.goto('./auth.html');
  await expect(page).toHaveTitle(/Compte Multy/);
  await expect(page.getByRole('heading', { name: 'Créer votre compte' })).toBeVisible();
  await expect(page.locator('#firmName')).toBeVisible();
  await page.locator('#loginTab').click();
  await expect(page.getByRole('heading', { name: 'Bon retour' })).toBeVisible();
  await expect(page.locator('#firmName')).toBeHidden();
  const config = await page.evaluate(() => window.MULTY_SUPABASE_CONFIG);
  expect(config.url).toBe('https://abxapmbiuijaybwddvrw.supabase.co');
  expect(config.publishableKey).toMatch(/^sb_publishable_/);
  expect(config.publishableKey).not.toContain('sb_secret');
});

test('billing calculates totals and saves a local invoice draft', async ({ page }) => {
  await page.goto('./facturation.html');
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
  await page.goto('./facturation.html');
  await page.getByRole('tab', { name: 'Payées' }).click();
  await expect(page.locator('#invoiceRows tr')).toHaveCount(1);
  await expect(page.locator('#invoiceRows tr').first()).toContainText('Maison Créative');
  await page.locator('#invoiceSearch').fill('absent');
  await expect(page.locator('#emptyInvoices')).toBeVisible();
});

test('billing page fits the mobile viewport', async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.startsWith('mobile'), 'Phone-specific layout check');
  await page.goto('./facturation.html');
  const metrics = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, content: document.documentElement.scrollWidth }));
  expect(metrics.content).toBeLessThanOrEqual(metrics.viewport);
});

test('pilotage navigation opens each local demo module', async ({ page }, testInfo) => {
  await page.goto('./app.html');
  const modules = [
    ['Transactions', 'Entrées du mois'],
    ['Dépenses', 'Total du mois'],
    ['Trésorerie', 'Comptes de trésorerie'],
    ['Comptabilité', 'Pré-comptabilité indicative'],
    ['Rapports', 'Chiffre d’affaires HT'],
    ['Équipe', 'Membres de l’espace']
  ];

  for (const [name, content] of modules) {
    if (testInfo.project.name.startsWith('mobile')) await page.locator('#menuToggle').click();
    await page.locator('.nav button[data-page="' + name + '"]').click();
    await expect(page.locator('#pageTitle')).toContainText(name);
    await expect(page.locator('#modulePage')).toHaveClass(/active/);
    await expect(page.locator('#modulePage')).toContainText(content);
  }
});
