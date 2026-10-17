// Display-only fixtures: every Evolution mutation is intercepted. No analyst
// verdict, model output, candidate freeze or held-out result reaches Firestore.
const assert = require('node:assert/strict');
const { expect } = require('@playwright/test');

module.exports = async function checkEvolution(browser, baseUrl = 'http://127.0.0.1:8080') {
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  try {
    const usage = { categories: null, known_categories: {}, total_tokens: null, known_estimated_usd_micros: 0,
      unknown_attempts: 0, not_applicable_attempts: 0, provider_attempts: 0 };
    const gate = { conclusive_reviews: 1, target_rule_reviews: 1, required_overall: 30, required_target_rule: 15, status: 'INSUFFICIENT_EVIDENCE' };
    const snapshot = { id: 'f'.repeat(64), created_at: '2026-10-17T00:00:00Z', body: { dataset_hash: 'unit-source',
      label_provenance: 'HUMAN_OPERATOR_ONLY', sample_sizes: { feedback_events: 1, reviewed_alerts: 1, conclusive_reviews: 1, inconclusive_reviews: 0, succeeded_steps: 0, usage_steps: 0 }, detector_gate: gate, usage, rules: {} } };
    const id = 'e'.repeat(24);
    const run = { id, state: 'QUEUED', error_code: null, analytical_snapshot_id: snapshot.id };
    const detail = { run, analytical_snapshot_id: snapshot.id, result: null, recommendation: null,
      optimization_replays: { prompt: 'UNEVALUATED', skill: 'UNEVALUATED', weight: 'UNEVALUATED' }, activation_allowed: false };
    const candidate = { id: 'hv-15000', kind: 'RULE_THRESHOLD', threshold_aud_minor: 1500000 };
    const stored = { freeze: null, simulation: null };
    const calls = { a5: 0, freeze: 0, simulation: 0, review: 0 };
    let reviewConflict = true;
    let holdAnalysis = false, releaseAnalysis;
    const otherRun = { ...run, id: 'b'.repeat(24), state: 'FAILED', error_code: 'BROWSER_FIXTURE_FAILURE' };
    await page.route('**/api/operator/session', route => route.fulfill({ json: { uid: 'operator-demo', is_admin: false, live_ai_eligible: true, mode: 'local' } }));
    await page.route('**/api/operator/evolution/**', async route => {
      const request = route.request(), url = new URL(request.url()), path = url.pathname;
      if (path.endsWith('/snapshots')) return route.fulfill({ json: request.method() === 'POST' ? snapshot : { items: [snapshot], next_cursor: null } });
      if (path.endsWith('/candidates')) return route.fulfill({ json: { options: [{ candidate, candidate_hash: 'c'.repeat(64) }] } });
      if (path.endsWith('/freeze')) return route.fulfill({ json: stored });
      if (path.endsWith('/runs') && request.method() === 'GET') return route.fulfill({ json: { items: [run, otherRun], next_cursor: null } });
      if (path.endsWith('/runs')) { calls.a5++; return route.fulfill({ json: { ...run, usage, children: [], attempts: [] } }); }
      if (path.endsWith('/runs/' + otherRun.id)) return route.fulfill({ json: { ...detail, run: otherRun, result: null, recommendation: null } });
      if (path.endsWith('/runs/' + id)) {
        if (holdAnalysis) await new Promise(resolve => { releaseAnalysis = resolve; });
        return route.fulfill({ json: detail }).catch(() => {}); // The superseded request may have been aborted.
      }
      if (path.endsWith('/freezes')) {
        calls.freeze++;
        stored.freeze = { id: 'browser-freeze', candidate, candidate_hash: 'c'.repeat(64), content_hash: 'd'.repeat(64),
          support_status: 'OPERATOR_SELECTED_NOT_FEEDBACK_SUPPORTED', detector_gate: gate, frozen_at: '2026-10-17T00:00:00Z', notes: request.postDataJSON().notes, activation_allowed: false };
        return route.fulfill({ json: stored.freeze });
      }
      if (path.endsWith('/simulation')) {
        calls.simulation++;
        const counts = { TP: 1, FP: 1, TN: 1, FN: 1, recall: 0.5, precision: 0.5, fpr: 0.5 };
        stored.simulation = { state: 'COMPLETE', error_code: null, metrics: { baseline: counts, candidate_metrics: counts,
          benign_alerts_removed: 0, suspicious_alerts_removed: 0, cases_retained_by_other_rules: [], additional_missed_case_ids: [],
          case_ids: ['fixture-1', 'fixture-2', 'fixture-3', 'fixture-4'], result: 'NO_ADDITIONAL_MISSES_OBSERVED', provenance: 'BROWSER_FIXTURE_ONLY' } };
        return route.fulfill({ json: stored.simulation });
      }
      if (path.endsWith('/review')) {
        calls.review++;
        if (reviewConflict) return route.fulfill({ status: 409, json: { detail: 'Browser fixture conflict' } });
        detail.recommendation = { ...detail.recommendation, ...request.postDataJSON(), revision: 1, review_notes: request.postDataJSON().notes };
        return route.fulfill({ json: detail.recommendation });
      }
      throw new Error('Unhandled fixture route: ' + path);
    });
    await page.goto(baseUrl);
    await page.getByRole('button', { name: /Public visitor/ }).click();
    await page.getByRole('button', { name: 'Sign in locally', exact: true }).click();
    await page.getByRole('button', { name: /Operator.*Sign out/ }).waitFor();
    await page.getByRole('button', { name: 'Evolution lab', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Queue Evolution analysis', exact: true })).toBeEnabled();
    await page.getByRole('button', { name: 'Queue Evolution analysis', exact: true }).click();
    await page.getByRole('dialog', { name: 'Queue Evolution analysis?', exact: true }).waitFor();
    assert.equal(calls.a5, 0);
    assert(await page.getByRole('button', { name: 'Close dialog' }).evaluate(button => button === document.activeElement));
    await page.keyboard.press('Escape');
    await page.getByRole('button', { name: 'Queue Evolution analysis', exact: true }).click();
    await page.getByRole('dialog').getByRole('button', { name: 'Queue Evolution analysis', exact: true }).click();
    await page.getByText(/Evolution analysis queued/).waitFor();
    assert.equal(calls.a5, 1);
    run.state = 'COMPLETE';
    detail.result = { status: 'INSUFFICIENT_EVIDENCE', summary: 'Browser fixture: insufficient evidence.', conclusive_reviews: 1,
      target_rule_reviews: 1, candidate_id: null, hypothesis: null, support_feedback_ids: [], limitations: ['Display fixture only; not provider evidence.'] };
    await page.getByRole('button', { name: 'Refresh Evolution data', exact: true }).click();
    await page.getByText('Browser fixture: insufficient evidence.', { exact: true }).waitFor();
    await page.getByLabel('Detector candidate', { exact: true }).selectOption(candidate.id);
    await page.getByLabel('Detector candidate', { exact: true }).focus();
    await page.keyboard.press('Alt+ArrowDown'); await page.keyboard.press('Escape');
    await page.getByRole('button', { name: 'Freeze detector candidate', exact: true }).click();
    await page.getByText('Explain your candidate selection.', { exact: true }).waitFor();
    assert(await page.getByLabel('Candidate freeze notes', { exact: true }).evaluate(input => input === document.activeElement));
    await page.getByLabel('Candidate freeze notes', { exact: true }).fill('Browser fixture selection; not a real operator freeze.');
    await page.getByRole('button', { name: 'System design', exact: true }).click();
    await page.getByRole('dialog', { name: 'Discard unsaved review?', exact: true }).waitFor();
    await page.getByRole('button', { name: 'Keep editing', exact: true }).click();
    await expect(page.getByLabel('Candidate freeze notes', { exact: true })).toHaveValue('Browser fixture selection; not a real operator freeze.');
    await page.getByRole('button', { name: 'Freeze detector candidate', exact: true }).click();
    await page.getByRole('dialog', { name: 'Freeze detector candidate?', exact: true }).waitFor();
    assert.equal(calls.freeze, 0);
    await page.getByRole('dialog').getByRole('button', { name: 'Freeze detector candidate', exact: true }).click();
    await page.getByText(/operator selected not feedback supported/).waitFor();
    assert.equal(calls.freeze, 1);
    await page.getByRole('button', { name: 'Run held-out comparison', exact: true }).click();
    await page.getByRole('dialog', { name: 'Open held-out comparison?', exact: true }).waitFor();
    assert.equal(calls.simulation, 0);
    await page.getByRole('dialog').getByRole('button', { name: 'Run held-out comparison', exact: true }).click();
    await page.getByText(/4 conclusive synthetic held-out cases/).waitFor();
    assert.equal(calls.simulation, 1);
    await expect(page.getByRole('button', { name: 'Run held-out comparison', exact: true })).toHaveCount(0);
    // A separate consistent supported-proposal display fixture exercises review.
    Object.assign(gate, { conclusive_reviews: 30, target_rule_reviews: 15, status: 'SUFFICIENT_EVIDENCE' });
    detail.result = { ...detail.result, status: 'SUPPORTED_PROPOSAL', conclusive_reviews: 30, target_rule_reviews: 15,
      candidate_id: candidate.id, hypothesis: 'Browser fixture only', support_feedback_ids: ['fixture-review'] };
    detail.recommendation = { id, state: 'PROPOSED', revision: 0, hypothesis: 'Browser fixture only',
      diff: { component: 'DETECTOR', rule_id: 'HIGH_VALUE', before: 'detector-v1', after: candidate }, activation_allowed: false };
    await page.getByRole('button', { name: 'Refresh Evolution data', exact: true }).click();
    await page.getByLabel('Recommendation review notes', { exact: true }).fill('Retain this fixture note after conflict.');
    await page.getByRole('button', { name: 'Save recommendation review', exact: true }).click();
    await page.getByText(/stored state changed or an evidence gate is closed/).waitFor();
    await expect(page.getByLabel('Recommendation review notes', { exact: true })).toHaveValue('Retain this fixture note after conflict.');
    reviewConflict = false;
    await page.getByRole('button', { name: 'Refresh Evolution data', exact: true }).click();
    await expect(page.getByLabel('Recommendation review notes', { exact: true })).toHaveValue('Retain this fixture note after conflict.');
    await page.getByRole('button', { name: 'Save recommendation review', exact: true }).click();
    await page.getByText('Recommendation review saved. No monitoring change was applied.', { exact: true }).waitFor();
    assert.equal(calls.review, 2);
    holdAnalysis = true;
    await page.getByRole('button', { name: 'Refresh Evolution data', exact: true }).click();
    await expect.poll(() => typeof releaseAnalysis).toBe('function');
    await page.getByLabel('Stored analysis', { exact: true }).selectOption(otherRun.id);
    await page.getByText(/Analysis: failed.*BROWSER_FIXTURE_FAILURE/).waitFor();
    releaseAnalysis(); holdAnalysis = false;
    await expect(page.getByLabel('Stored analysis', { exact: true })).toHaveValue(otherRun.id);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.emulateMedia({ reducedMotion: 'reduce' });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Evolution hashes and controls must fit mobile');
    await page.route('**/api/operator/evolution/snapshots', route => route.abort('internetdisconnected'));
    await page.getByRole('button', { name: 'Refresh Evolution data', exact: true }).click();
    await page.getByText(/request could not be confirmed/).waitFor();
    // Private-brief rendering is also a display fixture; feedback is never POSTed.
    const cases = (await (await page.request.get(baseUrl + '/api/demo/alerts')).json()).cases;
    const current = cases.find(item => item.alerts.length);
    const alertId = current.alerts[0].id;
    const finding = { text: 'Browser fixture: private brief rendering.', evidence_ids: [current.evidence.trigger.id] };
    const alertPath = '**/api/operator/alerts/' + alertId;
    await page.route(alertPath, route => route.fulfill({ json: { alert: { id: alertId, status: 'COMPLETE', feedback_revision: 0,
      current_run_id: 'display-fixture-only', priority: 'URGENT_REVIEW' }, latest_run: null, outputs: {
        A2: { findings: [finding], counter_evidence: [], limitations: ['Display fixture only'] },
        A3: { primary_typology: 'UNDETERMINED', suggested_action: 'REVIEW', uncertainty: 'HIGH', rationale: finding },
        A4: { overview: finding, key_findings: [], counter_evidence: [], missing_information: [], next_steps: [], limitations: ['Display fixture only'] }
      } } }));
    await page.getByRole('button', { name: 'Investigations', exact: true }).click();
    await page.getByLabel('Search cases', { exact: true }).fill(current.name);
    await page.locator('.case-item').click();
    await page.getByRole('heading', { name: 'Private investigation brief', exact: true }).waitFor();
    await expect(page.getByRole('button', { name: 'Save feedback', exact: true })).toBeEnabled();
    await page.getByText(/Source-ID checks do not establish semantic support/).waitFor();
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Private citation IDs must wrap on mobile');
    await page.getByLabel('Review notes', { exact: true }).fill('Unsaved browser fixture note; never submitted.');
    await page.route(alertPath, route => route.fulfill({ status: 401, json: { detail: 'Fixture expired session' } }));
    await page.getByRole('button', { name: 'Refresh status', exact: true }).click();
    await page.getByText('Your operator session expired. Sign in again to continue.', { exact: true }).waitFor();
    await expect(page.getByRole('heading', { name: 'Private investigation brief', exact: true })).toHaveCount(0);
    assert.deepEqual(await page.evaluate(() => [Object.keys(localStorage), Object.keys(sessionStorage)]), [[], []]);
  } finally { await page.close(); }
};
