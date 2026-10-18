// Run against isolated or local loopback API; provider/review fixtures never persist.
const assert = require('node:assert/strict');
const path = require('node:path');
process.env.PLAYWRIGHT_BROWSERS_PATH = path.resolve('.cache/playwright');
const { chromium } = require('@playwright/test');
const base = process.env.GENESIS_BROWSER_BASE_URL || 'http://127.0.0.1:8080';
const target = new URL(base);
assert(target.protocol === 'http:' && target.hostname === '127.0.0.1' && target.pathname === '/' && !target.search && !target.hash && !target.username && !target.password);
(async () => {
 const browser = await chromium.launch();
 try {
  const checks = ['bulk','learning','unified','corpus-evolution','intelligence','signin'];
  const selected = process.env.GENESIS_BROWSER_CHECKS?.split(',') || checks;
  assert(selected.length && selected.every(check => checks.includes(check)), 'Unknown browser check');
  for (const check of selected) await require('./check-' + check + '-browser.cjs')(browser, base);
  console.log('Browser journeys passed. Model success and feedback mutation fixtures are intercepted display-only evidence.');
 } finally { await browser.close(); }
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
