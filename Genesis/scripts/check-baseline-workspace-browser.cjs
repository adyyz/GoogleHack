// Read-only live-emulator acceptance: no feedback, policy changes or model calls.
const assert = require('node:assert/strict');
const path = require('node:path');
process.env.PLAYWRIGHT_BROWSERS_PATH ||= path.resolve('.cache/playwright');
const {chromium, expect} = require('@playwright/test');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({baseURL:process.env.GENESIS_BROWSER_BASE_URL || 'http://127.0.0.1:5173', viewport:{width:1440,height:1000}, reducedMotion:'reduce'});
  const errors = [], writes = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => {
    if (request.url().includes('/api/operator/') && request.method() !== 'GET' && !request.url().endsWith('/session')) writes.push(request.url());
  });
  try {
    await expect.poll(async () => {
      try { return (await page.request.get('/api/health')).status(); } catch { return 0; }
    }, {timeout:15000}).toBe(200);
    await page.goto(process.env.GENESIS_BROWSER_BASE_URL || 'http://127.0.0.1:5173');
    const summary = await (await page.request.get('/api/demo/bulk/summary')).json();
    assert.equal(summary.scope,'ACTIVE_BASELINE');
    assert.equal(summary.cases,3000); assert.equal(summary.identities,200);
    assert.equal(summary.reference_walkthrough_cases,2000); assert.equal(summary.initially_unprocessed,1000);
    assert.equal(summary.advisory.ai_reviewed_cases,30); assert.equal(summary.advisory.agent_draft_reviewed_cases,1970);
    assert(!('reserved' in summary.advisory), 'Public counters must not expose reserved label aggregates');
    assert.equal((await page.request.get('/api/operator/bulk/projected-reviews')).status(),401);
    await expect(page.locator('.bulk-metrics')).toContainText('3,000');
    await expect(page.locator('.bulk-metrics')).toContainText('200 identities');
    await expect(page.locator('.bulk-metrics')).toContainText('30 Gemini / 1,970 agent drafts');
    await expect(page.locator('.bulk-table tbody tr')).toHaveCount(50);
    await expect(page.getByLabel('Identity',{exact:true}).locator('option')).toHaveCount(201);
    const publicQueue = await (await page.request.get('/api/demo/bulk/cases')).json();
    assert.equal(publicQueue.total,3000); assert.equal(publicQueue.dataset_id,summary.dataset_id);
    const pending = await (await page.request.get('/api/demo/bulk/cases?status=awaiting_triage')).json();
    assert.equal(pending.total,1000);
    assert(pending.items.every(row => !Object.keys(row).some(key => key.startsWith('reference_'))));
    await page.getByRole('button',{name:/View details for/}).first().click();
    await expect(page.getByRole('dialog',{name:'View details',exact:true})).toContainText(publicQueue.items[0].name);
    await page.keyboard.press('Escape');
    await page.getByRole('button',{name:/Public visitor/}).click();
    await page.getByRole('button',{name:'Sign in locally',exact:true}).click();
    await expect(page.getByRole('button',{name:/Operator/}).first()).toBeVisible();
    const reviewedResponse = page.waitForResponse(response => response.url().includes('/api/operator/bulk/evolution/review-summary'));
    const matrixResponse = page.waitForResponse(response => response.url().includes('/api/operator/bulk/evolution/rule-matrix'));
    const projectedResponse = page.waitForResponse(response => response.url().includes('/api/operator/bulk/projected-reviews'));
    await page.getByRole('button',{name:'Evolution lab',exact:true}).click();
    const reviewed = await (await reviewedResponse).json(), matrix = await (await matrixResponse).json();
    assert.equal(reviewed.dataset_id,summary.dataset_id); assert.equal(reviewed.total_cases,3000);
    assert.equal(reviewed.total_identities,200); assert.equal(reviewed.reviewed_alerts,0);
    assert.equal(reviewed.agreement_rate,null); assert.equal(matrix.rules.length,9);
    for (const rule of matrix.rules) assert.equal(rule.alert_count,summary.rule_alerts[rule.id]);
    const referenceSummary = await (await page.request.get('/api/demo/bulk/reference-summary')).json();
    const projectedSummary = await (await projectedResponse).json();
    assert.equal(projectedSummary.cases,2000); assert.equal(projectedSummary.human_reviews_created,0);
    assert.deepEqual(projectedSummary.assignment_counts,{AGREE:1500,DISAGREE:400,UNCERTAIN:100});
    const rulePanel = page.locator('.rule-matrix');
    await expect(page.getByLabel('Outcome source')).toHaveValue('projection');
    await expect(rulePanel.getByRole('columnheader',{name:'Alerts / simulated reviews',exact:true})).toBeVisible();
    await expect(rulePanel.locator('.matrix-data tbody tr')).toHaveCount(9);
    for (const [index, rule] of matrix.rules.entries()) {
      const projected = projectedSummary.rules.find(row => row.rule_id === rule.id);
      await expect(rulePanel.locator('.matrix-data tbody tr').nth(index).locator('td').nth(0)).toHaveText(`${rule.alert_count} / ${projected.cases}`);
      await expect(rulePanel.locator('.matrix-data tbody tr').nth(index).locator('td').nth(1)).toHaveText(`${projected.true_positive} / ${projected.false_positive} / ${projected.inconclusive}`);
    }
    require('node:fs').mkdirSync('.cache/preview',{recursive:true});
    await rulePanel.screenshot({path:'.cache/preview/ci012-projected-matrix.png'});
    await page.getByLabel('Outcome source').selectOption('reference');
    await expect(page.getByLabel('Outcome source')).toHaveValue('reference');
    await expect(rulePanel.getByRole('columnheader',{name:'Alerts / reference-labeled',exact:true})).toBeVisible();
    await expect(rulePanel.locator('.matrix-data tbody tr')).toHaveCount(9);
    for (const [index, rule] of matrix.rules.entries()) {
      const reference = referenceSummary.rules.find(row => row.rule_id === rule.id);
      await expect(rulePanel.locator('.matrix-data tbody tr').nth(index).locator('td').nth(0)).toHaveText(`${rule.alert_count} / ${reference.cases}`);
      await expect(rulePanel.locator('.matrix-data tbody tr').nth(index).locator('td').nth(1)).toHaveText(`${reference.true_positive} / ${reference.false_positive} / ${reference.inconclusive}`);
    }
    await page.getByLabel('Outcome source').selectOption('human');
    await expect(rulePanel.getByRole('columnheader',{name:'Alerts / human-reviewed',exact:true})).toBeVisible();
    for (const [index, rule] of matrix.rules.entries()) {
      await expect(rulePanel.locator('.matrix-data tbody tr').nth(index).locator('td').nth(0)).toHaveText(`${rule.alert_count} / 0`);
    }
    await rulePanel.getByRole('button',{name:'Configuration',exact:true}).click();
    await expect(rulePanel.getByRole('columnheader',{name:'A0 TP / FP cutoffs',exact:true})).toBeVisible();
    await rulePanel.getByRole('button',{name:'Outcomes',exact:true}).click();
    await page.getByLabel('Outcome source').selectOption('reference');
    await expect(page.locator('.review-overview .review-totals')).toContainText('3,000');
    await expect(page.locator('.review-overview .review-totals')).toContainText('1,000 reserved cases');
    assert(!/40,000|20,000|17,753/.test(await page.locator('main').innerText()));
    for (const width of [320,390,768,1440]) {
      await page.setViewportSize({width,height:1000});
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),`Overflow at ${width}`);
    }
    await page.locator('.evo-practice > summary').click();
    await expect(page.getByRole('heading',{name:'2,000-case reference evaluation'})).toBeVisible();
    await expect(page.getByRole('region',{name:'Stored seeded history'})).toContainText('1,970');
    await page.getByRole('button',{name:'Admin',exact:true}).click();
    await expect(page.locator('main')).toContainText('current 3,000-case corpus');
    assert.equal(errors.length,0, errors.join('\n')); assert.deepEqual(writes,[]);
    console.log('Active Firestore baseline verified: Investigations, identities, details, Evolution, nine-rule matrix, practice and Admin; 320–1440px. No model or evidence writes.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode=1; });
