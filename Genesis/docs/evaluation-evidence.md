# Evaluation evidence

[evaluation-record.json](evaluation-record.json) captures local verification only. It records the actual base Git revision, an uncommitted-worktree flag, a fingerprint of application/test/tool/configuration sources and locks, the frozen source manifest, baseline bundle and test publication IDs. It is not a deployed revision or evidence of a completed AML investigation.

The record is generated from JUnit and advisory artifacts, not hand-entered pass counts. The source fingerprint must match the integration provenance artifact; capture refuses failed tests or skipped emulator integration. Documentation and generated evidence are excluded from the fingerprint to avoid self-reference. Re-run the checks and capture after code changes.

The unit command below also writes a source-bound receipt with the exact JUnit hash. Capture refuses a stale receipt. Public local provenance uses an explicit field whitelist. Existing public release references survive recapture with their original source binding and an explicit unverified status. An optional, separately gated read-only importer validates actual persisted cloud investigation/review/A5/freeze/comparison references; it never creates that evidence or sets readiness. See [the local integration handoff](local-integration-handoff.md) for the private input shape and remaining release checks.

From `Genesis/`:

```powershell
.venv/Scripts/python.exe scripts/capture_evaluation.py --run-unit
if ($LASTEXITCODE -ne 0) { throw 'Unit verification failed' }
$previousOptions = $env:PYTEST_ADDOPTS
try {
    $env:PYTEST_ADDOPTS = '--junitxml=.cache/integration-results.xml'
    npm.cmd run test:integration
} finally {
    $env:PYTEST_ADDOPTS = $previousOptions
}
npm.cmd audit --json | Set-Content .cache/npm-audit.json -Encoding utf8
npm.cmd audit --omit=dev --json | Set-Content .cache/npm-production-audit.json -Encoding utf8
.venv/Scripts/python.exe scripts/capture_evaluation.py
```

Capture also requires `.cache/python-audit.json`, produced by the temporary [PyPA pip-audit](https://github.com/pypa/pip-audit) invocation against `.venv/Lib/site-packages`. The audit tool was isolated in project-local uv caches; application manifests and locks were unchanged. Audits query advisory services and require network access. An audit command returning findings is not a clean result; capture retains its counts. Re-run the Python audit when dependencies change. The installed Windows environment does not establish the deployed Linux image's security state.

The access check enumerates every private API route and checks signed-out, invalid-token and unauthorized-user denial. Separate checks establish that admin membership also requires operator membership, private responses are not cached, direct authenticated Firestore reads/writes are denied, and filtered cursors/cross-dataset links are refused. These tests never create successful fake model output or human reviews.

The preserved Developer API smoke is recorded separately as connectivity-only evidence, with one generation, provider-reported tokens and unknown cost. The secret reference and payload are excluded from this report. Test fault doubles, browser display fixtures, deterministic queue hints and synthetic reference labels do not count as human feedback or a genuine investigation.

Release evidence remains explicitly missing: real investigation and manual citation grounding, analyst feedback, stored A5, explicit candidate freeze and held-out comparison, cloud identity/funding, deployed revisions, signed-out links, repository/deck/video and eligibility/cutoff. `release_ready` stays false. The local record must be supplemented by actual evidence before G26 or release can be completed.
