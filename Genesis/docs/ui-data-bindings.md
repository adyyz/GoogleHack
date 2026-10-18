# UI data binding review

The source UI uses the same application and local Firebase records. This review does not establish cloud deployment readiness or authorize model calls.

| Display | Source and boundary | Empty or unavailable state |
| --- | --- | --- |
| Active 3,000-case baseline | Integrity-checked baseline manifest/chunks and aggregate count of successful `seeded_advisory_reviews` for its ID | No baseline falls back to stored history; pending and reserved are separate, never invented model completions |
| Stored seeded history | Operator-only seeded-history read; immutable reference imports, actual pipeline/attempt ledger and frozen chunked comparisons in a separate dataset | Pending means no completed AI case; simulated reference reviews never count as human feedback |
| Queue filters, counts and pagination | Bounded corpus case APIs; source identity catalog plus operational progress records | Loading/no matches; no invented completed cases |
| View details dialog | The selected public/operator case API, with its own cancelled request | Loading/retry; previous-case details cannot appear under a new selection |
| Identity, account and trail | Frozen source evidence and available 90-day history | Only available transactions; no invented history |
| Python scores and weights | Case API `risk.dimensions`, `risk.weights`, `risk.overall_score` | Unavailable dimensions and contributions stay unavailable |
| Stage checks | Shared CaseStages; operational alert status and frozen feedback | Public AI/review statuses remain locked |
| Analysis, advisory opinion, confidence and trace | Private validated attempt reads through OperatorReview and AgentTrace | Not recorded, not started, failure and unknown remain distinct |
| Analyst verdict and history | Immutable feedback API, current assessment linkage | No save without genuine completed triage; frozen after save |
| Investigation usage | Corpus attempt-ledger aggregate API | Unknown/not applicable stay distinct; optional token categories appear only when reported |
| Evolution outcomes and matrix | Corpus review-summary/rule-matrix APIs, computed from genuine feedback | Explicit review denominators, zero-review rules, unavailable predictions |
| Plain rule summaries | Shared server rule catalog; original detector conditions remain alongside them | Summaries explain signals without assigning a human verdict |
| Stored reviewed-alert trend | Integrity-checked frozen review snapshots attached to A5 history | Repeated cohorts deduplicated; no bar for unavailable proportions; real zero remains zero |
| A5 reports and pattern support | Selected private report and bounded pattern history | Frozen sample sizes and insufficiency preserved; no automatic new report |
| Cutoff learning and application | Scoped genuine calibration/candidate/policy APIs | Explicit gates and prospective validation; current policy values separate from original/candidate values |
| Observed effects | Actual scoped applications, assessments and subsequent human reviews | Not yet observed; no causal improvement claim |
| Public aggregate brief | Explicit preview, immutable publication and withdrawal APIs | No automatic publication; no private case-level records |
| Synthetic practice/reference results | Separately labeled corpus references and isolated fixture APIs | Retry on failed reads; never counted as genuine feedback |
| Admin usage, runs and audit | Current corpus only; paged sanitized histories and ledger reducer | Archive scopes rejected; daily controls remain account-wide |
| System design/explainer | Server role catalog plus labeled workflow explanation | Describes architecture, not execution success or measured optimization |
| Sign-in | Firebase in-memory authentication and server operator/admin checks | Failed/expired access clears private state; no credentials in URLs/storage |

Corrections made: the case preview moved into the shared native dialog; queue controls use shared buttons; genuine queue counts no longer start at fabricated zeros; trend points retain immutable provenance and real denominators; Admin defaults to current corpus data instead of silently showing the earlier dataset; A0 current-policy values are distinct from before/candidate values; public publication controls have consistent layout and a word-count gate.

The nine detector conditions, fixed risk weights, genuine feedback and sealed model outputs were not rewritten. No model request, build, deployment or paid operation is part of this change.

Verification: 124 unit tests and 23 isolated Firebase integration tests passed; all eight browser journeys passed. TypeScript, shared design checks and the strict design audit passed. Read-only local checks confirmed one desktop filter row, a five-dimension case-risk dialog, nine plain-language rule summaries, two distinct stored review cohorts and 14 real corpus provider attempts in Admin. No operator mutation was sent during that local walkthrough. A regression check distinguishes an overall review gate of three from a rule-specific denominator of one; the live HIGH_VALUE point uses its own two-review denominator.
