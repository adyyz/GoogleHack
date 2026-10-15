// Executed by Firebase emulators:exec; never contacts a real Firebase project.
const assert = require('node:assert/strict');
async function main() {
  const firestore = process.env.FIRESTORE_EMULATOR_HOST;
  const auth = process.env.FIREBASE_AUTH_EMULATOR_HOST;
  for (const host of [firestore, auth]) {
    assert(host && /^(127\.0\.0\.1|localhost):\d+$/.test(host), 'A loopback emulator host is required');
  }
  const firestoreResponse = await fetch(`http://${firestore}/v1/projects/demo-aml-insight/databases/(default)/documents/health`, { signal: AbortSignal.timeout(5000) });
  // The emulator must be reachable and direct client reads must be denied by our rules.
  assert.equal(firestoreResponse.status, 403, 'Direct Firestore client reads must be denied');
  const authResponse = await fetch(`http://${auth}/emulator/v1/projects/demo-aml-insight/config`, { signal: AbortSignal.timeout(5000) });
  assert.equal(authResponse.status, 200, 'Auth emulator must respond');
  console.log('PASS: local Auth and Firestore emulators respond; direct Firestore reads are denied.');
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
