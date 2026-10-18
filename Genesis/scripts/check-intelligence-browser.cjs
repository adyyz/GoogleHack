// Read-only browser checks. Supporting evidence is an intercepted display fixture.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { expect } = require('@playwright/test');
module.exports = async (browser, base) => {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  try {
    const rows = (await (await page.request.get(base + '/api/demo/bulk/cases?status=awaiting_triage&rule=HIGH_VALUE&limit=100')).json()).items;
    const row = rows.find(row => row.rules.includes('HIGH_VALUE'));
    const source = await (await page.request.get(base + '/api/demo/bulk/cases/' + row.id)).json();
    const alert = source.alerts.find(item => item.rule_id === 'HIGH_VALUE');
    await page.route('**/api/operator/alerts/' + alert.id, route => route.fulfill({json: {
      alert: {...alert, feedback_revision: 0, current_run_id: null}, latest_run: null, outputs: {}, agent_trace: [],
    }}));
    await page.route('**/api/operator/bulk/evolution/rules/HIGH_VALUE/examples', route => route.fulfill({ json: {
      items: [{ feedback: { alert_id: alert.id, verdict: 'TRUE_POSITIVE', notes: 'BROWSER_ONLY supporting preview' }, case: source }], next_cursor: null,
    } }));
    await page.goto(base);
    await page.getByRole('button', { name: 'Evolution lab', exact: true }).click();
    await expect(page.getByRole('table').first().locator('tbody tr')).toHaveCount(9);
    await expect(page.getByRole('heading', { name: 'Rule matrix', exact: true })).toHaveCount(0);
    await page.getByRole('button', { name: /Public visitor/ }).click();
    await page.getByRole('button', { name: 'Sign in locally', exact: true }).click();
    await page.getByRole('button', { name: /Operator.*Sign out/ }).waitFor();
    const archive = page.locator('.corpus-evolution');
    const matrix = archive.locator('.rule-matrix');
    await expect(matrix.locator('tbody tr')).toHaveCount(9);
    await matrix.getByRole('button', { name: 'Configuration', exact: true }).click();
    await expect(matrix.getByText('Baseline: ≤ 0.25 / ≥ 0.65', { exact: true })).toHaveCount(9);
    await matrix.getByRole('button', { name: 'High-value movement', exact: true }).click();
    await matrix.getByRole('button', { name: 'Outcomes', exact: true }).click();
    await expect(matrix.getByRole('button', { name: 'High-value movement', exact: true })).toHaveAttribute('aria-pressed', 'true');
    await archive.getByRole('button', { name: 'Preview supporting alert', exact: true }).click();
    await page.getByRole('dialog', { name: 'Supporting investigation', exact: true }).waitFor();
    await page.getByRole('dialog').getByText('Agent execution trace', { exact: true }).click();
    await expect(page.getByRole('dialog').getByText('No agent attempt recorded for this alert.', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Open investigation', exact: true }).click();
    await expect(page.getByLabel('Selected alert', { exact: true })).toHaveValue(alert.id);
    await page.getByRole('dialog', { name: 'Supporting investigation', exact: true }).getByRole('button', { name: 'Close dialog', exact: true }).click();
    await expect(matrix.getByRole('button', { name: 'High-value movement', exact: true })).toHaveAttribute('aria-pressed', 'true');
    await archive.getByLabel('Public executive summary (maximum 120 words)', { exact: true }).fill('BROWSER_ONLY unsaved summary');
    // Dirty ownership crosses the publication form and Evolution before reaching the app guard.
    await expect.poll(() => page.evaluate(() => {
      const event = new Event('beforeunload', { cancelable: true });
      window.dispatchEvent(event);
      return event.defaultPrevented;
    })).toBe(true);
    await matrix.getByLabel('Rule category', { exact: true }).selectOption('Volume');
    await page.getByRole('dialog', { name: 'Discard unsaved review?', exact: true }).waitFor();
    await page.getByRole('button', { name: 'Keep editing', exact: true }).click();
    await expect(archive.getByLabel('Public executive summary (maximum 120 words)', { exact: true })).toHaveValue('BROWSER_ONLY unsaved summary');
    await matrix.getByLabel('Rule category', { exact: true }).selectOption('Volume');
    await page.getByRole('button', { name: 'Discard changes', exact: true }).click();
    await expect(archive.getByLabel('Public executive summary (maximum 120 words)', { exact: true })).toHaveValue('');
    await expect(matrix.locator('tbody tr')).toHaveCount(2);
    await matrix.getByLabel('Rule category', { exact: true }).selectOption('');
    await expect(matrix.locator('tbody tr')).toHaveCount(9);
    await expect(page.getByRole('button', { name: 'Approve A0 candidate', exact: true })).toHaveCount(0);
    await page.getByRole('button', { name: 'Investigations', exact: true }).click();
    await expect(page.locator('.bulk-table tbody tr')).toHaveCount(50);
    await expect(page.getByLabel('Investigation workspace')).toHaveCount(0);
    fs.mkdirSync('.cache/preview', { recursive: true });
    const layouts = [];
    for (const width of [1440, 1024, 768, 390, 320]) {
      await page.setViewportSize({ width, height: 1000 });
      for (const screen of ['Investigations', 'Evolution lab', 'System design', 'Admin']) {
        await page.getByRole('button', { name: screen, exact: true }).click();
        if (screen === 'Evolution lab') await expect(page.locator('.corpus-evolution .rule-matrix tbody tr')).toHaveCount(9);
        await page.emulateMedia({ reducedMotion: 'reduce' });
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${screen} overflows at ${width}px`);
        layouts.push({ screen, width, overflow: false });
        if (width === 1440 || width === 320) await page.screenshot({ path: `.cache/preview/intelligence-${screen.replaceAll(' ', '-')}-${width}.png` });
      }
    }
    fs.writeFileSync('.cache/intelligence-layout-verification.json', JSON.stringify(layouts, null, 2));
    assert.deepEqual(errors, []);
    console.log('Rule intelligence browser checks passed: public catalog, private matrix views, supporting-case return, current corpus, insufficient learning and 320–1440px layouts.');
  } finally { await page.close(); }
};
