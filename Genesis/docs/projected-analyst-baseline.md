# Simulated analyst baseline

The active 3,000-case local workspace contains 2,000 reference/advisory cases and 1,000 reserved cases. The 2,000 advisories came from 30 genuine Gemini case reviews and 1,970 coding-agent drafts. Neither source is a human verdict.

At the operator's request, Python created a separate reproducible projection for each of the 2,000 advisory cases:

| Case assignment | Cases | Meaning |
| --- | ---: | --- |
| Agree | 1,500 | Keep each alert's advisory verdict |
| Disagree | 400 | Invert a conclusive TP/FP advisory; preserve an inconclusive advisory |
| Uncertain | 100 | Project inconclusive for every alert on that case |

Largest-remainder allocation spreads the exact global split across all nine balancing rules. A content-hash ordering selects cases within each rule reproducibly. Multi-rule alert counts overlap. The percentages describe **case assignments**; final inconclusive verdicts can exceed 5% because existing advisory uncertainty remains intact. No fabricated opposite verdict is assigned to an inconclusive advisory. Manual/protected flags are preserved.

These are generated test labels, **not human-verified outcomes**. Agreement with an advisory is not evidence of accuracy. Randomly injected disagreement can introduce noise. The projections can exercise the learning/reporting machinery, but they cannot establish that a real decision was correct or qualify an operational policy for application.

## Local generation

Run from Genesis with the retained local Firestore/Auth emulators running:

```powershell
$env:APP_MODE='local'
$env:GOOGLE_CLOUD_PROJECT='demo-aml-insight'
$env:FIRESTORE_EMULATOR_HOST='127.0.0.1:8081'
$env:FIREBASE_AUTH_EMULATOR_HOST='127.0.0.1:9099'
node scripts/python.cjs scripts/prepare_projected_reviews.py --dry-run
node scripts/python.cjs scripts/prepare_projected_reviews.py --apply
```

All 2,000 source advisories, case/alert mappings, citations and manual-review flags are validated before the first write. Missing, duplicate, foreign, reserved or malformed records refuse the import. Source hashes are frozen in each derivative record. Repeating the same generation creates zero additional records.

Storage is separate: `projected_analyst_reviews` contains immutable per-case bodies, `projected_review_runs` contains the completed aggregate manifest and references, and `projected_review_controls` selects that completed run. No `feedback_events`, provider attempts, source cases, active policies or genuine analytical snapshots are created or rewritten. The manifest is published only after every derivative row exists. Partial imports can be resumed by repeating the command.

Current method: `projected-analyst-75-20-5-v1`. Verified run: `6c97820dc93014ff7694f26ed07a18ec2760c2d7e43d4cd58c7987550bc2c932`. It contains 2,000 case projections covering 2,622 alert opinions. Genuine human reviews created: zero. Model calls: zero. Reserved cases processed: zero.

## Inspect in the UI

1. Open http://127.0.0.1:5173, hard-refresh and sign in locally.
2. Open **Evolution lab → Understand → Rule matrix → Outcomes**.
3. Choose **Simulated analyst projections** to see projected TP/FP/inconclusive counts and advisory/projection agreement for each rule. This is the initial view when a projection exists.
4. Choose **Seeded reference outcomes** for the original reference labels and heuristic/reference comparison.
5. Choose **Human analyst outcomes** for genuine frozen verdicts. The current baseline has zero; earlier corpus reviews remain preserved separately.
6. Expand **Simulated cutoff exploration — training only** to inspect the existing Python fitter's results against projected labels and frozen source-case heuristic scores. Protected/missing-context observations are excluded. The current run found no supported candidate for any rule; baseline cutoffs remain TP ≤0.25 / FP ≥0.65.

No independent validation was performed. Projected training results have no operational Apply action and never satisfy genuine review/identity/prospective-validation gates. Future genuine cases still require real investigations and human decisions. Scores, risk weights, coefficients and active A0/detector policies remain unchanged.

The operator-only `/api/operator/bulk/projected-reviews` read returns aggregate results, not per-case opinions. Public visitors cannot access the projection endpoint. Reading or refreshing never generates records, starts A5 or calls a model. The public catalog and explicit-publication boundary are unchanged.

Local backups are under `.cache/ci012-before-projected` and `.cache/ci012-after-projected`; the preview launcher imports the latter. They are untracked and must not be published. No production build, packaging, deployment or paid execution occurred.
