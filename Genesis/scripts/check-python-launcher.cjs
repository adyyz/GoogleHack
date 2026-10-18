const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, 'python.cjs'), 'utf8');
for (const platform of ['win32', 'darwin', 'linux']) {
  for (const exists of [true, false]) {
    let called = false, exitCode, command;
    const process = { platform, argv: ['node', 'python.cjs', '-c', 'test-only'], exit(code) { exitCode = code; throw new Error('EXIT'); } };
    const requireStub = name => name === 'node:fs' ? { existsSync: () => exists } : name === 'node:path' ? path : {
      spawnSync(file, args, options) {
        called = true; command = file;
        assert.deepEqual(Array.from(args), ['-c', 'test-only']);
        assert.equal(options.stdio, 'inherit');
        assert.equal(options.env, undefined);
        assert.equal(options.cwd, path.resolve(__dirname, '..'));
        return { status: 7 };
      }
    };
    assert.throws(() => vm.runInNewContext(source, { require: requireStub, process, __dirname, console: { error() {} } }), /EXIT/);
    assert.equal(exitCode, exists ? 7 : 1);
    assert.equal(called, exists);
    if (exists) assert(command.endsWith(platform === 'win32' ? path.join('.venv', 'Scripts', 'python.exe') : path.join('.venv', 'bin', 'python')));
  }
}
console.log('Python launcher checks passed: platforms, missing environment, arguments, environment and exit status.');
