# AML Insight: architecture and implementation master plan

Planning date: **15 October 2026 — Australia/Sydney**  
Status: **Architecture documented; application implementation not started.**  
This revision incorporates the requested architecture-first sequence, per-leg costing, and Evolution proposals for prompts, skills, context, and scoring.

## 1. Read this first

1. Review [the architecture document](ai-builder-cup-architecture.html). It contains the system diagram, every execution leg, consumers, human checkpoints, Firestore field dictionary, mathematical functions, usage accounting, and evaluation policy.
2. Use [the Firestore contract](ai-builder-cup-firestore-contract.json) as the machine-readable design reference. It is not deployable SQL DDL, a Firebase migration, or an already provisioned database.
3. Follow the 24 tasks below in dependency order. Record actual evidence before marking a task complete.
4. Treat [the competition brief](ai-builder-cup-bfsi-brief.md) as sourced competition context, while the architecture defines our engineering decisions.

The original eight local references were reviewed during planning: the brief; architecture, agents and earlier update PDFs; Evolution pitch text; technical handover HTML; AML scenario HTML; and historical UI task Markdown. No old application code is available. Internal source documents must remain outside the public submission repository.

## 2. Product and fixed boundaries

Build a fresh AML investigation assistant that preserves:

**Transaction evidence → explainable triage → analyst review → feedback and usage analysis → evaluated improvement proposals.**

Primary user: AML analyst. Secondary user: monitoring lead.

The minimum complete demonstration is one genuinely executed synthetic suspicious investigation, a benign comparison, a persisted analyst decision, an Evolution proposal, and a deterministic held-out what-if comparison.

| Decision | Selected approach |
| --- | --- |
| Six roles | A1 enrichment; A2 risk; A3 categorization; A4 brief; A0 post-triage priority; A5 Evolution. |
| AI calls | Four Gemini roles; A1/A0 and other analytical services are deterministic. |
| Infrastructure | One codebase/image, public web/API and private worker Cloud Run modes; Cloud Tasks; Firestore. |
| Interaction | React/TypeScript; shared read-only published demo; verified operator-only actions. |
| Database | Cloud Firestore Standard edition, Native mode; Firebase Authentication for operator Google sign-in. |
| Evolution | Monitoring, prompt, skill, context and risk-policy proposals; isolated evaluation; human review. |
| No activation | REVIEWED/REJECTED records do not change deployed rules, prompts, skills or weights. |
| Funding | Confirmed eligible free credits only; no assumed zero-cost cloud availability. |
| Delivery | Three focused build days as an aggressive target, followed by submission checks. |

Do not build transaction blocking, account freezing, regulatory filing, actual sanctions screening, automatic code rewriting, a new ML training system, or production rule activation.

“Skills” means application role instructions, allowed tools and I/O contracts, not editor plugins. No agent framework, vector database, message-streaming platform, Kubernetes or agent-per-service deployment is required.

## 3. Competition and eligibility checks

The official material requires a fresh functioning Google Cloud prototype, Google AI integration, deployed URL, public GitHub repository, explanatory deck, and video strictly shorter than three minutes. Prepare the deck as a PDF and all materials in English.

Judging weights: technical/GenAI **40%**, alignment/impact **25%**, innovation **25%**, UX/design **10%**. The six-role architecture is our choice, not an organizer-mandated format.

