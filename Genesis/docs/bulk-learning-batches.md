# Bulk synthetic learning and case batches

Genesis now includes an additive synthetic learning workspace. The original 112-case source, publication and saved investigations remain unchanged.

## Dataset and provenance

`synthetic-bulk-v1-20261018` contains 40,000 unique transactions, 500 fictional identities (300 individuals and 200 organizations), and one candidate case per trigger transaction. Every identity has 80 linked transactions. Histories are assembled from that identity's frozen partition, with chronological 90-day evidence and the existing nine detectors/risk arithmetic.

The 20,000 preloaded annotations are scenario reference outcomes: 16,000 training transactions from 200 identities and 4,000 validation transactions from 50 different identities. Another 20,000 transactions from 250 identities begin unprocessed; 14,100 candidate cases have at least one detector alert. No-alert controls remain in the source population. Case, transaction, alert, model-attempt and review counts are separate.

References are not human decisions or Gemini outputs. Source partitions and separate indexed reference files live outside the web root. The validation cohort is denied by operational source APIs; its reference outcomes are opened only after a stored synthetic candidate freeze. The generator and seed are reproducible, so this synthetic comparison demonstrates the workflow rather than proving performance on independently collected real-world data.

Corpus manifest: `4df5fa318947ac2d158e2c1f75fdd2afe47e3ecea996c979d091a84212e2d654`. Regeneration uses a fixed seed and hashes source partitions, the queue index and reference database. Altered content under a frozen version is refused. Do not overwrite the original v1 dataset with this corpus.

## Local setup

Use the existing environment setup in the main README. With the local Firebase Auth/Firestore emulators running for `demo-aml-insight`:

```powershell
npm.cmd run bulk:generate
npm.cmd run bulk:import
npm.cmd run build
npm.cmd run api
```

The generator uses only Python and the existing engine, with no model calls. The explicit import initializes 20,000 pending-case status documents in the emulator; it skips existing documents and never resets completed or reviewed work. It refuses cloud mode. Build images generate frozen source assets under `/app/generated/bulk`; they do not publish Firestore state. A cloud status bootstrap requires a separate reviewed publication scope and must not be inferred from an image update.

In Investigations, choose **Synthetic learning / 40,000 transactions**. Native filters cover identity/type/rule and operator lifecycle state. Queue pages contain at most 100 summaries (50 in the UI); selecting a case loads its bounded identity history. Operator state uses indexed Firestore queries and count aggregations, not counts of loaded rows. Case completion summaries are recomputed in the same transaction as a completed alert/frozen review.

## Public and genuine batches

Public visitors can preview and run up to 100 eligible cases as a deterministic simulation in their tab. Python supplies source facts and frozen heuristic inputs; the browser applies the selected cutoff policy. No provider request, shared progress write, analyst feedback or fake agent trace is created. Predictions are labeled synthetic and reset on reload. Public AI/review stages remain locked; private completion is not inferred.

Operators preview and explicitly start a durable 1-100-case job. Each membership is atomically bound to the existing one-case parent and sequential alert children. Frozen reviews, completed unreviewed alerts and active work are preserved. Selection hashes pin policies; idempotency keys survive a submission retry. Restarting a coordinator reuses terminal as well as active parents instead of repeating a billed case.

Use explicit refresh. Pause/cancel controls future scheduling; sent attempts retain their actual outcomes. Capacity/expiry/switch or failed outcomes pause further scheduling. A failed member requires explicit acknowledgement before continuing other cases, and its attempt is never repeated by that acknowledgement. Unknown provider outcomes remain inspectable. A finished job with failures is reported as failed, not as all cases successfully triaged.

The existing separate local worker can drain jobs using `python -m backend.jobs --watch` within a verified temporary local Free Tier configuration. The Secret Manager wrapper supports `-Action Worker -EnableLocalGemini -Watch`; keys remain in process memory and the window expires after one hour. Today's separate admin switch/cap still applies, new UTC days start disabled, and the loop disables today's switch on exit. Without opt-in, no local model requests are possible. Cloud scheduling uses explicit `python -m backend.bulk_jobs --job <job-id>` and existing authenticated per-case task delivery; no 100-case job is run inside one bounded delivery.

The user reconfirmed the intended API-key project's Free Tier on 18 October 2026. Official [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing#gemini-3.5-flash-lite) lists free input/output for Gemini 3.5 Flash-Lite under that tier; [project-specific limits](https://ai.google.dev/gemini-api/docs/rate-limits) remain independent of the app's attempt cap. No paid model substitution or cloud activation is performed by this feature.

## Learning, outcomes and A5

Synthetic cutoff fitting reuses the existing deterministic grid search and safety comparison. Authoritative risk weights and the additive A0 formula are unchanged. Actual eligible sample counts and identity diversity are shown per rule; missing/protected examples are excluded and no candidate or improvement is guaranteed. Fit/freeze, one fixed validation, approval/rejection and application are explicit revision-checked actions. Application writes only a synthetic policy/version pointer, never an operational A0/detector pointer or genuine review gate.

