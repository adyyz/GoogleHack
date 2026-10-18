# Active Firestore baseline workspace

The local preview at http://127.0.0.1:5173 uses the baseline selected by `seeded_baseline_state`. Its authoritative serving index is in Firestore, not the original SQLite corpus summary. The frozen source corpus remains available for verified transaction trails; it is not the active queue population.

Current scope: 3,000 cases, 200 identities, 3,929 overlapping rule alerts. There are 2,000 reference/advisory cases and 1,000 reserved cases. Advisory coverage is 30 genuine Gemini cases plus 1,970 agent drafts, with no unfilled advisory slots. There are zero genuine human reviews belonging to this active scope. Three older operational human reviews and their A5 reports are preserved separately and never added to these counters.

## Local setup and recovery

Run from Genesis with Auth/Firestore emulators running. These commands validate frozen references and create only an immutable serving index; they do not reset data or call a model.

```powershell
$env:APP_MODE='local'
$env:GOOGLE_CLOUD_PROJECT='demo-aml-insight'
$env:FIRESTORE_EMULATOR_HOST='127.0.0.1:8081'
$env:FIREBASE_AUTH_EMULATOR_HOST='127.0.0.1:9099'
node scripts/python.cjs scripts/prepare_baseline_workspace.py --dry-run
node scripts/python.cjs scripts/prepare_baseline_workspace.py --apply
```

The index contains eight content-addressed `baseline_workspace_chunks` and one `baseline_workspace_views` document keyed by the selected baseline hash. Preparation validates every source history before the first write, is emulator-only and idempotent. No source manifest, baseline membership, provider record, human feedback or policy is modified. A missing or damaged index produces an error rather than silently returning the old corpus.

Preview exports: `.cache/ci010-before-workspace` and `.cache/ci010-after-workspace`. Restart the local preview using the latter snapshot, or run the indexing commands after restoring an earlier snapshot. These untracked local files must never be published.

## Boundaries and verification

- Investigations, identities, reference aggregates, private review summary, matrix, report histories, policy reads and Admin use the same selected baseline scope. Linked advisory attempts contribute measured usage; drafts never create attempts.
- Reserved cases expose source evidence but no reference verdict, prediction or typology. Reserved labels do not enter reference metrics, fitting or validation.
- Reference fitting uses only the active 2,000 reference cases. Independent validation is unavailable for this previously annotated reserve; genuine learning gates still require genuine human feedback.
- Full Gemini triage on this reference/advisory baseline is not enabled. The UI and API refuse execution here instead of submitting these selections to the earlier operational dataset. No execution was requested by this data-wiring change.
- The controlled 100-case exercise keeps its isolated scope. Public visitors receive safe counts/references, never private human notes or case-level model output.

Checks: `npm test` (156 passes), `npm run test:integration` (25 passes with zero integration skips), `node node_modules/typescript/bin/tsc --noEmit`, both `check-code-improvements-browser.cjs` and `check-baseline-workspace-browser.cjs`, shared design checks and strict audit. Browser checks cover 320–1440px. Existing evidence hashes match the pre-change checkpoint. No production build, package, deployment or model request occurred.
