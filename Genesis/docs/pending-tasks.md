# Genesis: project summary and pending tasks

Updated 18 October 2026, Australia/Sydney. This is the current handoff; older reports describe earlier source and evidence checkpoints. A completed implementation, a successful fixture and a verified deployed journey are different milestones.

## Current position

CI-011/CI-012 add clearly separated matrix sources and a generated analyst projection for the 2,000 advisory cases: 1,500 agree / 400 disagree / 100 uncertainty assignments, balanced across all nine rules. These are simulated labels with separate Firestore collections; genuine human-review counts and operational eligibility remain unchanged. Python cutoff exploration found no supported candidate, so no policy or weight changed. See [projected analyst baseline](projected-analyst-baseline.md).

CI-010 corrected the main UI's data scope: Investigations, Evolution and Admin now read the active Firestore 3,000-case / 200-identity baseline. The 2,000 reference cases have 30 Gemini + 1,970 draft advisories; 1,000 cases remain reserved. Genuine human-review metrics for this scope are zero. Older corpus reviews/reports remain preserved but are excluded from this workspace. Full genuine execution in this reference/advisory scope remains disabled; it must not fall through to the old corpus. See [baseline workspace](baseline-workspace.md).

The local investigation and Evolution workflows are implemented and tested. Genuine Gemini investigations, user-saved analyst reviews and A5 results exist. The active seeded practice dataset is now 3,000 cases, split into 2,000 baseline cases and 1,000 reserved cases. Baseline advisory coverage is complete using 30 preserved genuine Gemini reviews and 1,970 separately labeled agent drafts; genuine Gemini coverage alone remains incomplete. The newest source has not been built, packaged or deployed.

| Evidence or scope | Verified position |
| --- | --- |
| Local preview | http://127.0.0.1:5173; API on 8080 |
| Local persistence | Firebase Auth and Firestore emulators; local writes do not update cloud Firebase |
| Original source corpus | 40,000 transactions/candidate cases, 500 identities; source manifest preserved |
| Genuine operational subset | 20,000 cases; three frozen human reviews, all TP; two HIGH_VALUE reviews |
| Operational pending alerts | Previously verified 17,750 awaiting triage; baseline preparation has not processed that operational backlog |
| Active seeded baseline | 3,000 existing synthetic-source cases across all nine rules |
| Preprocessing allocation | 2,000 cases, 133 identities; 1,015 individual / 985 organization cases |
| Reserved allocation | 1,000 cases, 67 different identities; 536 individual / 464 organization cases |
| Actual baseline AI progress | 30 cases / 50 alert opinions stored with successful REAL_PROVIDER attempts |
| Agent-drafted advisory reviews | 1,970 cases; LOCAL_AGENT_DRAFT_ADVISORY_NOT_HUMAN; no provider attempts or human reviews |
| Unfilled advisory cases | Zero; this does not mean all cases were reviewed by Gemini |
| Reserved Gemini activity | Zero advisory reviews and zero earlier full-investigation attempts in the selected reserve |
| Historical seeded investigations | Nine completed full Gemini case investigations / ten alerts, separate from bulk advisory reviews |
| Current genuine A5 evidence | INSUFFICIENT_EVIDENCE: three overall conclusive reviews / two HIGH_VALUE reviews |
| Operational A0 policy | Baseline TP cutoff 0.25 / FP cutoff 0.65; no supported change applied |
| Current model execution | Worker stopped; daily live switch verified disabled |

Earlier 10,000-case reference imports remain preserved as historical source records. They are not the active 3,000-case processing target. Reference labels, AI opinions, full investigations and human verdicts remain separate. The reserved 1,000 are excluded from new model preprocessing but were previously annotated synthetic source cases; they are not independently unseen validation data.

## What is complete

