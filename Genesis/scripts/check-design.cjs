const assert = require('node:assert/strict');
const fs = require('node:fs');
const design = fs.readFileSync('DESIGN.md', 'utf8').replaceAll('\r\n', '\n');
const css = fs.readFileSync('frontend/style.css', 'utf8');
const colors = design.match(/^colors:\n([\s\S]*?)^typography:/m)[1];
for (const [, name, value] of colors.matchAll(/^  ([\w-]+): "(#[0-9a-f]+)"/gm)) {
  assert(css.includes(`--color-${name}:${value}`), `Design color drift: ${name}`);
}
for (const [token, value] of Object.entries({ 'radius-panel': '14px', 'radius-control': '8px', 'space-panel': '24px', 'space-gap': '20px' })) {
  assert(css.includes(`--${token}:${value}`), `Runtime token drift: ${token}`);
  assert(design.includes(`"${value}"`), `Documented token drift: ${token}`);
}
for (const token of ['font-display', 'font-body', 'font-mono', 'scrollbar-thumb', 'scrollbar-track', 'scrollbar-hover', 'scrollbar-active']) {
  assert(css.includes(`--${token}:`), `Missing runtime token: ${token}`);
}
assert(css.includes('scrollbar-color:var(--scrollbar-thumb) var(--scrollbar-track)'));
assert(css.includes('@media(forced-colors:active)'));
assert(css.includes('@media(prefers-reduced-motion:reduce)'));
console.log('Design checks passed: documented palette/radii/spacing, runtime typography and global scrollbar/accessibility rules.');
