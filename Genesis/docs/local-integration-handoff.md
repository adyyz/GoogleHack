# Local code to cloud integration handoff

Current identity workflow checkpoint (18 October): identity filtering, A0 pre-labels, frozen analyst review, pattern memory and gated operator policy transitions are implemented and locally verified (91 unit / 13 isolated integration passes, production build and browser checks). Genuine revised parent `4480b581c44d43f7af2de0faa02bf457` and human review `68db2eb6687dedf655fb304d-1` are saved. No policy was applied. Earlier `hv-15000` is frozen and evaluated with no improvement, so it cannot qualify for application. Earlier statements below about unopened held-out data are historical. Local emulator evidence is not synchronized to cloud Firestore. Cloud build/update, Vertex activation and public publication remain gated.


Latest: user removed the special local 12-attempt ceiling; local reservations now follow the configured admin limit up to 120 (cloud configuration unchanged). Corrected-context parent `c1b25ced99e74585a2f17d94553830d6` and genuine A5 `da3c6b833d9ac65ecb634083` are complete. A5 reports actual 1 overall / 0 target-rule reviews and INSUFFICIENT_EVIDENCE. Candidate freeze remains human-owned and held-out data is unopened. Source `ab0ff27c...` passed 82 unit tests, all 12 isolated integration checks and production build; the genuine A5 UI was also verified without mutations. The checkpoint below is historical.

## Current continuation checkpoint — 17 October 2026

Local genuine investigation, both completed alert chains, the human review and immutable analytical snapshot were reverified without writes. Daily reservations are 12/12 and the expired local window is disabled. The next UTC day starts at 11:00 Sydney on 18 October. This is an application safety limit, not Google's published quota.

Remaining order: bounded local Free Tier re-enablement, one corrected-context investigation with manual currency/source grounding, genuine A5 with actual insufficient sample counts, the human operator's explicit candidate freeze, one stored held-out comparison, refreshed evidence and final package, private deployment, then funded/verified Vertex multi-model and authenticated worker testing. Preserve existing failures and human decisions. Never generate a verdict or freeze on the operator's behalf. The detailed workspace-only checklist is `docs/local-to-private-verification.md`; it is intentionally excluded from the clean source export.

Real Firebase Auth/Firestore are already connected to private staging and 12 cloud cases load. Local emulators do not synchronize their investigation/review records to cloud Firebase. Cloud AI/tasks remain off and the public repository remains on hold. A final build/update and later model activation need concrete spending scopes; prior one-build approvals are consumed.

Prepared locally on 17 October 2026. This guide does not authorize cloud writes, model calls, secret access or publication. The resource setup guide remains the ordered infrastructure runbook. Keep every AI/task switch disabled until verified funding, identities and the specific execution window are approved.

## Verify the same sources

From `Genesis/`, after edits stop:

```powershell
.venv/Scripts/python.exe scripts/capture_evaluation.py --run-unit
if ($LASTEXITCODE -ne 0) { throw 'Unit verification failed' }
$previousOptions = $env:PYTEST_ADDOPTS
try {
    $env:PYTEST_ADDOPTS = '--junitxml=.cache/integration-results.xml'
    npm.cmd run test:integration
    if ($LASTEXITCODE -ne 0) { throw 'Emulator verification failed' }
} finally {
    $env:PYTEST_ADDOPTS = $previousOptions
}
npm.cmd run build
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
# Run the documented seeded loopback API/browser journey separately.
.venv/Scripts/python.exe scripts/capture_evaluation.py
if ($LASTEXITCODE -ne 0) { throw 'Evidence capture failed' }
.venv/Scripts/python.exe -m scripts.export_source
if ($LASTEXITCODE -ne 0) { throw 'Export failed' }
```

`--run-unit` runs the existing pytest suite and binds its exact JUnit hash to the source fingerprint. Normal capture requires that receipt and matching emulator provenance. It performs no cloud reads. Documentation changes do not alter this code fingerprint; source/configuration/test/script changes require renewed verification. Build/browser and image execution remain separately recorded checks.

For a real deployment, set `DEPLOYED_CODE_FINGERPRINT` to the verified 64-character `source.code_fingerprint` from [evaluation-record.json](evaluation-record.json), identically in publisher, web and worker configuration. Cloud bundles pin that value. Record the actual committed revision and built image digests separately; a fingerprint is not a Git revision or an image digest.

## Source-only publication

The default command is entirely offline, including credential handling:

```powershell
.venv/Scripts/python.exe -m backend.publisher --project genesis-aicb --approved-manifest 9f297c1dd06ef395d9dad851348d15c5ffa4db95cedb49dc4ad7b5b36130dfa0
```

It reports the frozen manifest, source counts and public-case hash without loading settings, ADC or a client. Never use the emulator seeder or import a whole emulator export into cloud.

