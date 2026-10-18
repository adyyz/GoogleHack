# Current checkout execution

This is the canonical executable ledger. The approved implementation plan adapts stale Mac statuses/paths, preserves genuine Gemini reviews, validates draft compatibility before import, scopes CSS, and separates private-cloud setup from local code completion. Root handoff files remain unchanged. Each task is verified before the next begins.

# Genesis code improvements

Updated 18 October 2026. This file is the sequential queue for code fixes. Quota processing, cloud deployment, and submission work stay in [pending-tasks.md](pending-tasks.md).

A junior developer or a single subagent takes the first `ready` task whose dependencies are `done`. Implement that task only. Set it to `done` after its tests pass. Do not start the next task in the same change.

## Task shape

- **Id:** `CI-00N`
- **Status:** `ready`, `blocked`, or `done`
- **Depends on:** earlier ids, or none
- **Files:** exact paths to read and edit
- **Current behavior:** what the code does now
- **Change:** the one result this task must produce
- **Steps:** numbered actions, including commands
- **Tests:** the command and the assertion
- **Stop:** what this task must not change

## CI-001 — Run the Python npm scripts on macOS

- **Status:** done
- **Depends on:** none
- **Files:** [package.json](../package.json), [scripts/python.ps1](../scripts/python.ps1), new `scripts/python.cjs`. Do not edit the PowerShell wrappers.
- **Current behavior:** `api`, `seed`, `test`, `bulk:generate`, and `bulk:import` call `powershell` and [scripts/python.ps1](../scripts/python.ps1). That wrapper runs `.venv/Scripts/python.exe`, which exists only on Windows. On this Mac the environment is `.venv/bin/python`, so those npm scripts cannot start.
- **Change:** those five scripts invoke Node, which selects `.venv/bin/python` on macOS and Linux and `.venv/Scripts/python.exe` on Windows, then runs the same module arguments.

### Steps

1. Add `scripts/python.cjs`. Resolve the project root as the parent of `scripts`. Choose `process.platform === "win32" ? ".venv/Scripts/python.exe" : ".venv/bin/python"`. If that file is missing, print `Missing project virtualenv. Run uv sync --python 3.12 from Genesis.` and exit 1.
2. Spawn that Python with `stdio: "inherit"` and the arguments after the script name. Exit with the child status code. Do not set `GEMINI_API_KEY`, `LIVE_AI_ENABLED`, or `CREDITS_VERIFIED`.
3. In `package.json`, replace only these five script values with `node scripts/python.cjs` plus their existing Python arguments:
   - `api` → `-m uvicorn backend.api:app --host 127.0.0.1 --port 8080`
   - `seed` → `-m backend.seed`
   - `test` → `-m pytest -q`
   - `bulk:generate` → `-m backend.bulk_dataset`
   - `bulk:import` → `-m backend.bulk_jobs --import-local`
4. Leave `dev`, `build`, browser checks, and the PowerShell tool scripts unchanged.

### Tests

From `Genesis`, with no Gemini environment variables:

```sh
node scripts/python.cjs -c 'import sys; print(sys.executable)'
```

The printed path ends in `.venv/bin/python` on macOS. `node scripts/python.cjs -c 'import backend.seed'` exits 0.

### Stop

Do not generate the corpus again, call a model, or change seed data. Do not claim this task makes `npm run emulators` work on macOS; that script still uses PowerShell.

Verified in this checkout: launcher checks cover Windows/macOS/Linux selection, inherited environment, arguments, missing virtualenv and exit status; actual Windows Python and backend.seed import passed. No seeding occurred.

## CI-002 — Report agent-drafted baseline reviews separately from Gemini

- **Status:** done
- **Depends on:** CI-001
- **Files:** [backend/seeded_baseline.py](../backend/seeded_baseline.py), [frontend/SeededHistory.tsx](../frontend/SeededHistory.tsx)
- **Current behavior:** `seeded_baseline.progress` counts every `seeded_advisory_reviews` document as `ai_reviewed_cases`. The Seeded History page shows that number as "Actual Gemini advisory reviews". After CI-003 imports 2,000 agent-drafted reviews, the page would wrongly claim 2,000 Gemini reviews.
- **Change:** progress returns `agent_draft_reviewed_cases` for documents with provenance `LOCAL_AGENT_DRAFT_ADVISORY_NOT_HUMAN`. `ai_reviewed_cases` excludes them, and `pending_ai_reviews` still subtracts every stored review. The page shows both numbers.

