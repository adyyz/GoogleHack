// Display fixtures intercept every mutation. No genuine review, policy or model output is written.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { expect } = require('@playwright/test');
module.exports = async (browser, base) => {
  const page = await browser.newPage({viewport: {width: 1440, height: 1000}, reducedMotion: 'reduce'});
  const errors = [], calls = [];
  page.on('pageerror', error => errors.push(error.message));
  try {
    const gate = {conclusive_reviews: 30, target_rule_reviews: 15, status: 'SUFFICIENT_EVIDENCE'};
    const snapshot = {id: 'b'.repeat(64), created_at: '2026-10-18T00:00:00Z', body: {sample_sizes: {conclusive_reviews: 30, feedback_events: 30}, detector_gate: gate}};
    const candidate = {id: 'c'.repeat(24), rule_id: 'HIGH_VALUE', state: 'PROPOSED', revision: 0, baseline: {tp: .25, fp: .65}, thresholds: {tp: .25, fp: .4}, training: [], training_count: 15, identity_count: 8, frozen_at: snapshot.created_at, validation: null, before: {}, after: {correct_fp_resolutions: 3}};
    let prepared = false, validationChecks = 0;
    const policy = {policy_version_id: 'auto-label-v1', revision: 0};
    await page.route('**/api/operator/bulk/evolution/**', async route => {
      const request = route.request(), pathname = new URL(request.url()).pathname, method = request.method();
      if (pathname.endsWith('/snapshots')) return route.fulfill({json: {items: [snapshot], next_cursor: null}});
      if (pathname.endsWith('/auto-label/candidates')) return route.fulfill({json: {items: prepared ? [candidate] : [], next_cursor: null, active_policy: policy}});
      if (pathname.endsWith('/auto-label/calibrations')) {
        if (method === 'POST') { prepared = true; calls.push('prepare'); }
        return route.fulfill({json: method === 'POST' ? {id: 'fixture'} : {items: prepared ? [{id: 'fixture', overall_reviews: 30, results: [{rule_id: 'HIGH_VALUE', sample_size: 15, identity_count: 8, status: 'AWAITING_NEW_REVIEWS'}]}] : [], next_cursor: null}});
      }
      if (method !== 'GET') {
        const action = pathname.split('/').pop(); calls.push(action);
        if (action === 'validate') {
          validationChecks++;
          if (validationChecks === 1) return route.fulfill({json: {...candidate, validation_progress: 4}});
          candidate.validation = {passed: true, before: {wrong_fp: 0, wrong_tp: 0, correct_fp_resolutions: 0, uncertain: 2}, after: {wrong_fp: 0, wrong_tp: 0, correct_fp_resolutions: 2, uncertain: 0}};
          candidate.revision++;
        } else if (action === 'review') { candidate.state = 'APPROVED'; candidate.revision++; }
        else if (action === 'apply') { candidate.state = 'APPLIED'; candidate.revision++; candidate.applied_policy_id = 'd'.repeat(64); policy.policy_version_id = candidate.applied_policy_id; policy.revision++; }
        else if (action === 'rollback') { candidate.state = 'ROLLED_BACK'; candidate.revision++; policy.policy_version_id = 'auto-label-v1'; policy.revision++; }
        else if (action === 'reassess') return route.fulfill({json: {items: [{alert_id: 'display-only', state: 'SUCCEEDED'}], next_cursor: null}});
        else throw Error('Unexpected mutation ' + pathname);
        return route.fulfill({json: candidate});
      }
      return route.continue();
    });
    await page.goto(base);
    await page.getByRole('button', {name: /Public visitor/}).click();
    await page.getByRole('button', {name: 'Sign in locally', exact: true}).click();
    await page.getByRole('button', {name: /Operator.*Sign out/}).waitFor();
    await page.getByRole('button', {name: 'Evolution lab', exact: true}).click();
    const main = page.locator('.corpus-evolution');
    await expect(main.locator('.rule-matrix tbody tr')).toHaveCount(9);
    assert.deepEqual(await main.locator('.evo-stage').evaluateAll(rows => rows.map(row => row.id)), ['evo-outcomes','evo-understand','evo-learn','evo-apply','evo-observe']);
    await expect(page.getByText('Earlier Demo/Discovery evidence', {exact: true})).toHaveCount(0);
    await expect(page.locator('.evo-practice')).not.toHaveAttribute('open');
    assert.deepEqual(calls, [], 'Opening Evolution must not mutate or start model work');
    async function action(label) {
      await main.getByRole('button', {name: label, exact: true}).click();
      await page.getByRole('dialog').getByRole('button', {name: 'Confirm A0 action', exact: true}).click();
      await expect(page.getByRole('dialog')).toHaveCount(0);
    }
    await action('Prepare eligible A0 rules');
    await expect(main.getByRole('button', {name: 'Approve A0 candidate', exact: true})).toBeDisabled();
    await action('Check new validation reviews');
    await expect(page.getByText('Awaiting new independent reviews: 4 / 5.', {exact: true})).toBeVisible();
    await action('Check new validation reviews');
    await main.getByLabel('A0 decision notes', {exact: true}).fill('BROWSER_ONLY explicit decision');
    await page.getByRole('navigation', {name: 'Evolution stages'}).getByRole('button', {name: /4. Apply/}).click();
    await expect(main.getByLabel('A0 decision notes', {exact: true})).toHaveValue('BROWSER_ONLY explicit decision');
    await action('Approve A0 candidate');
    await main.getByLabel('A0 decision notes', {exact: true}).fill('BROWSER_ONLY apply');
    await action('Apply A0 cutoffs');
    await main.getByLabel('A0 decision notes', {exact: true}).fill('BROWSER_ONLY reassess');
    await action('Reassess uncertain alerts');
    await main.getByLabel('A0 decision notes', {exact: true}).fill('BROWSER_ONLY rollback');
    await action('Roll back A0 policy');
    await main.getByLabel('A0 decision notes', {exact: true}).fill('BROWSER_ONLY restore');
    await action('Restore affected assessments');
    assert.deepEqual(calls, ['prepare','validate','validate','review','apply','reassess','rollback','reassess']);
    await main.getByLabel('Public executive summary (maximum 120 words)', {exact: true}).fill('BROWSER_ONLY unsaved');
    await expect.poll(() => page.evaluate(() => { const event = new Event('beforeunload', {cancelable: true}); window.dispatchEvent(event); return event.defaultPrevented; })).toBe(true);
    await page.getByRole('button', {name: 'System design', exact: true}).click();
    await page.getByRole('dialog', {name: 'Discard unsaved review?', exact: true}).waitFor();
    await page.getByRole('button', {name: 'Keep editing', exact: true}).click();
    await expect(main.getByLabel('Public executive summary (maximum 120 words)', {exact: true})).toHaveValue('BROWSER_ONLY unsaved');
    await page.getByRole('button', {name: 'System design', exact: true}).click();
    await page.getByRole('button', {name: 'Discard changes', exact: true}).click();
    await page.getByRole('button', {name: 'Evolution lab', exact: true}).click();
    await expect(main.locator('.rule-matrix tbody tr')).toHaveCount(9);
    await expect(main.getByLabel('Public executive summary (maximum 120 words)', {exact: true})).toHaveValue('');
    assert.equal(await page.evaluate(() => {const ids = [...document.querySelectorAll('[id]')].map(el => el.id); return ids.length - new Set(ids).size;}), 0, 'Evolution must not duplicate form IDs');
    fs.mkdirSync('.cache/preview', {recursive: true});
    for (const width of [1440, 1024, 768, 390, 320]) {
      await page.setViewportSize({width, height: 1000});
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `Evolution overflow at ${width}px`);
      if (width === 1440 || width === 320) await page.screenshot({path: `.cache/preview/corpus-evolution-${width}.png`, fullPage: true});
    }
    assert.deepEqual(errors, []);
    console.log('Corpus Evolution passed: five-stage order, no automatic mutations, isolated A0 actions, dirty guards, unique form IDs and 320–1440px layouts.');
  } finally { await page.close(); }
};