- [x] Implement nine deterministic detectors, identity/account linkage, available transaction history, Python risk dimensions and fixed weights.
- [x] Preserve immutable source manifests, versioned configuration, run linkage and private evidence.
- [x] Implement selected-case parent/child triage, sequential A1 → A2 → A3 → A4 → A0 execution, durable checkpoints and truthful failure states.
- [x] Integrate genuine local Gemini calls through the gated gateway, atomic reservations and the single attempt ledger.
- [x] Add A2 advisory dimensions, A3 secondary typologies, A4 confidence and expandable agent traces while preserving authoritative Python scores.
- [x] Separate A0 heuristic pre-labels from queue priority and human decisions; preserve protected and missing-context overrides.
- [x] Add investigation filters, eye/View details dialogs, queue review actions, frozen one-time feedback and transactional conflict handling.
- [x] Implement public aggregate usage, private attempt detail, operator/admin boundaries and revision-checked daily controls.
- [x] Connect Evolution's Outcomes → Understand → Learn → Apply → Observe journey to genuine corpus records.
- [x] Add the nine-rule matrix, plain-language summaries, supporting evidence, frozen A5 reports, patterns and scoped statistics.
- [x] Implement gated cutoff calibration, prospective validation, approval/application/rollback, explicit reassessment and aggregate-publication controls.
- [x] Exercise cutoff application in an isolated controlled fixture: FP boundary 0.65 → 0.40, with 25 uncertain labels resolved on 100 fixture cases; operational policy unchanged.
- [x] Remove the resource-management app dashboard and earlier Demo/Discovery operational UI/API entry points; retain saved historical evidence.
- [x] Apply shared table gutters, full-width highlights, sticky headers, darker pills, native dialogs and eight-second toast dismissal with a progress indicator.
- [x] Select and freeze the 3,000-case baseline with balanced rule strata and disjoint baseline/reserved identities.
- [x] Implement small multi-case Gemini JSON requests with schema-constrained output, exact alert matching, citation checks, bounded histories and truthful provenance.
- [x] Commit successful advisory case records atomically with parent completion; exclude reserved cases from preprocessing.
- [x] Verify the latest code with 156 unit passes and 25 explicit isolated Firebase integration passes. The normal unit command separately skips emulator tests; those skips are not the integration evidence.
- [x] Pass TypeScript, shared design checks and strict design audit; check the active baseline UI at 320, 390, 768 and 1440px with no page errors or operator mutations.
- [x] Preserve the current local database in an ignored emulator export: `.cache/ci003-after-agent-drafts-20261018`.

The existing private staging deployment, Google operator sign-in and an earlier cloud data connection were verified at previous checkpoints. They do not establish that today's local source is deployed or that cloud AI is enabled.

## Baseline advisory coverage

- [x] Preserve the 30 genuine Gemini case reviews and their attempt linkage.
- [x] Validate all supplied draft records against current case membership, source alerts, citations and manual-review flags before writes.
- [x] Import 1,970 missing drafts with distinct provenance, null provider linkage and no human-feedback claims.
- [x] Verify repeat import creates zero records; preserve source/configuration/ledger/feedback hashes and all 1,000 reserved cases.
- [x] Complete local code tasks CI-001 through CI-009; see [canonical ledger](code-improvements.md).
- [ ] Inspect semantic grounding of the agent opinions before relying on them for a practice report. Structure/citation checks do not prove the analysis is correct.
- [ ] Freeze a baseline report separating real Gemini/reference and agent-draft/reference comparisons, with exact counts and limitations.
- [ ] Run the later reserved-case walkthrough only when requested; it is not independently unseen genuine validation.

Further Gemini processing is deferred under the current no-model-call instruction. Draft coverage does not erase the 1,970 cases without actual Gemini reviews. New model execution would require explicit renewed authorization and verified Free Tier capacity. No A5 or human verdict was drafted.

See [baseline checklist](seeded-baseline.task-list.md), [scope/provenance](seeded-history.md), and [private-staging login setup still pending](operator-staging-login.md).

## Pending: demonstrate genuine learning improvement

