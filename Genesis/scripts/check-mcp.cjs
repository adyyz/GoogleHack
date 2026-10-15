// Protocol smoke check only: initialize and list tools, never invoke a cloud tool.
const { spawn } = require('node:child_process');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const environment = { ...process.env, FIREBASE_EMULATORS_PATH: path.join(root, '.cache/firebase/emulators') };
delete environment.DEBUG;
const child = spawn(process.execPath, [path.join(root, 'node_modules/firebase-tools/lib/bin/firebase.js'), 'mcp', '--dir', root, '--only', 'auth,firestore'], {
  cwd: root,
  env: environment,
  stdio: ['pipe', 'pipe', 'pipe'],
  windowsHide: true
});
let buffer = '', finished = false;
const timeout = setTimeout(() => finish(new Error('MCP handshake timed out')), 25000);
function finish(error) {
  if (finished) return;
  finished = true;
  clearTimeout(timeout);
  child.stdin.end();
  child.kill();
  if (error) { console.error(error.message); process.exitCode = 1; }
}
function send(message) { child.stdin.write(JSON.stringify({ jsonrpc: '2.0', ...message }) + '\n'); }
child.on('error', finish);
child.on('exit', code => { if (!finished) finish(new Error('MCP exited before tools/list: ' + code)); });
child.stderr.on('data', () => {}); // Do not echo credentials or unrelated local CLI diagnostics.
child.stdout.on('data', chunk => {
  buffer += chunk.toString();
  let end;
  while ((end = buffer.indexOf('\n')) >= 0) {
    const line = buffer.slice(0, end); buffer = buffer.slice(end + 1);
    let message;
    try { message = JSON.parse(line); } catch { continue; }
    if (message.error) { finish(new Error('MCP protocol error: ' + message.error.message)); return; }
    if (message.id === 1) {
      send({ method: 'notifications/initialized' });
      send({ id: 2, method: 'tools/list', params: {} });
    }
    if (message.id === 2) {
      const names = (message.result?.tools || []).map(tool => tool.name);
      if (!names.some(name => name.includes('firestore'))) { finish(new Error('Firestore MCP tools were not advertised')); return; }
      console.log('PASS: Firebase MCP initializes and advertises ' + names.length + ' tools. No tools invoked; no cloud project selected.');
      finish();
    }
  }
});
send({ id: 1, method: 'initialize', params: { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'genesis-tooling-check', version: '1.0.0' } } });