Sources: [themes and requirements](https://aibuildercup.com/themes.html), [FAQ](https://aibuildercup.com/Faqs.html), [terms](https://docs.google.com/document/d/e/2PACX-1vRm7ChZ6Ij9fG7uFDkxzUMpwgVeBmnQ6cMDnAIEEX84AiLBOOQ9cYbl3S5OzFBbcVb8TF55s-eVpiXb/pub).

Before submission, confirm:

- Registered team has 2–4 eligible members and its roster is finalized.
- Rights to the historical ideas are clear; no internal material or employer assets are published.
- Organizer accepts a fresh implementation inspired by an earlier project. No confirmation has been obtained.
- New code, prompts, dataset and visuals are created during the allowed window; maintain provenance and dated commits.
- Credits, expiry, service eligibility and quotas cover the intended deployment.
- Exact dashboard cutoff/timezone is confirmed.

The [current overview](https://aibuildercup.com/) lists **18 October 2026** as the prototype deadline. Internal feature-freeze target: **17 October at 18:00 Sydney time**. Never substitute this planning target for an official cutoff. The supplied video remains unverified.

## 4. Architecture contracts

### Layers and runtime

- Presentation: React + TypeScript + Vite, component CSS/design tokens, six screens: dashboard, queue, investigation, feedback, Evolution, system.
- API: Python 3.12 + FastAPI + Pydantic; auth, validation, command dispatch and explicit publication reads.
- Intelligence: plain Python, Google Gen AI SDK structured JSON, deterministic calculation and simulation.
- Persistence: 18 Firestore collection types; source of truth is durable documents, never a separate in-memory registry.

Deployment region: australia-southeast1 for Run/Tasks/Firestore. Synthetic-data Gemini endpoint: global. Baseline model: gemini-3.5-flash, verified in the eventual credited-project smoke test. Pin tested dependency versions. Use attached service identities and Application Default Credentials, not browser model secrets.

Worker contract: persist job → dispatch outside transaction → claim 300-second lease → execute within 240 seconds → checkpoint each validated stage. Resume committed work after crashes; account for unknown provider outcomes. Avoid unawaited post-response tasks. One worker instance/concurrent request; one transient model retry; 120 reserved model attempts per UTC day including retries.

Public visitors cannot trigger Gemini, write feedback, create candidates or publish. Firebase ID tokens are verified server-side and operator UIDs allowlisted. Direct browser Firestore access is denied; server IAM and backend authorization remain essential.

### Agent sequence, outputs and consumption

| Role | Output | Consumer |
| --- | --- | --- |
| A1: deterministic enrichment | EvidenceBundle, exact facts, source IDs, missing-data flags | A2–A4 and investigator evidence panel. |
| A2: code scores + Gemini rationale | Five scores, cited signals/counter-evidence, limitations | A3/A4, score panel, evaluation. |
| A3: Gemini categorization | Typology, suggested action, uncertainty, code-derived tier | A4/A0, queue and investigator. |
| A4: Gemini brief | Cited brief under 500 words, gaps and next steps | Human review and A0 metadata. |
| A0: deterministic priority | NEEDS_CONTEXT / URGENT_REVIEW / STANDARD_REVIEW / LOWER_PRIORITY | Queue ordering; never a reviewer label. |
| A5: Evolution | Cited patterns, typed change proposals, candidate configuration versions | Evaluation, simulation, human recommendation review. |

A0 follows A4. AI confidence is not benign evidence. Protected signals are synthetic sanctions exposure, structuring, and post-death activity.

A2 calculates:
R = 0.30 transaction + 0.25 customer + 0.15 account + 0.20 behavioral + 0.10 network.
Dimensions lie in [0,1], weights sum to 1. Missing required context produces unavailable scoring/NEEDS_CONTEXT. The HTML specifies baseline signal values and tier thresholds.

Gemini never overwrites numerical statistics. Taxonomy and action enums are fixed in the architecture. Findings must cite in-snapshot evidence IDs; support still needs human evaluation.

### Firestore “DDL equivalent”

Eighteen root collection types:

- Source: datasets, customers, accounts, transactions, cases.
- Operational lineage: alerts, pipeline_runs, step_runs, feedback_events.
- Improvement: evolution_runs, patterns, recommendations, config_versions, evaluations, simulations.
- Control/publication: audit_events, publications, usage_daily.

The HTML and JSON specify fields, references, primary/unique keys, writer ownership and indexes.

No SQL linkage tables: pipeline_runs links cases/alerts/jobs/configuration; step_runs links each leg attempt to evidence, output, usage and versions; feedback_events binds judgments to an exact triage; evaluations links candidates/baselines/populations.

All dataset-scoped links are checked server-side. Firestore does not supply foreign keys or cascade deletion. Use integer minor units, explicit currencies, frozen synthetic FX, UTC timestamps and one [0,1] score scale.

Feedback and completed attempts are append-only/sealed through application APIs. Mutable job and queue projections cannot overwrite historical results. All transitions have audit events. This is an application audit trail, not certified tamper-proof storage.

### Usage and costing

The step_runs record is the attempt ledger: no second usage table that can double count it. Include run/leg/attempt IDs, parent step IDs, model/version IDs, input hash/evidence selection, timestamps, validation, raw provider usage, prompt/cache/output/thought/tool/total token counts, rate-card ID, estimated USD micros and unknown coverage.

Create the attempt and reserve its daily slot transactionally before the external call. Retrying creates a new attempt. Never call Gemini inside a Firestore transaction callback.

Unknown usage/rates remain null. Separate pre-counts from provider-reported consumption; cached prompt is a subset, and total_tokens must not be added again to component counts. Use verified non-overlapping billable categories from a versioned rate card. Unknown provider outcomes remain unknown; reconcile available billing later.

Cost of a comparison includes affected downstream legs, failures and retries. Model-token estimates exclude infrastructure bills. Record gross resource use separately from credits. Include A5’s own completed costs in later analysis.

### Context and optimization

Build full-window deterministic facts before context selection. Send a leg-specific fact registry and evidence excerpts, not the full prior prompt/history at every leg.

Initial request caps, inclusive of instructions/schema:

| Role | Input tokens | Generated tokens |
| --- | ---: | ---: |
| A2 | 4,096 | 1,536 |
| A3 | 2,048 | 768 |
| A4 | 4,096 | 2,048 |
| A5 | 8,192 | 3,072 |

Verify model-specific thinking/output accounting during integration. Pre-count exact payloads. Keep protected sequences, chronology, counter-evidence, units and source IDs. Essential evidence exceeding budget produces an explicit failure/review state, not silent truncation.

Evolution can propose one changed component at a time: prompt, skill, context policy, or risk-weight pair. Weight experiments shift at most five percentage points between two dimensions per candidate, preserve nonnegativity and sum=1, and do not relax protected-signal gates.

Initial engineering ranking:
J = 0.50(cost ratio) + 0.20(p95 latency ratio) + 0.30(FPR / max(baseline FPR, 0.01)).
Rank only candidates satisfying every quality gate. Cost/latency denominators must be positive and comparable; otherwise show separate metrics and insufficient optimization evidence. These coefficients are not competition judging weights.

No activation follows evaluation or human review. Versioned candidate artifacts are available for a separately authorized future release.

## 5. Data and evaluation

Generate **112 fresh case bundles** with disjoint fictional customers and scenario variants:

- 40 calibration-discovery: hypothesis/pattern analysis; at least 30 high-value examples with benign/suspicious variation.
- 20 calibration-selection: compare candidates; do not expose these labels to proposal prompts.
- 40 held-out: freeze candidate before evaluation; do not tune on results.
- 12 demo: live investigation journey.

Store reference labels privately, separate from scripted historical review labels and actual operator feedback. Do not seed fake AI outputs.

Nine detector rules: high value >AUD 10k; crypto; PEP; post-death; dormancy >=365 days; >=3 currencies in 30 days; cash >50% of 30-day absolute volume; non-AUD wire; >=3 cash deposits in 72 hours, each AUD 8k–under 10k, totaling >AUD 20k. These are demo settings, not legal reporting requirements.

Supported detector candidates: high-value threshold 15k/20k, or expected-activity exemption for accounts >=365 days, >=30 comparable historical transactions, amount within 2 standard deviations, no protected signals.

Discovery statistics require 30 conclusive reviews total and 15 per target rule before a detector proposal. Other missing/insufficient populations must be reported.

Compute case-level TP/FP/TN/FN across the full population, including non-alerted cases. Detector positive means any rule retains an alert. Separate AI-assistance mapping: any ESCALATE/REVIEW is positive; all MONITOR/CLOSE is negative; incomplete/unvalidated is abstention. Freeze mapping versions.

Report precision, recall, FPR, effective suspicious-case recall including abstentions, alert-noise proportion, valid/actually-supported citations, latency, tokens, failures/retries, cost coverage and sample sizes. Null denominators are unavailable, not perfect performance.

Paired candidate gates: no additional suspicious misses; no worse effective recall/precision; no increased abstention or validation failures; valid citation IDs; non-degraded manually assessed support; no protected-field loss. A minimum grounding smoke check covers five paired cases with protected/counter-evidence examples; this is not statistical validation.

Choose candidate on selection cases; seal it before held-out replay. Reuse identical cases/configurations except the intended change. A failed gate yields FAIL; absent evidence yields INSUFFICIENT_EVIDENCE. Never claim expected savings as measured results.

Core delivery requires one real A5 recommendation and deterministic held-out detector simulation. Prompt/skill/weight optimization experiments are credit- and time-gated; drafts can exist without replay, but remain UNEVALUATED.

## 6. Delivery timeline

| Window | Focus | Exit evidence |
| --- | --- | --- |
| Architecture first | HTML flow, schema contract, math/usage design, this plan | Internally consistent documentation; completed in this documentation pass only. |
| Day 1 | T01–T09; begin T10–T14 | Credits and cloud verified; dataset frozen; one alert through worker. |
| Day 2 | Finish T10–T16; T17–T20 | Investigator review and a grounded Evolution proposal + simulation. |
| Day 3 | T21–T24 | Security/evaluation checks, published demo, repository/deck/video. |

This is dependency order, not a guaranteed hour-by-hour estimate. T01 external checks proceed alongside local T02/T03/T05. Application tasks are pending. Missing credits block live calls/deployment, not local code and deterministic tests. No requirement is waived because a deadline is close.

If time slips, drop decorative UI, extra charts, and optional optimization replays first. Keep six roles, evidence, review, durable state, one evaluated detector proposal and required artifacts.

## 7. Twenty-four implementation tasks

### T01 — Eligibility, credit and deadline register
Dependencies: none. Status: **PENDING external confirmation**.
Deliver: team/rights/provenance status, organizer reuse clarification, exact cutoff, credit balance/expiry/service coverage and quotas.
Acceptance: no unsupported eligibility/zero-cost claim. Do not contact organizers without explicit messaging authorization.
Evidence: user-supplied confirmation/dashboard facts and credit verification; no secrets in docs.

### T02 — Fresh application foundation
Dependencies: none. Status: **PENDING**.
Deliver: React/TypeScript/Vite frontend, FastAPI/Pydantic backend, one multi-stage container image, environment template, pinned dependencies and local commands.
Acceptance: build/typecheck, health endpoint and startup work. Check actual Python/container tooling rather than assuming it exists.
Evidence: command outputs and runtime versions.

### T03 — Typed contracts and provenance
Dependencies: T02. Status: **PENDING**.
Deliver: implement the documented data schemas, role enums, evidence IDs, score/money/time rules, config bundles, prompt versions and public projections.
Acceptance: reject bad scores, mixed currency amounts, unknown enum values, cross-dataset links and reference-label leakage.
Evidence: focused contract tests.

### T04 — Credited Google Cloud foundation
Dependencies: T01–T03. Status: **PENDING credits/project**.
Deliver: project services, least-privilege IAM, Firestore, Firebase Google operator sign-in, Tasks queue and both Run modes.
Acceptance: real authenticated Gemini smoke call, verified operator UID, unauthorized worker invocation denied.
Evidence: project/service/revision identifiers and redacted smoke-test result.

### T05 — Synthetic data and frozen splits
Dependencies: T03. Status: **PENDING**.
Deliver: deterministic generator, 40/20/40/12 manifest, new fictional records, all scenario families, negative/non-alerted cases and explicit label provenance.
Acceptance: exact count 112; no customer overlap; reproducible hash; source/reference labels not in triage prompts.
Evidence: manifest and generator checks.

### T06 — Firestore repositories and integrity
Dependencies: T03–T05. Status: **PENDING**.
Deliver: collection repositories, transaction boundaries, indexes, seed idempotency, append-only events, size/array limits.
Acceptance: restart retains state, second seed does not duplicate, feedback conflicts detected, references validated.
Evidence: emulator/integration tests; document where cloud verification is absent.

### T07 — Detection and stable alert generation
Dependencies: T05–T06. Status: **PENDING**.
Deliver: nine versioned rules; stable hash key across completed rescans; multi-rule case links.
Acceptance: threshold/time/currency boundaries and overlapping rules produce expected matches, without future look-ahead.
Evidence: deterministic fixtures.

### T08 — A1 enrichment and context projection
Dependencies: T07. Status: **PENDING**.
Deliver: full-window facts, compact fact registry, source map, selection manifest, missing-history flags and protected-context policy.
Acceptance: hand-calculated values match; future rows excluded; no zero-as-missing confusion; essential over-budget context fails visibly.
Evidence: chronology, missing-data and protected-sequence tests.

### T09 — Model gateway and attempt accounting
Dependencies: T03–T04. Status: **PENDING**.
Deliver: current Gen AI SDK client, structured outputs, token pre-counts, usage metadata, versioned rate mapping, reservations, kill switch and bounded retries.
Acceptance: each attempt—including failed retries—has a ledger record; unknown stays null; no request without credits/limit permission.
Evidence: one real call plus mocked fault tests; do not publish test mocks as model output.

### T10 — A2 risk and explanation
Dependencies: T08–T09. Status: **PENDING**.
Deliver: numerical policy from the architecture; fixed weights; cited Gemini explanation and counter-evidence.
Acceptance: model cannot override scores; unavailable dimension produces NEEDS_CONTEXT; unknown citations rejected.
Evidence: formula checks and selected live result.

### T11 — A3 categorization and suggestion
Dependencies: T10. Status: **PENDING**.
Deliver: constrained taxonomy/action schema, qualitative uncertainty, deterministic tier and protected-signal warnings.
Acceptance: unsupported enum/evidence fails; uncertainty does not imply benign.
Evidence: contract tests and live example.

### T12 — A4 investigation brief
Dependencies: T11. Status: **PENDING**.
Deliver: structured <500-word brief with references, counter-evidence, missing information and suggested next steps.
Acceptance: real execution stored, selected claim support manually checked, no claim of performed banking/legal action.
Evidence: grounded example and failure case.

### T13 — A0 review prioritization
Dependencies: T12. Status: **PENDING**.
Deliver: deterministic precedence and explicit reasons; no FP probability or automatic reviewer verdict.
Acceptance: missing-context/protected-signal tests; stable ordering; no writes to feedback labels.
Evidence: priority decision table tests.

### T14 — Durable orchestration and recovery
Dependencies: T06, T08–T13. Status: **PENDING**.
Deliver: parent/child jobs, leased claims, stage checkpoints, dispatch generations, private task invocation, terminal failure/retry links.
Acceptance: duplicate delivery/restart resumes correctly; unknown external outcome retained; terminal model failures do not produce endless retries.
Evidence: crash/dispatch/duplicate/timeout tests.

### T15 — Dashboard, queue and live progress
Dependencies: T07, T14. Status: **PENDING**.
Deliver: real database views, public publication routes, private operator list/detail routes, filters, bounded polling and visible failures.
Acceptance: no fake telemetry; public writes denied; polling stops at terminal state.
Evidence: API checks and browser journey.

### T16 — Investigation, feedback and human checkpoint
Dependencies: T12–T15. Status: **PENDING**.
Deliver: transaction trail, evidence links, risk/finding panels, persisted review, revision conflict handling and feedback history.
Acceptance: alert → investigation → decision survives reload; latest valid revision is clear.
Evidence: end-to-end operator test.

### T17 — Frozen feedback and usage statistics
Dependencies: T06, T16. Status: **PENDING**.
Deliver: immutable snapshot IDs, computed denominators, grouping, sample gates, label provenance and cost-coverage summaries.
Acceptance: predictions never become human truth; repeated snapshot not new evidence; unknown cost visible.
Evidence: known-count fixtures and snapshot-hash checks.

### T18 — A5 proposals and immutable configuration versions
Dependencies: T09, T17. Status: **PENDING**.
Deliver: grounded patterns and detector/context/prompt/skill/risk proposals, component diff, hypothesis, supporting IDs and intended evaluation.
Acceptance: writes new candidate versions only; validates allowlisted changes; no activation endpoint; own usage visible to later runs.
Evidence: proposal-schema tests and one real Evolution report.

### T19 — Simulation and optimization evaluator
Dependencies: T07, T17–T18. Status: **PENDING**.
Deliver: rule replay plus generic paired evaluator for configuration candidates; freeze candidate before held-out; include downstream usage.
Acceptance: correct case deduplication and other-rule retention; no missed-case/abstention gaming; cannot rank missing cost/quality evidence.
Evidence: detector fixtures; credited prompt replay only if available, otherwise explicitly UNEVALUATED.

### T20 — Evolution, usage and system screens
Dependencies: T18–T19. Status: **PENDING**.
Deliver: sample sizes/provenance, usage per leg/configuration, proposal diff, metrics, review/reject notes, six-role system explanation.
Acceptance: REVIEWED never appears as applied; static and live results distinguished; real charts only.
Evidence: inspection and browser checks.

### T21 — Security, privacy and credit controls
Dependencies: T04, T14–T20. Status: **PENDING**.
Deliver: endpoint authorization, direct Firestore denial, publication sanitization, log redaction, input controls, kill switch and daily attempts cap.
Acceptance: signed-out visitor cannot mutate/trigger model/read private labels/prompts/identity; no committed secrets.
Evidence: negative auth, leakage and limit tests.

### T22 — Evaluation and regression record
Dependencies: T16–T21. Status: **PENDING**.
Deliver: deterministic regression, selected real AI examples, manual grounding, paired detector results, browser/restart checks, explicit limitations.
Acceptance: all metrics linked to manifest/config/run IDs; no unrun experiment presented as successful.
Evidence: evaluation JSON/report and reproducible commands.

### T23 — Deployment and explicit demo publication
Dependencies: T21–T22. Status: **PENDING credits/project**.
Deliver: deployed revision IDs, validated synthetic snapshot, read-only public URL, operator smoke test, recovery/kill-switch instructions.
Acceptance: signed-out demo journey works without triggering AI; real outputs retain source lineage.
Evidence: literal URL and deployment results, not inferred success.

### T24 — Submission package and final checklist
Dependencies: T22–T23. Status: **PENDING**.
Deliver: new public repository excluding internal context; README; fresh architecture/business-case deck PDF; <3-minute demo; final artifact checklist.
Acceptance: links work signed out; deck/video agree with measured behavior; eligibility and cutoff confirmed; no unsupported compliance/performance statements.
Evidence: artifact URLs, video duration and final checks. Publication is not automatic from documentation creation.

## 8. Release gates and acceptance

1. Foundation: credits, identity, model, persistence and private worker verified.
2. Investigation: one genuinely executed case with evidence and persisted human feedback.
3. Evolution: valid feedback/usage snapshot, real proposal and held-out deterministic comparison.
4. Access: public read-only; no public model/mutation path.
5. Submission: URL, repository, PDF deck and short video verified.

Preserve failed gates explicitly. Do not replace unavailable model execution with invented summaries or declining metrics.

Suggested 2:40 video: problem (0:00–0:20); investigation/review (0:20–1:10); Evolution/evaluation (1:10–2:00); architecture (2:00–2:25); measured outcomes and limitations (2:25–2:40).

Documentation itself creates no cloud resources, models, database collections, billing configuration, runtime code or public submission.

## 9. Current handoff

Completed in this pass: architecture HTML, Firestore JSON design contract, timeline and 24-task implementation documentation.

Documentation verification: run `node context/check-architecture.cjs` from the workspace root. This checks HTML/JSON consistency, collection relationships, local links, script syntax, the illustrative risk function and task IDs. It does not test browser rendering, provision Firestore, validate external URL availability or execute the planned application.

Not completed: application code, schema enforcement, tests of application behavior, live Gemini calls, cloud deployment, evaluation experiments or submission artifacts.

External dependencies: organizer reuse/rights clarification, finalized eligible team, credited Google project/quotas, operator UID and exact submission cutoff/timezone.

For contradictions between historical material and this revision, use this revision's explicit choices. If the architecture HTML and JSON contract diverge during implementation, fix both before changing the application.