- [ ] Investigate a diverse genuine operational sample across identities and rules through the normal UI workflow.
- [ ] Have the analyst save their own verdicts. AI advisory opinions and synthetic references cannot satisfy human-review gates.
- [ ] Reach 30 conclusive genuine reviews overall and 15 eligible scored observations for a target rule, including at least two TP and two FP identities, with compatible versions and protected-context exclusions.
- [ ] Freeze genuine evidence, run A5 if needed and prepare deterministic cutoff candidates. A5 summarizes; Python fits cutoffs independently.
- [ ] Validate each candidate once on the first five eligible future reviews from distinct identities outside training, with both verdict classes and no increase in either error direction.
- [ ] Approve and apply only a passing supported candidate, then explicitly reassess eligible unreviewed alerts.
- [ ] Measure subsequent human-reviewed outcomes and verify rollback/restoration without changing frozen reviews.
- [ ] Record no beneficial candidate or insufficient evidence honestly when appropriate. The existing `hv-15000` selection is not a supported improvement.

Only A0 cutoffs are adjustable in this main journey. Five Python risk weights, heuristic coefficients, detectors and AI execution stay fixed. Fewer uncertain labels alone does not mean fewer Gemini calls; skipping AI stages would require a separate agreed change.

## Pending: current-source private cloud integration

CI-006 local code is complete; secret creation, existing Firebase password-user verification, web-only IAM/mounting, the staging enable flag and deployed acceptance remain pending. The shortcut must be disabled and unmounted before public release.

- [ ] Review the complete source diff and update the evaluation record for the final intended scope.
- [ ] After renewed authorization to build, produce and verify a replacement package. Existing ZIPs/images are historical and predate this source.
- [ ] Confirm the concrete spending scope before another Cloud Build/image push/private-service update. Earlier single-build approvals are consumed; budget alerts are not a hard spending cap.
- [ ] Verify current cloud funding or approved spending, quotas, runtime identities, official model availability/location and applicable pricing before Vertex activation.
- [ ] Review and explicitly apply required Firestore rules/index changes. Emulator data and index checks do not deploy them.
- [ ] Deploy the reviewed source to the private web/worker services and record actual image digests and revision IDs.
- [ ] Verify real signed-in Admin behavior, private-output denial, dispatch authentication, lease/deadline recovery and duplicate delivery.
- [ ] Run a bounded genuine cloud investigation, human review and Evolution journey with measured usage/provenance.
- [ ] Confirm the deployed journey before public exposure; do not upload local private model/review records as substitute cloud execution evidence.

Cloud AI and task dispatch remain separate activation gates. No production build, deployment, paid execution or public publication was performed for the current baseline revision.

## Pending: release and submission

- [ ] Reconcile the original G01–G30 checklist with the latest implementation and evidence; do not mark cloud/release tasks complete because local code exists.
- [ ] Finalize access/privacy, source-export, dependency/license and release checks against the actual release revision.
- [ ] Create the clean public Genesis repository only after deployed integration is verified, as requested. Keep the existing private repository/history intact and exclude internal context, secrets, logs and emulator exports.
- [ ] Prepare a working signed-out public prototype URL and confirm its availability through evaluation.
- [ ] Finalize the pitch deck using the prescribed template and export the reviewed PDF.
- [ ] Record a working demo video under three minutes and verify its accessible link.
- [ ] Finalize the brief project description and all five submission deliverables: deck, video, prototype, repository and description.
- [ ] Recheck dashboard eligibility, submission destination and cutoff before submitting. The user-reported cutoff is 18 October 2026, 11:59 PM IST, equivalent to 19 October, 5:29 AM AEDT in Sydney; this document has not independently reverified the dashboard.
- [ ] Submit only after the release/publication instructions are satisfied and record the receipt and final links.

See [submission checklist](../submission/README.md), [deployment/recovery evidence](deployment-recovery.md), [implementation history](implementation-status.md) and [UI/data bindings](ui-data-bindings.md).

## Next order of work

1. Review the provenance-separated baseline and walk through the intended local UI flow together.
2. Gather genuine human evidence for supported learning; drafts do not satisfy these gates.
3. Authorize and verify CI-006 private-staging setup and final-source cloud integration separately.
4. Complete release/privacy/export checks, then the public repository and submission artifacts after deployed integration works.
