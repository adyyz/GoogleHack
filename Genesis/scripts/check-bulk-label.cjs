// Compare the actual browser classifier to Python-produced boundary fixtures.
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const ts = require('typescript');
const source = fs.readFileSync('frontend/bulk-label.ts', 'utf8');
const javascript = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;
const scope = { exports: {} };
vm.runInNewContext(javascript, scope);
const rows = JSON.parse(fs.readFileSync(0, 'utf8'));
for (const row of rows) assert.equal(scope.exports.syntheticLabel(...row.inputs), row.expected);
console.log(`Python/browser synthetic cutoff parity passed: ${rows.length} boundaries and protected overrides.`);