### Steps

1. In `progress()` in `backend/seeded_baseline.py`, replace the `reviewed = ...` line and the `return` keys with:

```python
    query = repo.db.collection('seeded_advisory_reviews').where(filter=firestore.FieldFilter('baseline_id', '==', selected['id']))
    reviewed = query.count().get(timeout=15)[0][0].value
    drafted = query.where(filter=firestore.FieldFilter('provenance', '==', 'LOCAL_AGENT_DRAFT_ADVISORY_NOT_HUMAN')).count().get(timeout=15)[0][0].value
```

   In the returned dict, use `'ai_reviewed_cases': reviewed - drafted, 'agent_draft_reviewed_cases': drafted, 'pending_ai_reviews': 2000 - reviewed`. Keep every other key.
2. In `frontend/SeededHistory.tsx`:
   - Add `agent_draft_reviewed_cases?: number;` to the `Baseline` type after `ai_reviewed_cases`.
   - Directly after the "Actual Gemini advisory reviews" `<div>`, add `<div><dt>Agent-drafted advisory reviews</dt><dd>{(data.baseline.agent_draft_reviewed_cases ?? 0).toLocaleString()}</dd></div>`.

### Tests

- `node scripts/python.cjs -m pytest -q` passes; it was 137 passed and 25 skipped before this task.
- `npx tsc --noEmit -p .` passes.
- With the emulator running, `node scripts/python.cjs -m backend.seeded_baseline status` includes `"agent_draft_reviewed_cases": 0` before CI-003.

### Stop

Do not change how reviews are created, and do not touch reserved cases or the Gemini gateway.

Verified: 140 unit passes, TypeScript pass, and local status before import reports 30 Gemini / zero drafts / 1,970 unfilled cases. Emulator integrations are run explicitly at final verification.

## CI-003 — Import the agent-drafted baseline reviews

- **Status:** done
- **Depends on:** CI-002
- **Files:** `scripts/import_agent_drafts.py`, unchanged `docs/seeded-baseline-agent-drafts.md`.
- **Current behavior before change:** 30 genuine Gemini reviews existed; missing advisory cases could not be filled while Free Tier was refusing calls.
- **Change:** validate the complete supplied draft set, preserve existing records, and import only missing agent opinions with distinct provenance.

### Steps

1. Use only local `demo-aml-insight` emulators; no model key is required. Export the current database first.
2. Run `node scripts/python.cjs scripts/import_agent_drafts.py --dry-run --allow-equivalent-baseline` from Genesis.
3. The explicit compatibility option is needed because the supplied source baseline ID differs from this checkout. Accept only the pinned document checksum, exact complete baseline membership, no reserved cases, source-matching alert mappings, valid citations/verdicts and correct manual-review flags. Validation must finish before writes.
4. Apply with `node scripts/python.cjs scripts/import_agent_drafts.py --apply --allow-equivalent-baseline`.
5. Repeat the apply command to verify zero creations. Confirm 30 Gemini, 1,970 agent drafts and zero unfilled advisory records. Export the resulting database.

### Tests and evidence

Six importer unit checks pass, including a malformed final record causing zero writes. Actual first apply created 1,970 records and preserved 30; second apply created zero. Genuine attempt, feedback, source, configuration, policy and snapshot hashes are unchanged. The isolated Firebase integration additionally exercises a fresh 2,000-draft import and idempotent repeat. Both before/after local backups exist. Windows CRLF and Unix LF are accepted without altering document content.

### Stop

Do not edit the JSON, overwrite existing reviews, call Gemini, touch reserved cases, create provider usage/attempts, or manufacture human/A5 output. Imported records use LOCAL_AGENT_DRAFT_ADVISORY_NOT_HUMAN with null run/step linkage and retain their original source baseline/checksum. Advisory coverage is not Gemini completion or genuine learning eligibility.

## CI-004 — Give the bulk state column room

- **Status:** done
- **Depends on:** none
- **Files:** [frontend/style.css](../frontend/style.css)
- **Current behavior:** the bulk table's state column holds a badge and an action button with nothing between them, so they touch. The table cells use 5px of horizontal padding, so the badge and button also press against the neighbouring columns. The header reads "Simulation state" when signed out and "Investigation state" when signed in.
- **Change:** the state cell lays its contents out with an 8px gap and 10px of padding on both sides, and it keeps at least 260px of width so the badge and button sit on one line. The shared table rules stay as they are.

