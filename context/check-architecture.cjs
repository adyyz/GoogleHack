// Run: node context/check-architecture.cjs — documentation checks, no cloud calls.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const read = file => fs.readFileSync(path.join(__dirname, file), 'utf8');
const html = read('ai-builder-cup-architecture.html');
const plan = read('ai-builder-cup-implementation-plan.md');
const contract = JSON.parse(read('ai-builder-cup-firestore-contract.json'));
const embedded = JSON.parse(html.match(/<script id="schema-data" type="application\/json">([\s\S]*?)<\/script>/)[1]);
assert.deepEqual(embedded, contract, 'HTML and JSON contract diverged');
assert.equal(contract.collections.length, contract.collection_count);
assert.equal(contract.collection_count, 18);
const collections = new Set(contract.collections.map(item => item.name));
assert.equal(collections.size, 18);
for (const collection of contract.collections) {
  for (const link of collection.links) assert(collections.has(link), 'Missing collection: ' + link);
}
for (const [collection] of contract.indexes) assert(collections.has(collection));
const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
assert.equal(new Set(ids).size, ids.length, 'Duplicate HTML IDs');
for (const [, ref] of html.matchAll(/\bhref="([^"]+)"/g)) {
  if (/^https?:/.test(ref)) continue;
  if (ref.startsWith('#')) assert(ids.includes(ref.slice(1)), 'Missing anchor: ' + ref);
  else assert(fs.existsSync(path.join(__dirname, decodeURIComponent(ref))), 'Missing local link: ' + ref);
}
assert(!/__(FLOWS|COLLECTIONS|SCHEMA)__/.test(html), 'Unexpanded placeholder');
assert(!/<script[^>]+src=|<link[^>]+href=|\bfetch\(/.test(html), 'Unexpected runtime dependency');
const script = html.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
new vm.Script(script); // Compile without requiring a browser.
const calculator = script.slice(script.indexOf('function calculateRisk'), script.indexOf('function updateRisk'));
const scope = {};
vm.createContext(scope);
vm.runInContext(calculator, scope);
const weights = [30, 25, 15, 20, 10];
const scores = [.7, .1, .1, .6, .4];
assert(Math.abs(scope.calculateRisk(scores, weights).risk - .41) < 1e-12);
assert.equal(scope.calculateRisk(scores, weights).tier, 'MEDIUM');
assert(scope.calculateRisk(scores, [40, 25, 15, 20, 10]).error);
assert(scope.calculateRisk([NaN, .1, .1, .6, .4], weights).error);
assert(scope.calculateRisk([1.1, .1, .1, .6, .4], weights).error);
assert.equal(scope.calculateRisk([0, 0, 0, 0, 0], weights).tier, 'LOW');
assert.equal(scope.calculateRisk([1, 1, 1, 1, 1], weights).tier, 'CRITICAL');
const taskIds = [...plan.matchAll(/^### (T\d{2}) —/gm)].map(match => match[1]);
assert.equal(taskIds.length, 24);
for (let number = 1; number <= 24; number++) assert(taskIds.includes('T' + String(number).padStart(2, '0')));
const markup = html.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, '').replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, '');
const stack = [];
const voidTags = new Set(['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr']);
for (const [, closing, name] of markup.matchAll(/<(\/?)([a-z][a-z0-9-]*)\b[^>]*>/gi)) {
  const tag = name.toLowerCase();
  if (voidTags.has(tag)) continue;
  if (closing) assert.equal(stack.pop(), tag, 'Unbalanced HTML: ' + tag);
  else stack.push(tag);
}
assert.equal(stack.length, 0, 'Unclosed HTML');
console.log('PASS: schema consistency, 18 collection links/indexes, anchors/local files, standalone HTML/JS, risk calculator and 24 tasks.');
console.log('Limit: static checks only; no browser rendering or cloud/application behavior verified.');
