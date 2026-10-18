// Read-only checks: never save feedback, change policy, import data or call models.
const assert = require('node:assert/strict');
const path = require('node:path');
process.env.PLAYWRIGHT_BROWSERS_PATH ||= path.resolve('.cache/playwright');
const { chromium, expect } = require('@playwright/test');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
  const errors = [], writes = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => { if (request.url().includes('/api/operator/') && request.method() !== 'GET') writes.push(request.url()); });
  try {
    await page.goto(process.env.GENESIS_BROWSER_BASE_URL || 'http://127.0.0.1:5173');
    await expect(page.locator('.bulk-table tbody tr')).toHaveCount(50, {timeout:15000});
    async function stateSpacing() {
      const geometry = await page.locator('.bulk-table tbody tr').first().locator('td').nth(3).evaluate(cell => {
        const group = cell.querySelector('.bulk-state'), children = [...group.children].map(child => child.getBoundingClientRect());
        return { display: getComputedStyle(cell).display, padding: getComputedStyle(cell).paddingLeft,
          gap: getComputedStyle(group).gap, children: children.map(r => ({ left: r.left, right: r.right, top: r.top, bottom: r.bottom })) };
      });
      assert.equal(geometry.display, 'table-cell'); assert.equal(geometry.padding, '10px'); assert.equal(geometry.gap, '8px');
      if (geometry.children.length >= 2) {
        const [a,b] = geometry.children;
        assert(b.left - a.right >= 7.5 || b.top - a.bottom >= 7.5, 'State elements need an 8px gap');
      }
    }
    await stateSpacing();
    await expect(page.locator('.bulk-table tbody td:first-child small')).toHaveCount(0);
    await expect(page.getByLabel('Identity type',{exact:true}).getByRole('option',{name:'Individuals',exact:true})).toHaveCount(1);
    await expect(page.getByLabel('Identity type',{exact:true}).getByRole('option',{name:'Organizations',exact:true})).toHaveCount(1);
    await page.getByRole('button',{name:/View details for/}).first().click();
    await expect(page.getByRole('dialog',{name:'View details',exact:true}).getByText('Identity type',{exact:true})).toBeVisible();
    await page.keyboard.press('Escape');
    await page.getByRole('button', { name: /Public visitor/ }).click();
    await page.getByRole('button', { name: 'Sign in locally', exact: true }).click();
    await page.getByRole('button', { name: /Operator.*Sign out/ }).waitFor();
    await expect(page.getByRole('columnheader', { name: 'Investigation state', exact: true })).toBeVisible();
    await stateSpacing();
    for (const width of [1440,768,390,320]) {
      await page.setViewportSize({ width, height: 1000 });
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `Overflow at ${width}`);
    }
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.locator('.bulk-table').screenshot({ path: '.cache/preview/ci004-table.png' });
    await page.getByRole('button', {name:'Evolution lab',exact:true}).click();
    await expect(page.locator('.matrix-rule-label .category-chip')).toHaveCount(9);
    await page.locator('.evo-practice > summary').click();
    const history = page.getByRole('region',{name:'Stored seeded history',exact:true});
    for (const [label,value] of [['Actual Gemini advisory reviews','30'],['Agent-drafted advisory reviews','1,970'],['Awaiting an advisory review','0'],['Reserved for later','1,000']]) {
      await expect(history.locator('dt').filter({hasText:new RegExp('^'+label+'$')}).locator('..').locator('dd')).toHaveText(value);
    }
    await history.screenshot({path:'.cache/preview/ci003-draft-counters.png'});
    async function singleLineChips(target, selector) {
      const lines = await target.locator(selector).evaluateAll(chips => chips.map(chip => {
        const range = document.createRange(); range.selectNodeContents(chip);
        return {lines:range.getClientRects().length,wrap:getComputedStyle(chip).whiteSpace};
      }));
      assert(lines.every(value => value.lines === 1 && value.wrap === 'nowrap'));
    }
    await singleLineChips(page, '.matrix-rule-label .category-chip');
    const catalog = await browser.newPage({viewport:{width:390,height:740}});
    await catalog.goto(process.env.GENESIS_BROWSER_BASE_URL || 'http://127.0.0.1:5173');
    await catalog.getByRole('button', {name:'Evolution lab',exact:true}).click();
    await expect(catalog.locator('.rule-catalog .category-chip')).toHaveCount(9);
    await singleLineChips(catalog, '.rule-catalog .category-chip');
    await catalog.locator('.rule-catalog').screenshot({path:'.cache/preview/ci007-catalog.png'});
    await catalog.close();
    const counts = await browser.newPage();
    await counts.route('**/api/demo/bulk/summary', async route => {
      const response = await route.fetch(); const data = await response.json();
      await route.fulfill({json:{...data,scope:'LEGACY_CORPUS',transactions:12345,cases:24680,identities:123,reference_annotations:10000,
        training_transactions:8000,validation_transactions:2000,initially_unprocessed:14680,reference_walkthrough_cases:4000}});
    });
    await counts.route('**/api/demo/bulk/reference-summary', async route => {
      const response = await route.fetch(); const data = await response.json();
      await route.fulfill({json:{...data,cases:4000,population_fraction:0.2}});
    });
    await counts.goto(process.env.GENESIS_BROWSER_BASE_URL || 'http://127.0.0.1:5173');
    await expect(counts.locator('.metric').filter({has:counts.getByText('Dataset',{exact:true})}).locator('strong')).toHaveText('12,345');
    await expect(counts.locator('.metric').filter({has:counts.getByText('Reference annotations',{exact:true})}).locator('strong')).toHaveText('10,000');
    await expect(counts.getByText(/4,000 reference \+ 14,680 operational cases/)).toBeVisible();
    await expect(counts.getByRole('heading',{name:/4,000-case reference evaluation/})).toBeVisible();
    await expect(counts.getByText(/20% of the corpus/)).toBeVisible();
    await counts.getByRole('button',{name:/Public visitor/}).click();
    await counts.getByRole('button',{name:'Sign in locally',exact:true}).click();
    await counts.getByRole('button',{name:/Operator.*Sign out/}).waitFor();
    await counts.getByRole('button',{name:'Evolution lab',exact:true}).click();
    await expect(counts.getByText(/24,680 source cases · 14,680 operational cases/)).toBeVisible();
    await expect(counts.getByText(/Current corpus: 14,680 operational cases within 24,680 total cases/)).toBeVisible();
    await counts.locator('.evo-practice > summary').click();
    await expect(counts.getByRole('option',{name:'Existing corpus / 8,000 training references',exact:true})).toHaveCount(1);
    await counts.getByRole('button',{name:'Admin',exact:true}).click();
    await expect(counts.getByText(/current 24,680-case corpus/)).toBeVisible();
    await counts.close();
    for (const {googleAvailable, stored} of [{googleAvailable:true,stored:false},{googleAvailable:false,stored:false},{googleAvailable:true,stored:true}]) {
      const cloud = await browser.newPage(); let passwordCalls = 0, sessionCalls = 0;
      await cloud.route('**/api/config', route => route.fulfill({ json: { mode: 'cloud', project_id: 'genesis-aicb', firebase_web_api_key: 'TEST_ONLY_PUBLIC_CONFIG', auth_emulator_url: null, ...(stored ? {operator_demo_email:'operator@example.test'} : {}) } }));
      await cloud.route('**/api/operator/demo-login', route => {
        assert(stored); assert.equal(route.request().method(), 'POST');
        return route.fulfill({json:{idToken:'TEST_ONLY_TOKEN'}});
      });
      await cloud.route('**/google-auth.ts*', route => route.fulfill({ contentType: 'text/javascript', body:
        `export function prepareGoogleSignIn(){${googleAvailable ? 'return {signIn:async()=>"TEST_ONLY_TOKEN",dispose:async()=>{}}' : 'throw new Error("TEST_ONLY_SETUP_FAILURE")'}};export function googleSignInError(){return "TEST_ONLY operator denied"}` }));
      await cloud.route('https://identitytoolkit.googleapis.com/**', async route => {
        assert(route.request().url().includes('/accounts:signInWithPassword?key=TEST_ONLY_PUBLIC_CONFIG'));
        assert.deepEqual(route.request().postDataJSON(), { email: 'operator@example.test', password: 'fixture-only-not-a-credential', returnSecureToken: true });
        passwordCalls++; await route.fulfill({ json: { idToken: 'TEST_ONLY_TOKEN' } });
      });
      await cloud.route('**/api/operator/session', route => {
        assert.equal(route.request().headers().authorization, 'Bearer TEST_ONLY_TOKEN'); sessionCalls++;
        return route.fulfill({ status: 403, json: { detail: 'TEST_ONLY operator denied' } });
      });
      await cloud.goto(process.env.GENESIS_BROWSER_BASE_URL || 'http://127.0.0.1:5173');
      await cloud.getByRole('button', { name: /Public visitor/ }).click();
      const dialog = cloud.getByRole('dialog', { name: 'Operator sign-in' });
      await expect(dialog.getByLabel('Email', { exact: true })).toHaveValue(stored ? 'operator@example.test' : '');
      await expect(dialog.getByLabel('Password', { exact: true })).toHaveValue('');
      await expect(dialog.getByRole('button', { name: 'Sign in with email', exact: true })).toBeEnabled();
      if (googleAvailable) {
        await dialog.getByRole('button', { name: 'Continue with Google', exact: true }).click();
        await expect(dialog.getByText('TEST_ONLY operator denied', { exact: true })).toBeVisible();
      } else await expect(dialog.getByRole('button', { name: 'Continue with Google', exact: true })).toBeDisabled();
      if (stored) {
        await dialog.getByRole('button', {name:'Use stored operator login',exact:true}).click();
        await expect(dialog.getByText('TEST_ONLY operator denied', {exact:true})).toBeVisible();
        await expect(dialog.getByLabel('Password', {exact:true})).toHaveValue('');
      } else await expect(dialog.getByRole('button', {name:'Use stored operator login',exact:true})).toHaveCount(0);
      await dialog.getByLabel('Email', { exact: true }).fill('operator@example.test');
      await dialog.getByLabel('Password', { exact: true }).fill('fixture-only-not-a-credential');
      await dialog.getByRole('button', { name: 'Sign in with email', exact: true }).click();
      await expect(dialog.getByText('TEST_ONLY operator denied', { exact: true })).toBeVisible();
      assert.equal(passwordCalls, 1); assert.equal(sessionCalls, (googleAvailable ? 2 : 1) + (stored ? 1 : 0));
      await cloud.close();
    }
    assert.deepEqual(errors, []); assert.deepEqual(writes, []);
    console.log('Code-improvement browser checks passed: table spacing, public/operator modes, 320–1440px, no operator writes.');
  } catch (error) { console.error(JSON.stringify({pageErrors:errors})); throw error; }
  finally { await browser.close(); }
})().catch(error => { console.error(error.stack); process.exitCode = 1; });