### Steps

1. In `frontend/style.css`, find `.bulk-table td:last-child{min-width:180px}` and add these rules directly after it:

```css
.bulk-table th:nth-child(4){min-width:330px}
.bulk-table td:nth-child(4){padding-inline:10px}
.bulk-state{display:flex;flex-wrap:wrap;align-items:center;gap:8px}
```

2. Wrap only the state cell contents in `<div className="bulk-state">` in BulkWorkspace. Preserve native table-cell display. Leave every other rule, including `.bulk-table td:last-child>.secondary`, unchanged. The minimum width goes on the header, because a minimum width on the cell does not widen the column.

### Tests

- `npx tsc --noEmit -p .` passes.
- With the app running, open the bulk page signed out. In the "Simulation state" column the badge and its button have visible space between them and between the adjacent columns.
- Sign in and check the same column under "Investigation state".

### Stop

Do not change the cell contents, the badge colours, or the global table padding.

Verified: TypeScript and read-only browser checks pass for public/operator state cells and 320–1440px layouts. Native table cells remain intact; the inner group has an 8px gap, 10px insets and a 330px header minimum. No operator writes.

## CI-005 — Keep the local-style operator form on Cloud Run, beside Google

- **Status:** done
- **Depends on:** none
- **Files:** [backend/api.py](../backend/api.py), [frontend/main.tsx](../frontend/main.tsx), [tests/test_integration.py](../tests/test_integration.py)
- **Current behavior:** `/api/config` in cloud mode returns the Firebase web API key and no emulator URL. The sign-in dialog then shows only "Continue with Google". The local email/password form, which pre-fills `operator@aml-insight.test` / `local-demo-only`, is hidden.
- **Change:** in cloud mode the dialog still has Google sign-in, and it also shows the same email/password form. The form posts to Identity Toolkit `signInWithPassword` using `firebase_web_api_key`, then calls `/api/operator/session` as today. The UID still has to be in `OPERATOR_UIDS`. The password is not returned by `/api/config`.

### Steps

1. In `frontend/main.tsx`, `SignIn`, keep the Google branch when `config.mode === 'cloud'`. Directly under the Google button, render the existing email/password fields. Change `submit` so it also runs when `config.mode === 'cloud'`. For the Identity Toolkit URL:
   - local: keep `http://` + `auth_emulator_url` + `/identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=emulator-only`
   - cloud: `https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=` + `config.firebase_web_api_key`
2. Keep the existing Google button and `signInGoogle()`. Do not remove Google Auth.
3. On cloud, leave email and password empty until CI-006. Do not put a password into `/api/config`.
4. Copy remains: local "These fixture credentials work only with the local emulator." Cloud form label: "Operator email and password. Google sign-in stays available."
5. In `tests/test_integration.py`, next to `assert client.get("/api/config").json()["firebase_web_api_key"] is None`, add `assert "operator_password" not in client.get("/api/config").json()`.

### Tests

- `npx tsc --noEmit -p .` passes.
- `node scripts/python.cjs -m pytest -q tests/test_integration.py` (emulators running) still signs in the local operator with `operator@aml-insight.test` / `local-demo-only`.
- On Cloud Run, the dialog shows Google and the email/password form. A password typed by the operator still has to match a Firebase Auth user whose UID is in `OPERATOR_UIDS`.

### Stop

Do not return the password from `/api/config`. Do not disable Google sign-in. Do not create a Firebase user in this task.

Verified: TypeScript pass; 25 isolated Firebase integrations pass with zero skips; real local sign-in and intercepted cloud Google/password/denial checks pass. Existing Google SDK refusal, focus, memory-only storage and cancellation journey also passes. No Firebase users/providers changed.

## CI-006 — Fill the Cloud Run operator form from Secret Manager

- **Status:** done
- **Depends on:** CI-005
- **Files:** [backend/config.py](../backend/config.py), [backend/api.py](../backend/api.py)
- **Current behavior:** after CI-005 the cloud form is empty. The password for the demo operator is not in the image. Project `genesis-aicb` already has Secret Manager enabled.
- **Change:** Cloud Run maps secret `operator-demo-login` into `OPERATOR_DEMO_LOGIN`. The API reads `{email, password, uid}` from that JSON and, on `POST /api/operator/demo-login`, signs in through Identity Toolkit on the server, then returns only the Firebase `idToken`. The browser fills the form with the email, keeps the password field empty, and a "Fill operator demo login" button posts to that route. `/api/config` still does not contain the password.