Actual apply is a later explicitly authorized cloud action. Start with [the approval example](../config/source-publication-approval.example.json), keep its completed copy under private `.cache/`, and review every field. Approval must identify the same verified source fingerprint, approved project/default database, frozen manifest, covered Firestore service, unexpired funding verification, exact real operator/admin UID sets and same-project publishing service account. Set `status` to `APPROVED_FOR_SOURCE_PUBLICATION` and `source_publication_authorized` to true only after that review is authorized. The supplied example refuses apply.

The process also requires cloud settings with no emulator hosts, matching verified model/location, `CREDITS_VERIFIED=true` and its verified expiry, and **all three execution switches false**. ADC must resolve to the approved attached or impersonated service account; user ADC alone is refused. No service-account key file is required. Today's stored AI switch must be disabled.

The future apply form is `python -m backend.publisher --project genesis-aicb --approved-manifest <the frozen hash> --apply --approval-file .cache/deploy/publication-approval.json`. It creates only deterministic sources/alerts, immutable configuration and the public DEMO snapshot. It creates no Auth fixture, model result or human feedback. A failed preparation preserves the prior publication; an explicit rerun first verifies persisted records and resumes missing creates. Incompatible source/configuration refuses. Unchanged publication retains its identity.

## Reviewed rate cards

[rate-card.example.json](../config/rate-card.example.json) is deliberately invalid until reviewed: `verified=false`, placeholder scope and null rates/dates. Do not switch the flag alone. Populate exact cloud model/location, applicable service/SKUs, official source, named verifier and timezone-aware effective interval. Review the supported standard on-demand text-token semantics against current official pricing. `VERIFIED_RATE_CARD_JSON` is a compact JSON configuration value, never a secret or an authorization switch.

Rates use **integer micro-USD per million tokens**: USD 1 per million becomes `1000000`. This is a unit example, not an approved price. Cached tokens are a subset of prompt tokens; uncached input is prompt minus cache. Candidate and thought tokens use the explicitly reviewed output rate. The sum rounds upward once to whole micro-USD. Only reconciled, explicit categories, zero tool tokens and a reported standard service tier qualify. Wrong model/location, expired card, unsupported tier, long context or missing categories leave cost `UNKNOWN`. Free-tier Developer API usage is not priced by this cloud card.

The card is immutable, included in the run's frozen bundle and linked from each applicable reserved attempt. New configuration never reprices an existing run. The gateway requests standard tier only when using this card. The attempt ledger remains the only accounting store. Estimates are not an invoice or verified remaining credits.

## Genuine reference capture

Normal local capture preserves valid existing public release references, labels them unverified and retains their original source binding. It never fills genuine fields from emulator or browser fixtures. `release_ready` always remains false in this local tool.

A later explicit import uses both `--release-evidence .cache/private-release.json` and `--verify-release-references`. It requires verified unexpired funded cloud settings, disabled AI/task switches, the approved project/default database and actual read authorization before constructing a client. It makes repository reads only; it does not generate, review, freeze, simulate or deploy.

The private JSON contains exactly `expected_code_fingerprint`, `expected_manifest_hash`, `cloud_read_authorized`, `manual_grounding_actor_uid` and `release_evidence`. The last object uses the fields in [evaluation-record.json](evaluation-record.json). `genuine_investigation_run_id` identifies a completed **child alert investigation**, not its batch parent. Grounding uses `{investigation_run_id, review_status, reviewed_at}` with an explicit human `PASS` assertion and timezone-aware timestamp. The private actor must match an authorized stored human review. Include actual feedback event IDs, completed A5 ID, frozen candidate hash and stored comparison ID. Do not include model output, analyst notes, credentials or held-out labels.

Verification follows the persisted sealed chain, immutable cloud bundles with the matching source fingerprint, frozen analytical inputs, real validated A5, explicit operator freeze and subsequent stored simulation. Broken, failed, unknown or unrelated references refuse before replacing the public record. Only sanitized references are exported. The tool cannot establish human semantic truth or final anonymous URL access from an ID: grounding remains a human assertion, and deployment/artifact/eligibility checks remain separate release gates.

## Clean review artifact

The exporter uses exact source/document allowlists, checks credential patterns and archive-relative links, and rejects linked or escaping paths. It does not recursively include `submission/`: historical ZIP/PDF drafts, caches and private context remain excluded. ZIP entries have stable timestamps/order and per-file SHA256s. Preserve prior archives; the new filename includes its digest. No repository is created or published.

## Remaining runtime and release gates

Docker/Podman are unavailable and WSL has no installed distribution on this workstation. Both Linux images must still be built and exercised locally with an approved engine. Static Dockerfile review and native launcher checks do not prove image behavior. No paid cloud build substitutes for that missing proof.

Real cloud IAM/OIDC/model availability, funding coverage, deployed delivery/recovery, genuine investigation and human grounding, analyst verdict, A5, explicit candidate freeze, held-out comparison, final artifact links and publication remain pending. Use [the code checklist](workstreams/code-completion.html), [infrastructure checklist](workstreams/infrastructure.html) and [submission checklist](../submission/README.md) to close those gates without rebuilding the local implementation.
