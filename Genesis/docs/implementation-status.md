# Implementation status

Updated 15 October 2026, Australia/Sydney. All implementation and tooling remain inside Genesis.

## UI refinement — 15 October

The screenshot-inspired follow-up adds a sculpted sidebar selection surface, a sliding active indicator and cascading letter-roll labels (sidebar only). Summary cards now combine consistent SVG icon tiles, larger labels and right-aligned colored values. Risk tracks share one height/radius recipe, and completed workflow checks are green. The Evolution handover flow supports hover, focus and click/tap descriptions with explicit input-to-output explanations; connector arrows nudge on hover/focus. Reduced-motion mode disables all added motion.

Follow-up verification passed: production build/typecheck, token mapping, strict Premium audit (zero findings), DESIGN.md lint (zero errors/warnings), six backend tests, and expanded desktop/mobile Chromium checks covering stagger timing, stable accessible labels, summary icons, bar geometry, completed-state color, explanation hover/focus/tap, and reduced motion. No runtime dependency, cloud operation or model invocation was added.

Applied the requested Frontend Design Premium direction with Ponytail's minimal implementation approach: midnight navigation, cobalt actions, cool white investigation panels, consistent SVG icons, improved typography and a truthful evidence-to-review strip. No runtime dependencies or cloud services were added.

`DESIGN.md` records the visual system; `UX-CONTRACT.md` records canonical behavior. The shared CSS token mapping check, official DESIGN.md lint (zero errors/warnings), Premium strict static audit (zero findings), TypeScript/production build and expanded Chromium workflow check passed. Browser coverage includes search/clear/no-results, sign-in validation/failure/success, protected and missing context, discovery replay, all three screens, mobile layout, reduced motion, loading, empty results, offline failure and retry. Six backend tests passed; the emulator integration test was skipped in this UI-only verification run.

The application remains a local synthetic prototype with live AI and cloud deployment gated as described below.

## Working locally

- React/TypeScript investigation workspace, Evolution discovery diagnostic, and six-role system explanation.
- FastAPI serves the built frontend and the API on one local origin.
- Firebase Auth and Firestore emulators, with server-side token verification and an operator UID allowlist.
- 112 reproducible fictional cases: 40 discovery, 20 selection, 40 held-out, 12 interactive. Every case has a distinct customer. The manifest hash includes all source records and reference labels.
- Nine deterministic rules, integer minor-unit money, frozen synthetic FX, pre-trigger history, weighted five-dimension risk, protected signals, missing-context handling, and deterministic prioritization.
- Frozen public synthetic publication, private reference labels, append-only feedback and audit APIs, conflict checks, idempotent local seeding.
- Three allowlisted detector candidates and case-level replay, including unalerted suspicious controls and overlapping-rule retention. The UI diagnostic uses discovery only; no candidate is selected and held-out evaluation remains unopened.
- Typed AI output schemas and validators for citation IDs, uncertain/incomplete cases, protected signals, and brief length. Valid IDs do not establish semantic support.

## Verification evidence

- Frontend TypeScript check and production build passed.
- Deterministic population, boundary, future-history isolation, priority, and case-level replay tests passed.
- Real Auth/Firestore emulator integration passed: seed/reseed, persisted records, public/private separation, missing/invalid/unauthorized tokens, operator diagnostic, no feedback without completed AI triage, denied direct client Firestore reads.
- API health and built homepage returned HTTP 200 at `http://127.0.0.1:8080`.
- All seven tests passed with the emulators running (six deterministic/AI-boundary tests plus one real emulator integration workflow). The integration test skips outside an explicit emulator environment.
- Headless Chromium browser workflow passed: 12 cases, structuring protection, missing-context score abstention, Firebase operator sign-in, gated live triage, discovery replay, six-role screen, and 390px mobile layout without horizontal overflow. No browser JavaScript errors. Screenshots are local ignored artifacts under `.cache/preview`.
- No cloud resources created and no model requests sent.

## Remaining work

The Gemini gateway, durable jobs/Cloud Tasks worker, actual A2/A3/A4 narratives, live analyst review UI, feedback snapshot aggregation, A5 analysis, per-attempt usage/cost ledger, candidate selection freeze, held-out evaluation, publication of genuine AI results, cloud deployment, and submission assets are **not complete**.

The Evolution discovery diagnostic is deterministic reference replay, **not** an A5 recommendation or evidence of improved real-world detection. Public pages explicitly say that AI has not run. Live triage returns 503 rather than creating fake progress or model outputs.

The current public publication is a single bounded snapshot for 12 cases; split publication records before growing beyond Firestore's document-size limit. Source records remain separate documents.

## Cloud target and external gates

| Item | Status |
| --- | --- |
| Project ID | `genesis-aicb`, supplied by the user |
| Project number | `638299117256`, supplied by the user |
| Locally authenticated Google Cloud account | None found in the project-local CLI configuration |
| Credit type, remaining balance, expiry, eligible services | Unknown; user confirmed details are not known |
| Cloud deployment and Gemini calls | Gated pending account and credit verification |
| Team eligibility, reuse clarification, official cutoff/timezone | Still external dependencies from the master plan |

Project identifiers are recorded for later configuration; the application continues using `demo-aml-insight` locally. Do not infer that a project ID establishes active billing or usable credits. Budget alerts do not create a universal spending cap.

To inspect funding later, select the project's linked billing account in [Google Cloud Billing](https://console.cloud.google.com/billing?project=genesis-aicb), then inspect credits and expiration. Do not upgrade billing just to complete this check.

## Dependency findings

The npm advisory check reported 8 affected development-tool dependency entries (3 high, 5 moderate), concentrated in Firebase CLI's dependency tree and an installed optional native dependency. `npm audit --omit=dev` reported zero production dependency vulnerabilities. No forced downgrade or cross-major override was applied. Development tooling is not included in the static React build. Reassess the pinned Firebase CLI and its upstream fixes before public deployment; keep emulator and development servers on loopback.

## Backlog correspondence

T01 remains gated on external eligibility/funding details. T02 has a working local scaffold/build (container validation remains). T03 has source/AI schemas and provenance conventions; execution/usage version contracts remain. T05's fresh dataset is implemented. T06–T08 and T10/T13 have working local persistence, detector, enrichment, risk arithmetic and priority components; cloud and AI acceptance gates remain. T15 and T20 have partial read-only screens. T09, T11–T12, T14, T16–T19 and T21–T24 remain incomplete beyond the safeguards and diagnostic described above.

The parent master plan remains the design reference. This file records implementation evidence without modifying historical context files.