### Steps

1. In Google Cloud, create secret `operator-demo-login` in `genesis-aicb` / `australia-southeast1` with JSON `{"email":"<firebase email>","password":"<firebase password>","uid":"<firebase uid>"}`. The UID must already be in `OPERATOR_UIDS` and `ADMIN_UIDS` on the web service. Do not commit the JSON.
2. Grant `genesis-demo-web@genesis-aicb.iam.gserviceaccount.com` `roles/secretmanager.secretAccessor` on that secret only.
3. Mount it on the web Cloud Run service as env `OPERATOR_DEMO_LOGIN` from `operator-demo-login:latest`. Do not mount it on the worker.
4. In `config.py`, add `operator_demo_login: str = ""`, loaded from `OPERATOR_DEMO_LOGIN`. If `APP_MODE=cloud` and the value is set, `json.loads` it and require keys `email`, `password`, `uid` as non-empty strings. If it is unset, leave the field empty. If `APP_MODE=local` and it is set, raise `ValueError`.
5. In `api.py`, `POST /api/operator/demo-login` with no Authorization:
   - 404 when `settings.mode != "cloud"` or the secret is empty.
   - Parse the secret JSON. If `uid` is not in `settings.operator_uids`, 403.
   - `POST https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={firebase_web_api_key}` with `{email, password, returnSecureToken: true}`.
   - Return `{idToken}` only. Never return the password. Set `Cache-Control: no-store`.
