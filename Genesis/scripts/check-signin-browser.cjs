// Cloud/provider requests are intercepted faults; no Google login is attempted.
const assert = require('node:assert/strict');
const { expect } = require('@playwright/test');

module.exports = async function checkSignIn(browser, baseUrl = 'http://127.0.0.1:8080') {
  const context = await browser.newContext({ viewport: { width: 390, height: 740 }, reducedMotion: 'reduce' });
  try {
    const page = await context.newPage();
    let config = { mode: 'cloud', project_id: 'genesis-aicb', auth_emulator_url: null, firebase_web_api_key: null };
    let configFailure = true;
    let providerRequests = 0;
    let sessionCalls = 0;
    let releaseConfig;
    let slowConfig = false;
    await page.route('**/api/config', async route => {
      if (slowConfig) await new Promise(resolve => { releaseConfig = resolve; });
      await route.fulfill({ status: configFailure ? 503 : 200,
        json: configFailure ? { detail: 'Unavailable' } : config }).catch(() => {});
    });
    // Reject every external request, including Google's popup/iframe loader.
    await context.route(/^https:\/\//, async route => {
      providerRequests++;
      assert(!route.request().url().includes('idToken='));
      await route.abort('internetdisconnected');
    });
    await page.route('**/api/operator/session', async route => {
      sessionCalls++;
      await route.fulfill({ status: 403, json: { detail: 'Must not accept a provider fault as a session' } });
    });
    await page.goto(baseUrl);
    await page.getByRole('heading', { name: 'Investigations', exact: true }).waitFor();
    const trigger = page.getByRole('button', { name: /Public visitor/ });
    await trigger.click();
    await page.getByText('Unable to load sign-in. Check your connection and retry.', { exact: true }).waitFor();
    configFailure = false;
    await page.getByRole('button', { name: 'Retry sign-in setup' }).click();
    await page.getByText('Operator sign-in is not configured. Contact the administrator.', { exact: true }).waitFor();
    await expect(page.getByLabel('Email', { exact: true })).toHaveCount(0);
    await expect(page.getByLabel('Password', { exact: true })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Continue with Google', exact: true })).toBeDisabled();
    assert.equal(providerRequests, 0);
    config = { ...config, firebase_web_api_key: 'public-firebase-test-configuration' };
    await page.getByRole('button', { name: 'Retry sign-in setup' }).click();
    const googleButton = page.getByRole('button', { name: 'Continue with Google', exact: true });
    await expect(googleButton).toBeEnabled();
    await googleButton.focus();
    await page.keyboard.press('Enter');
    await expect(page.getByRole('dialog').getByRole('alert')).toHaveText(/^(Google sign-in failed\. Try again or contact the administrator\.|Unable to reach Google sign-in\. Check your connection and retry\.)$/);
    await expect(googleButton).toBeEnabled();
    assert(providerRequests > 0, 'Google SDK must attempt an intercepted provider request');
    assert.equal(sessionCalls, 0);
    await expect(trigger).toBeVisible();
    await page.keyboard.press('Tab');
    // Native dialog tab order may visit browser chrome (document.body) at its end.
    // It must never focus background page controls, and Tab returns to the modal.
    if (await page.evaluate(() => document.activeElement === document.body)) await page.keyboard.press('Tab');
    assert(await page.getByRole('dialog').evaluate(dialog => dialog.contains(document.activeElement)), 'Tab focus must remain inside sign-in dialog');
    await page.screenshot({ path: '.cache/preview/cloud-signin-fault.png' });
    assert.deepEqual(await page.evaluate(() => [localStorage.length, sessionStorage.length]), [0, 0]);
    assert.equal(new URL(page.url()).search, '');
    await page.keyboard.press('Escape');
    await expect(trigger).toBeFocused();
    slowConfig = true;
    await trigger.click();
    await expect(page.getByRole('dialog').locator('button[aria-busy=true]')).toBeDisabled();
    await expect.poll(() => !!releaseConfig).toBe(true);
    await page.keyboard.press('Escape');
    releaseConfig();
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await expect(trigger).toBeFocused();
    assert.equal(sessionCalls, 0);
    console.log('Google sign-in preparation passed: offline/missing setup, Google-only cloud UI, intercepted SDK network refusal, keyboard/focus, mobile, no persisted token and cancelled setup. No Google session established.');
  } finally { await context.close(); }
};