Four cards distinguish dataset size, triage progress, outcomes and review/reference progress. Public training detector FPR is FP/(FP+TN), including unalerted benign controls; the operator card shows analyst FP/(TP+FP) on conclusive human reviews. These are different measures. Inconclusive/unavailable predictions remain separate. The old generic protected-signals card is replaced by contextual guards explaining mandatory analyst attention.

Genuine bulk reviews require validated completed provider steps and one transactional, frozen human verdict per alert. Large genuine analytical inputs use immutable chunks and whole-cohort aggregates; only three supporting examples and bounded narratives enter A5. Usage reduces ledger pages without the previous 10,000-row ceiling or invented token categories. The attempt ledger remains `step_runs`.

Latest genuine local evidence: case parent `33584c03d4f243dba5f362ea2cfe84d4`, case `4ef7b2d03289e52db1ccc22c`, alert `52bbd231764cb4f0a8ec7704`; the user saved its frozen review. A5 `f8297942c1020e93e4e114c4` completed against snapshot `7b9c8ff17effe1237cae3d29bb9d5da3b48fd4f2599f7a930ddb38a376d153d5` with genuine counts 1 overall / 1 target and INSUFFICIENT_EVIDENCE. Synthetic annotations did not enter those counts. This does not claim a supported detector/A0 improvement.

## Verification and release

```powershell
npm.cmd test
npm.cmd run test:integration
npm.cmd run build
npm.cmd run test:browser:isolated
```

Integration/browser commands use isolated Auth 19099, Firestore 18081 and API 18080, with all model flags off. They preserve the genuine preview on 8080/8081/9099. Tests include exact counts/provenance, reserved denial, filters/pages, duplicate starts, terminal-parent recovery, capacity/cancellation/revisions, synthetic/operational separation, and more than 10,000 usage rows. Browser checks cover a real computed 100-case public simulation with zero API mutations, private cancellation, learning, genuine-feedback refusal, keyboard/native dialogs and responsive layouts. Fault doubles never become successful provider output or human evidence.

See the final evaluation record for source-bound counts. Cloud images, real task delivery, a reviewed bulk status publication, Vertex funding/activation, public repository release and final submission remain separate execution gates. This document authorizes none of them.


## Unified queue revision

The investigation selector has been removed. The single corpus queue combines 10,000 pre-evaluated reference cases with 20,000 operational source cases. Another 6,000 training cases and the sealed 4,000-case validation cohort remain outside operational browsing. All 40,000 transactions/500 fictional identities remain in the immutable corpus.

The 10,000-case (25%) reference walkthrough is deterministic and balanced by available primary-rule, identity-type and synthetic-typology strata. Rare-rule capacity prevents exact equality, and rule counts overlap. The reference matrix reports actual outcomes, comparable-case agreement, uncertainty and baseline heuristic cutoffs. References carry SYNTHETIC_REFERENCE_WALKTHROUGH provenance, zero provider calls and zero genuine human reviews. They never generate private attempt success or feedback events. Genuine batches skip them.

Batch size/status controls lead the queue. A completed genuine row exposes Review, opening the shared analyst-only native dialog. Inspect model analysis in the selected evidence area before deciding. Drafts are guarded on close; feedback is saved once, conflicts preserve notes, and a successful verdict remains frozen. Reference previews are read-only and explicitly labeled as simulations.

Build/package/deployment work is stopped at the user's instruction. The earlier archive predates this UI revision.


## Guided controlled cutoff exercise in Evolution

Use the source preview at http://127.0.0.1:5173 while production builds are stopped. Sign in locally, open Evolution lab and select Controlled exercise / isolated fixture under Cutoff learning. This fixture proves application wiring; it does not claim predictive benefit on the 40,000-transaction corpus.

1. Prepare exercise candidate and confirm. HIGH_VALUE should propose TP <= 0.25 and FP >= 0.40, from baseline FP >= 0.65. No policy changes yet.
2. Validate candidate and confirm. The independent 20-case fixture should pass safety checks. Approval becomes available.
3. Approve candidate and confirm. The candidate becomes APPROVED; the active exercise policy still has not changed.
4. Apply cutoffs and confirm. Only the controlled exercise policy pointer changes. Genuine policies and stored reviews remain unchanged.
5. Test 100 cases and confirm. The comparison should show AUTO_TP 50 -> 50, AUTO_FP 25 -> 50, AUTO_UNCERTAIN 25 -> 0. These deliberately separable test cases make no Gemini requests.
6. Refresh learning to verify the saved result. Repeating a comparison returns the existing result; no new candidate or test cohort is created.

The existing corpus option retains its no-beneficial-candidate results. Its disabled Validate/Approve/Apply buttons are correct. Do not treat the controlled fixture's successful application as permission to apply a corpus or operational policy. Risk weights and heuristic coefficients remain fixed in both paths.
