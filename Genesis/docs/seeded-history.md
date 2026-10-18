# Local seeded history

## Active 3,000-case baseline

The active practice set is now 3,000 cases: 2,000 baseline cases from 133 identities and 1,000 reserved cases from 67 different identities. Both sets cover all nine rules and both customer types. The baseline contains 1,015 individual and 985 organization cases; the reserve contains 536 individual and 464 organization cases. Rule allocation is approximately equal except DORMANT, whose available source capacity is 133 baseline / 67 reserved. Multi-rule alert counts overlap.

The baseline's existing reference labels are 987 TP, 1,001 FP and 12 inconclusive; those labels were selected from existing synthetic annotations, not invented human decisions or forced Gemini outputs. Reserved cases are excluded from the new Gemini preprocessing worker. They remain previously annotated synthetic training-source cases, not an independently untouched validation dataset. The original sealed 4,000-case validation partition is unchanged.

Preparation freezes source-record hashes in eight immutable chunks and selects a practice-only pointer. Original 10,000-case imports and earlier model attempts remain preserved; the source corpus manifest and operational policies do not change. Both the full-history worker and bulk advisory worker now respect the active baseline boundary.

```powershell
.venv/Scripts/python.exe -m backend.seeded_baseline prepare
.venv/Scripts/python.exe -m backend.seeded_baseline status
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/with-gemini-secret.ps1 -Action BaselineReview -EnableLocalGemini -LocalModel gemini-3-flash-preview
```

Bulk review sends up to five cases per generation request, with Python scores, source facts and one explicitly bounded history example per case. Omitted history counts remain recorded. Token counting enforces the existing 8,192-token input cap; an oversized group can be reduced before generation. Gemini's schema-constrained JSON output is additionally checked for exact alert references, duplicates and citation ownership. This checks structure and references, not semantic correctness. Protected signals always retain their manual-review flag; AI opinions never override A0 or become analyst verdicts.

Each successful request has one immutable EVALUATE attempt in `step_runs`. Its case reviews are committed atomically with parent completion into `seeded_advisory_reviews`, carrying REAL_PROVIDER_AI_ADVISORY_NOT_HUMAN provenance, source alert mappings and baseline ID. These records do not count as completed full investigations, human feedback or genuine calibration eligibility. Invalid responses are discarded; sanitized validation error types are retained. Repeating a stored failed request does not send it again automatically.

Actual progress at the final check: 20 baseline cases / 33 alert opinions saved from real Gemini requests; 1,980 baseline cases pending; zero reserved cases sent. HTTP 429 stopped further execution and the daily switch was disabled. No random TP/FP labels were generated, and no operational weights or cutoffs changed.

The local source UI shows the active allocation and actual advisory progress in Evolution → Practice with synthetic data → Stored seeded history. Refresh explicitly. Earlier full investigations and reference-only fitting are labeled separately.

## Earlier 10,000-case reference import

This separate practice scope contains 10,000 existing TRAIN reference cases. Its reviews are simulated reference labels, never human feedback. Records carry their actual creation time; no prior operating history is invented. Public publication, source manifests, operational reviews and active operational policies remain unchanged.

Each immutable import records computed Python risk dimensions, fixed weights, signals and evidence. Its `ai_investigation: NOT_RUN` describes import time. Current AI completion comes from separate pipeline, attempt and progress records, not changes to that immutable import.

In the local source UI, open Evolution, then Practice with synthetic data, then Stored seeded history. Refresh explicitly to see completed genuine investigations, failures, usage and model/reference comparisons. These comparisons measure agreement with synthetic references, not human agreement or population accuracy. No UI read starts a model request.

## Prepare and run

Run commands from Genesis with `APP_MODE=local`, `GOOGLE_CLOUD_PROJECT=demo-aml-insight` and `FIRESTORE_EMULATOR_HOST=127.0.0.1:8081`.

```powershell
.venv/Scripts/python.exe -m backend.seeded_history prepare
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/with-gemini-secret.ps1 -Action History -EnableLocalGemini -LocalModel gemini-3-flash-preview -HistoryCases 1
.venv/Scripts/python.exe -m backend.seeded_history status
```

Verify the key project's Free Tier before live execution. `HistoryCases 0` continues untouched prepared cases until a gate stops it. The wrapper keeps the secret in process memory and spaces token-count and generation requests at least five seconds apart. This bounds one sequential worker below 15 HTTP requests per minute; other clients share the project's quotas. Pacing cannot guarantee daily/token quota availability or provider capacity.

The worker stops on a failed case, expiry or the existing daily reservation cap, and disables the daily switch in `finally`. It skips every previously attempted case, including unknown outcomes and quota failures. It never silently retries those cases or substitutes another model. Run only one local worker.

Each actual completed investigation uses the existing A1 → A2 → A3 → A4 → A0 pipeline and immutable attempt ledger. A model failure does not create successful downstream output. Seeded feedback writes are refused; genuine human reviews belong to operational investigations.

## Learning boundary

Reference-only cutoff fitting uses the selected training cases and excludes held-out validation. Genuine completed model outputs are compared separately against reference labels, with immutable observation chunks and explicit case/identity denominators. Insufficient evidence and no beneficial candidate are valid results. Neither preparation nor evaluation changes risk weights, heuristic coefficients, detectors or operational cutoffs. No human-review gate is bypassed.

Export the local Firebase emulators after completed work. Emulator exports, secrets and local logs remain ignored and must not be published.