6. In `frontend/main.tsx` cloud mode, if `/api/config` includes `operator_demo_email` (add that string from the secret's email, still no password), pre-fill the email field. Add button "Use stored operator login" that `POST`s `/api/operator/demo-login` with no body, then calls `/api/operator/session` with the returned token, same as Google.

### Tests

- Local: `POST /api/operator/demo-login` returns 404. `/api/config` has no `operator_password` and no `operator_demo_email`.
- Cloud with the secret unset: same 404.
- Cloud with a stubbed Identity Toolkit success: the route returns only `idToken`, and a unit test asserts the password is absent from the JSON response and from `/api/config`.
- After deploy, the dialog shows the stored email. Clicking the button signs in as that UID. Google sign-in still works.

### Stop

Do not print the secret. Do not put it in the image, the repo, or `/api/config`. Do not enable Email/Password in Firebase unless it is already on. Do not change `OPERATOR_UIDS` in this task; the stored UID must already be allowlisted.

Local code verified: ten secret/authorization/transport tests, TypeScript and intercepted browser checks pass. The separate enable flag defaults off; Google and password sign-in remain independent. Cloud acceptance is PENDING under docs/operator-staging-login.md: no secret, IAM, provider or deployed configuration changed.

## CI-007 — Stop Evolution category pills wrapping mid-word

- **Status:** done
- **Depends on:** none
- **Files:** [frontend/style.css](../frontend/style.css)
- **Current behavior:** the Published Evolution brief table (`RuleCatalog` in [frontend/RuleIntelligence.tsx](../frontend/RuleIntelligence.tsx)) puts each category in a pill. Global table CSS sets `overflow-wrap: anywhere` on every cell, and later `.matrix-rule-label>.category-chip` also sets `white-space: normal; overflow-wrap: anywhere`. "Behaviour" therefore splits to `Behaviou` / `r` inside a crushed bubble. Shorter labels (`Pattern`, `Volume`, `Wire`) still look fine.
- **Change:** category pills stay on one line. The Category column is wide enough for `Behaviour` (the longest label). Other table cells still wrap as they do today.

### Steps

1. In `frontend/style.css`, find `.matrix-rule-label>.category-chip{margin:0;max-width:100%;white-space:normal;overflow-wrap:anywhere}` and replace that one rule with:

```css
.matrix-rule-label>.category-chip{margin:0;max-width:100%}
.category-chip{white-space:nowrap;overflow-wrap:normal}
```

2. Give RuleCatalog its own `rule-catalog` table class, then add a rule for that public catalog table (the one with headers Rule / Category / Trigger condition / Guard, no `matrix-data` class):

```css
.rule-catalog th:nth-child(2),.rule-catalog td:nth-child(2){width:9rem;white-space:nowrap}
```

3. Leave badge wrapping, trigger-condition wrapping, and the rule-matrix Outcomes/Configuration views unchanged.

### Tests

- `npx tsc --noEmit -p .` passes.
- Open Evolution lab signed out. In Published Evolution brief, every category pill (`Behaviour`, `Pattern`, `Volume`, `Wire`, `Identity`) is a single line with even padding. "Behaviour" does not split.
- Check the signed-in Rule matrix too: the category chip under each rule name stays on one line.

### Stop

Do not rename categories, change chip colours, or stop the trigger-condition / guard text wrapping.

Verified: TypeScript and public/operator browser checks pass. Category text has one rendered line; width rules are catalog-specific and unrelated second columns are unchanged.

## CI-008 — Bind leftover hardcoded corpus counts to the existing summary APIs

- **Status:** done
- **Depends on:** none
- **Files:** [frontend/BulkWorkspace.tsx](../frontend/BulkWorkspace.tsx), [frontend/ReferenceOverview.tsx](../frontend/ReferenceOverview.tsx), [frontend/CorpusEvolution.tsx](../frontend/CorpusEvolution.tsx), [frontend/RuleIntelligence.tsx](../frontend/RuleIntelligence.tsx), [frontend/Admin.tsx](../frontend/Admin.tsx), [frontend/SeededHistory.tsx](../frontend/SeededHistory.tsx), [frontend/SyntheticLearning.tsx](../frontend/SyntheticLearning.tsx)
- **Current behavior:** queues, cases, usage, reviews, and Evolution reports already load from Firestore and `/api/demo/bulk/summary`. Several headings and captions still hardcode 40,000 / 20,000 / 10,000 / 16,000 / 3,000. Those strings do not move when the live summary or seeded baseline counts change. The public "Reference annotations" metric is the string `20,000` even though `summary.reference_annotations` is already on the payload.
- **Change:** every leftover count interpolates a field that the page already fetches, or that `/api/demo/bulk/summary` already returns. System design stays the static explainer (`/api/system/agents`). Detector conditions, risk weights, and "All nine rules" as a catalog label stay as they are.

### UI points now live

These captions read `/api/demo/bulk/summary` or `/api/demo/bulk/reference-summary`. They are not hardcoded 40,000 / 20,000 / 10,000 / 16,000 / 3,000 strings.

**Investigations (signed out)** — `BulkWorkspace.tsx`, `ReferenceOverview.tsx`

- Dataset metric value: `summary.transactions`
- Dataset detail: identities / candidate cases / pre-evaluated walkthrough cases
- Triage progress detail: walkthrough cases evaluated separately
- Reference annotations value: `summary.reference_annotations`
- Reference annotations detail: training / sealed validation
- Queue footer: walkthrough + operational; extra training + sealed validation outside the queue
- Reference evaluation heading: `{cases}-case reference evaluation`
- Reference evaluation intro: `{population_fraction}% of the corpus`

**Evolution lab (signed in)** — `CorpusEvolution.tsx`, `RuleIntelligence.tsx`

- Scope line under “From analyst decisions to safer pre-labels”: source cases · operational cases
- Rule matrix caption: operational cases within total cases

**Admin (signed in)** — `Admin.tsx`

- “Usage and histories cover the current {cases}-case corpus”

**Seeded History (signed in)** — `SeededHistory.tsx`

- Heading: `Active {total_cases}-case baseline` (`baseline_cases` / `reserved_cases` were already live)

**Cutoff learning (signed in)** — `SyntheticLearning.tsx`

- Dataset option: `Existing corpus / {training_transactions} training references`
- Corpus-scope sentence: training references including displayed walkthrough cases
- Leave 40 / 20 / 100 on the isolated fixture option

Already live before this task, do not re-bind: queue rows, case details, genuine triage/review counts, usage/audit/runs, Evolution snapshots/reports/patterns, reference-by-rule table, System design, detector conditions, risk weights, “All nine rules”.

### Steps

1. In `frontend/BulkWorkspace.tsx`, extend `Summary` with `training_transactions`, `validation_transactions`, `initially_unprocessed`, and `reference_walkthrough_cases`. `/api/demo/bulk/summary` already returns the first three from `corpus().manifest`. For the walkthrough size, either:
   - add `"reference_walkthrough_cases": bulk_reference.SIZE` in `backend/bulk_api.py` `summary()`, or
   - use `data.cases` from `/api/demo/bulk/reference-summary` (already `10000`).
   Then replace the hardcoded strings:
   - Dataset detail: `` `${summary.identities.toLocaleString()} identities / ${summary.cases.toLocaleString()} candidate cases; ${walkthrough.toLocaleString()} pre-evaluated references` ``
   - Triage progress (signed out): drop `10,000 reference cases evaluated separately`; use `walkthrough`.
   - Reference annotations value: `summary.reference_annotations.toLocaleString()`, not `'20,000'`.
   - Reference annotations detail: `` `${summary.training_transactions.toLocaleString()} training / ${summary.validation_transactions.toLocaleString()} sealed validation; not human reviews` ``
   - Footer: `` `${walkthrough.toLocaleString()} reference + ${summary.initially_unprocessed.toLocaleString()} operational cases; ${(summary.training_transactions - walkthrough).toLocaleString()} additional training and ${summary.validation_transactions.toLocaleString()} sealed validation cases stay outside this queue.` ``
   While `summary` is null, keep showing `Loading`.
2. In `frontend/ReferenceOverview.tsx`, the heading and intro currently say `10,000-case` and `25% of the 40,000-case corpus`. `/api/demo/bulk/reference-summary` already returns `cases` and `population_fraction`. After `data` loads, render `{data.cases.toLocaleString()}-case reference evaluation` and `{(100 * data.population_fraction).toFixed(0)}% of the corpus`. Keep the loading copy until then.
3. `CorpusEvolution` and `RuleIntelligence` do not fetch the bulk summary today. Add the same `/api/demo/bulk/summary` request already used in `BulkWorkspace` (no new backend). Replace `40,000 source cases · 20,000 operational cases` and `Current corpus: 20,000 operational cases within 40,000 total cases` with `summary.cases` and `summary.initially_unprocessed`.
4. In `Admin.tsx`, replace `the current 40,000-case corpus` with the same `summary.cases` after fetching `/api/demo/bulk/summary`.
5. In `SeededHistory.tsx`, replace the heading `Active 3,000-case baseline` with `Active ${data.baseline.total_cases.toLocaleString()}-case baseline`. The dl already uses `baseline_cases` and `reserved_cases`.
6. In `SyntheticLearning.tsx`, the corpus option and the "Uses the existing 16,000 training references, including the 10,000 displayed walkthrough cases" sentence should use `summary.training_transactions` and the walkthrough size from step 1. Leave the controlled-exercise numbers (40 / 20 / 100) as they describe the isolated fixture, not the live corpus.

### Tests

- `npx tsc --noEmit -p .` passes.
- Grep the seven files for `40,000`, `20,000`, `10,000`, `16,000`, and `3,000-case`. None remain except inside comments or the fixture copy in step 6.
- Signed-out Investigations: Dataset, Reference annotations, the queue footer, and the reference-evaluation heading match `/api/demo/bulk/summary` and `/api/demo/bulk/reference-summary`.
- Signed-in Evolution lab and Admin show the same live `cases` / `initially_unprocessed` values, not the old literals.

### Stop

Do not invent counts, change Firestore writes, or rewrite System design. Do not treat synthetic references as human reviews. Leave detector rule names and "All nine rules" as the catalog size.

Verified in this checkout: all seven caption files contain no listed hardcoded corpus-count literals; TypeScript passes. Read-only browser fixtures change summary values and confirm Investigations, reference headings/coverage, Evolution, learning options and Admin follow them. Public API now supplies reference_walkthrough_cases. Fixture and detector constants remain unchanged.

## CI-009 — Remove the identity-type subtext in the bulk Identity/case column

- **Status:** done
- **Depends on:** none
- **Files:** [frontend/BulkWorkspace.tsx](../frontend/BulkWorkspace.tsx)
- **Current behavior:** each Identity / case cell is `{row.name} / {row.id.slice(0, 6)}` plus `<small>{names(row.customer_type)}</small>`. That prints `individual` or `organization` under the button. Combined with `.bulk-table td small{display:block}` it stacks extra muted text in a tight column.
- **Change:** the cell is only the existing identity button. Identity type stays on the Identity type filter and in View details (`Identity type` in the case dialog).

### Steps

1. In `frontend/BulkWorkspace.tsx`, in the bulk table body, find:

```tsx
<td><button aria-pressed={selected === row.id} className="secondary" onClick={() => navigate(() => setSelected(row.id))}>{row.name} / {row.id.slice(0, 6)}</button><small>{names(row.customer_type)}</small></td>
```

   Replace it with the same button and no `<small>`:

```tsx
<td><button aria-pressed={selected === row.id} className="secondary" onClick={() => navigate(() => setSelected(row.id))}>{row.name} / {row.id.slice(0, 6)}</button></td>
```

2. Do not delete `row.customer_type` from the `Row` type, the Identity type filter, or the View details dialog.

### Tests

- `npx tsc --noEmit -p .` passes.
- Open Investigations. The Identity / case column shows only `Morgan Example 001 / df7aa0` (and the other names). No `individual` or `organization` line under the button.
- The Identity type filter still lists Individuals / Organizations. View details still shows Identity type.

### Stop

Do not restyle the button, change pagination, or remove customer type from filters or the case dialog.
Verified: TypeScript and read-only browser checks pass; row subtext is absent, both identity-type filter options remain and View details still exposes Identity type.

## Final verification

156 unit passes; 25 isolated Firebase integrations passed with zero integration skips; six existing isolated browser journeys passed; new code-improvement browser checks passed; TypeScript/shared design/strict audit passed. Cloud acceptance for CI-006 is still pending. No model call, build, package or deployment occurred.

## CI-010 — Serve the active Firestore baseline throughout the workspace

- **Status:** done locally
- Investigations, identity filters, case reads, reference aggregates and Evolution must use the same active baseline membership, rather than the original source corpus totals.
- Build an immutable, local-only Firestore serving index from the verified 2,000 baseline and 1,000 reserved references; preserve original manifests, reviews, attempts and policies.
- Keep advisory coverage separate from genuine triage and human feedback. Never import archived reviews into the active baseline's learning metrics.
- Verify scope consistency, pagination, reserved-data boundaries, live advisory counters and public/private separation. No model requests, production build, packaging or deployment.

Verified: the local Firestore index serves 3,000 cases / 200 identities, 2,000 references and 1,000 reserved cases. Nine-rule alert totals sum to 3,929. Coverage remains 30 Gemini + 1,970 drafts; genuine human reviews in this scope are zero. The old corpus's three human reviews, reports and policies remain preserved and excluded. Missing/corrupt serving records fail closed; a test-only draft deletion/restoration proves counters refresh from Firestore.

Checks: 156 unit passes; 25 explicit isolated Firebase integrations passed, no integration skips; both read-only live-browser runners passed, including 320–1440px; TypeScript, shared design checks and strict design audit passed. Existing evidence hashes are unchanged. Local emulator exports were captured before/after indexing. See [baseline workspace](baseline-workspace.md). Genuine execution on the reference/advisory baseline remains disabled rather than routing selections into the old operational corpus.

## CI-011 — Distinguish seeded outcomes from human reviews in the rule matrix

- **Status:** done locally
- **Files:** frontend/RuleIntelligence.tsx, frontend/ReferenceOverview.tsx, read-only browser checks and UX documentation.
- **Current behavior:** the active baseline has 2,000 reference-labeled cases, but Outcomes shows only genuine human-review counts (zero), making the imported coverage invisible.
- **Change:** add a native outcome-source selector for the active baseline. Default to explicitly labeled seeded reference outcomes; retain human analyst outcomes independently. Configuration, human counts, learning gates and stored evidence remain unchanged.
1. Reuse the existing Firestore reference-summary API and its metric types. Reject a response from a different dataset; preserve loading/error states and abort stale reads.
2. Show reference-labeled alert coverage, reference TP/FP/inconclusive, conclusive reference FP share and synthetic heuristic/reference agreement. Reserved cases stay excluded.
3. Label human columns and supporting investigations explicitly. Source changes preserve the selected rule and respect the existing dirty-form guard.
4. Verify every displayed rule against the API, switch to zero human reviews, check Configuration and responsive/keyboard behavior. Run TypeScript and design checks; perform no database writes, model calls or production build.
- **Stop conditions:** never convert references or agent drafts into human verdicts, change operational eligibility or replace a missing measurement with zero.

Verified: TypeScript/shared design checks pass; read-only live browser checks compare all nine seeded rows with Firestore reference aggregates, switch independently to zero genuine human reviews, preserve Configuration and pass 320–1440px layouts. No evidence writes or model calls.

## CI-012 — Reproducible simulated analyst projections

- **Status:** done locally
- **Files:** backend/projected_reviews.py, scripts/prepare_projected_reviews.py, operator aggregate route, matrix source selector and focused tests.
- **Current behavior:** the baseline has reference/advisory labels but no projected analyst-review dataset. Genuine review counters correctly remain zero.
- **Change:** generate a separate, explicitly simulated 2,000-case dataset using 75% agreement, 20% disagreement and 5% uncertainty assignments, stratified by the nine balancing rules. It never represents human verification.
1. Validate every active baseline case and stored advisory mapping before writes; reject missing, duplicate, foreign or reserved records. Preserve frozen source/advisory hashes.
2. Allocate exactly 1,500/400/100 case assignments reproducibly. Invert conclusive advisory labels for disagreement; preserve inconclusive advisory labels and report that final uncertainty can exceed 5%. Preserve manual/protected flags.
3. Store immutable derivative records and a completed aggregate manifest with source hashes. Provide dry-run/apply, repeat safely and keep incomplete imports unpublished.
4. Explore A0 cutoffs using the existing Python fitter and projected labels only, excluding protected/missing context. Mark results synthetic training-only, unvalidated and inapplicable to operational policy.
5. Expose a separate operator-only matrix source. Verify exact allocation, all-nine-rule coverage, source immutability, reserved exclusion, idempotency, validation-before-writes and unchanged genuine learning gates. No Gemini, production build or cloud writes.
- **Stop conditions:** do not write HUMAN_OPERATOR feedback, mark cases human-verified, activate policies, manufacture real A5 evidence or claim that noisy agreement-based labels demonstrate accuracy improvement.

Verified: local run `6c97820d…` stores 2,000 simulated case projections / 2,622 alert opinions with 1,500/400/100 assignments. Every balancing rule contains disagreement and uncertainty assignments. Repeating creates zero records. All nine fitter results have no supported candidate; validation is unperformed and application unavailable. Existing source, Gemini, human-feedback and policy hashes are unchanged. The reserved 1,000 cases are excluded.

Checks: 162 unit passes; 25 explicit isolated Firebase integrations passed, zero integration skips; both read-only browser runners passed, including all three outcome sources and 320–1440px; TypeScript, shared design and strict audit passed. No Gemini requests, production build, package or deployment. See [projection walkthrough](projected-analyst-baseline.md).

## CI-013 — Genuine five-case batch through active-baseline Evolution

- **Status:** in progress
- **Files:** baseline workspace/repository, existing batch coordinator/worker, scoped analytics, local run helper and focused integration/browser checks.
- **Current behavior:** the active baseline can display projections but genuine batching is explicitly disabled. Its genuine namespace is not yet routed through the existing coordinator, feedback and A5 paths.
- **Change:** reuse the existing pipeline for explicitly selected pending reserved cases, pinning the baseline's own detector/A0 policies. Keep source records, earlier evidence and projected labels separate.
1. Add a baseline case repository restricted to the selected immutable membership, with new alerts/runs in the baseline namespace. Allow live enqueue only for reserved pending cases; keep reference cases read-only.
2. Route the existing preview/coordinator, separate local worker, alert/latest-run reads, frozen human feedback and progress through that scope. Reject stale/foreign scope and preserve completed/frozen outcomes.
   Add an operator-only Triage now button beside each pending queue row, previewing exactly that case through the shared confirmation. Display queued/paused work and prevent duplicate clicks; preserve reference and public boundaries.
3. Remove hardcoded original-corpus scope in frozen analytical inputs, usage and A5 routing. Genuine snapshots consume only real sealed investigations and HUMAN_OPERATOR feedback; projections never qualify.
4. Verify offline refusal, duplicate enqueue, scope isolation, worker checkpoints, review access and honest insufficient evidence using isolated fixtures before live requests.
5. Run five genuine cases with currently confirmed Gemini Free Tier, then stop for the user's actual alert verdicts. Freeze/analyze those reviews and inspect Evolution through its final observed-effects state; application still requires valid evidence and explicit operator decisions.
- **Stop conditions:** no synthetic human feedback, fabricated A5, unsupported policy application, production build, packaging, deployment or paid model activation. Actual model execution follows the user's explicit five-case request and current Free Tier confirmation, superseding the temporary no-Gemini code-improvement mode for this bounded run only.
