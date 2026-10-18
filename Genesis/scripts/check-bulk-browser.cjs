// Isolated emulator workflow. Public simulation never creates provider/human evidence.
const assert = require('node:assert/strict');
const { expect } = require('@playwright/test');
module.exports = async (browser, base) => {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [], mutations = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('request', r => { if (r.method() === 'POST' && new URL(r.url()).pathname.startsWith('/api/')) mutations.push(r.url()); });
  try {
    const initialUsage = await (await page.request.get(base + '/api/demo/usage')).json();
    await page.goto(base);
    const metrics = page.locator('.bulk-metrics');
    await expect(metrics).toContainText('40,000');
    await expect(metrics).toContainText('20,000');
    await expect(page.locator('.bulk-table tbody tr')).toHaveCount(50);
    await expect(page.getByLabel('Identity', { exact: true }).locator('option')).toHaveCount(451);
    await expect(page.locator('.case-workflow')).toHaveCount(0);
    await page.getByRole('button', {name: /^View details for/}).first().click();
    const details = page.getByRole('dialog', {name: 'View details', exact: true});
    await expect(details.locator('.case-workflow')).toContainText('Operator-only status');
    await expect(details.getByRole('heading', {name: 'Python risk scores and weights', exact: true})).toBeVisible();
    await expect(details.locator('.case-risk-details tbody tr')).toHaveCount(5);
    await page.keyboard.press('Escape');
    await expect(details).toHaveCount(0);
    await expect(page.getByRole('button', {name: /^View details for/}).first()).toBeFocused();
    await page.getByLabel('Cases per batch', { exact: true }).fill('101');
    await expect(page.getByRole('button', { name: 'Preview synthetic batch', exact: true })).toBeDisabled();
    await page.getByLabel('Cases per batch', { exact: true }).fill('100');
    await page.getByRole('button', { name: 'Preview synthetic batch', exact: true }).click();
    await expect(page.getByRole('dialog')).toContainText('100 selected cases');
    await page.getByRole('button', { name: 'Start batch', exact: true }).click();
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await expect(metrics.locator('.metric').nth(1)).toContainText('100');
    assert.equal(mutations.length, 0, 'Public simulation must make no API mutation');
    assert.deepEqual(await (await page.request.get(base + '/api/demo/usage')).json(), initialUsage);
    await page.getByLabel('Identity type', { exact: true }).selectOption('INDIVIDUAL');
    await page.getByLabel('Detector rule', { exact: true }).selectOption('HIGH_VALUE');
    await expect(page.locator('.bulk-table tbody tr')).toHaveCount(50);
    await page.getByRole('button', { name: 'Next page', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Previous page', exact: true })).toBeEnabled();
    for (const width of [1440, 1024, 768, 390, 320]) {
      await page.setViewportSize({ width, height: 1000 });
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `Bulk ${width} overflow`);
    }
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.getByRole('button', { name: /Public visitor/ }).click();
    await page.getByRole('button', { name: 'Sign in locally', exact: true }).click();
    await page.getByRole('button', { name: /Operator.*Sign out/ }).waitFor();
    await expect(page.getByLabel('Investigation workspace')).toHaveCount(0);
    await page.getByLabel('Cases per batch', { exact: true }).fill('2');
    await page.getByRole('button', { name: 'Preview Gemini batch', exact: true }).click();
    await expect(page.getByRole('dialog')).toContainText('authorization is currently disabled');
    await page.getByRole('button', { name: 'Start batch', exact: true }).click();
    await expect(page.locator('.batch-progress')).toContainText('Batch: queued');
    await page.getByRole('button', { name: 'cancel', exact: true }).click();
    await page.getByRole('button', { name: 'Confirm action', exact: true }).click();
    await expect(page.locator('.batch-progress')).toContainText('Batch: cancelled');
    await page.getByRole('button', { name: 'Evolution lab', exact: true }).click();
    await page.getByRole('button', { name: 'Freeze genuine bulk outcomes', exact: true }).click();
    await expect(page.getByRole('alert')).toContainText('Genuine bulk analyst feedback is required');
    assert.deepEqual(errors, []);
    assert.deepEqual(await page.evaluate(() => [localStorage.length, sessionStorage.length]), [0, 0]);
    console.log('Bulk browser passed: 100-case zero-call simulation, paged filters, private job/cancel, synthetic learning, genuine-evidence refusal and responsive layouts.');
  } finally { await page.close(); }
};
