# AML Insight UI contract

## Seeded history practice

An active practice baseline can restrict work to 2,000 preprocessing cases while reserving 1,000 from different identities. Show the active allocation and actual Gemini advisory count first. Preserved 10,000-case history and earlier full investigations have separate labels. Never present an advisory review as a full investigation, analyst verdict or qualifying genuine calibration observation. Reserved cases are excluded server-side from both preprocessing workers.

The read-only seeded-history panel belongs inside synthetic practice. Its reference reviews remain visibly simulated, separate from genuine human metrics. Actual AI completion and failures come from the ledger; importing a reference never marks an investigation complete. Refresh is explicit. Reads never submit model work or change policies. Genuine model/reference comparisons show distinct case and identity counts and are not labeled human agreement.

## Corpus Evolution story — 18 October 2026

The main Evolution journey reads genuine corpus evidence only. Live review summaries and matrix counts describe the 20,000 operational cases within the 40,000-case source corpus; frozen A5 reports describe their own immutable sample. Synthetic walkthroughs and reference labels never enter genuine review counts, calibration gates or prospective validation. Earlier Demo/Discovery controls and API routes are removed. Stored historical records remain immutable and inaccessible through operational APIs.

The page follows Outcomes → Understand → Learn → Apply → Observe. Jump buttons only scroll and focus the corresponding heading; they do not clear notes, change selection, fetch a different report or write data. Report and snapshot changes, screen navigation and supporting investigations reuse the shared dirty-form guard. Current corpus forms have unique IDs and dirty ownership. No sensitive state enters URLs or browser storage.

Corpus A0 policies, pending candidates, assessments and audit records are dataset-scoped. New corpus parents pin the selected corpus policy; previous runs and human decisions remain unchanged. Approval, application, rollback, reassessment and restoration remain explicit, confirmed actions. Only cutoff changes are actionable in the main journey. A5 is a separately confirmed model request; merely opening or refreshing Evolution sends none. Deterministic candidate preparation reads every eligible frozen review, independent of the bounded examples sent to A5.

Observation separates training, prospective validation, explicit label reassessment and subsequent human reviews. Absence of post-application reviews is “Not yet observed”; none of these metrics establishes causal production improvement. Aggregate publication uses its own corpus pointer, explicit preview/confirmation and withdrawal. Public visitors cannot read individual records or learning controls.

## Identity review and operator-approved detector policies — 18 October 2026

Identity type and identity filters are native selects owned by the existing form-field styling. Filters and search operate on the same case set; selection stays within visible results. Changing filters, cases, alerts, recommendation selection or screens uses App's unsaved-note guard. The queue shows linked source identity/account, the full available 90-day transaction trail and counts awaiting triage/review or frozen. Customer type is a source attribute, not an AI identity-verification claim.

Operator queue reads are private and policy-versioned. Public frozen publications retain baseline detector evidence. Refresh is explicit. Selected-case triage includes all applicable unfrozen alerts, preserves frozen alerts and pins the expected detector version. No actionable alerts means a disabled triage action. Saved analyst feedback is final; the form and API refuse later changes. Historical events remain readable.

Agent 0 owns the deterministic machine pre-label, heuristic score and explanatory signals, separately from priority and the analyst verdict. Legacy runs show Not recorded. The score is never presented as a calibrated probability. Evolution's ReviewOverview counts stored analyst outcomes and machine agreement with explicit denominators; it never infers population accuracy/FPR from reviewed alerts.

RecommendationQueue owns bounded recommendation/pattern histories and explicit operator approval, rejection, apply and rollback. It reuses native selects, the request helper, Dialog and the parent dirty-state owner. Each item separates AI rationale, sample support, measured synthetic what-if, expected/unknown effects and observed post-apply outcomes. Insufficient, unchanged or unsafe findings cannot be approved/applied. A0/Python risk weights, prompts and model selection are not application targets. Application changes only future detector-policy versions; historical runs, frozen reviews and held-out records are immutable. Confirmation and expected revisions are mandatory; failed/unknown writes preserve notes and require authoritative refresh. No automatic retries or activation occur.

## Business sources

| Source | UI consequence |
| --- | --- |
| `backend/api.py`, `backend/config.py` | Public frozen synthetic reads; allowlisted authenticated operator routes; live triage unavailable. |
| `backend/engine.py`, `backend/validation.py` | Scores are deterministic heuristics; protected signals remain visible; missing context abstains. |
| `docs/implementation-status.md` | No genuine model results or A5 recommendations yet; discovery diagnostic only. |
| User's Genesis/free-only requirements | All assets/tooling remain local; no new paid services or cloud execution. |

No deletion, payment, permission editing, or rule activation exists in this UI. This visual revision changes none of those domain boundaries.

## Canonical UI Map

| Capability | Canonical owner | Source of truth | Allowed variants | Verification |
| --- | --- | --- | --- | --- |
| Form | native labeled fields and app-owned validation, following `SignIn` / `OperatorReview` | This contract + backend request schemas | sign-in, analyst feedback, admin controls, Evolution notes | browser invalid/error/success, retained notes, first-error focus |
| Scrollbar | `frontend/style.css` global baseline | DESIGN.md and root tokens | queue/table geometry only | computed styles + mobile |
| Search | queue search in `frontend/main.tsx` | Published fixed demo dataset | immediate local filtering | clear/no-results/count |
| Dialog | `Dialog.tsx` native modal dialog | This contract | sign-in, run usage, unsaved review, daily controls, A5 queue, candidate freeze, held-out confirmation | focus, Escape, short viewport |
| Feedback | `.error` alert and inline field help | This contract | request error, validation | browser failure tests |
| Navigation | App screen state | This contract | three public workspace screens plus operator Admin | sibling screen + mobile |
| Select/Listbox | native HTML select in operator review and Evolution | This contract | selected alert, verdict, optional override, analytical snapshot, A5 run, candidate, recommendation decision; platform popup accepted | keyboard, opened popup, mobile |
| Toast | `CompletionToast` in `Usage.tsx`, owned by App | run summary | one terminal parent notification for initiating operator | live region, deduplication, open dialog |

No date input, bulk table selection or CRUD editor applies. Read-only evidence/discovery tables remain bounded. Admin run/audit histories and alert feedback history use cursor-based Load more, 50 records per request and a server maximum of 100. Search operates over exactly twelve published cases; server pagination would not improve this bounded prototype.

`WorkflowExplainer` owns the five Evolution handover explanations. Hover, keyboard focus, or click/tap selects a step; the selection persists until another step is chosen. The associated description states what is added from the prior step. This is explanatory content about the designed workflow, not a running job or generated Evolution result. No live region announces hover changes; the visible explanation follows the step buttons in document order. Touch and keyboard users have the same access as pointer users.

Workspace navigation preserves stable accessible names while decorative per-letter duplicates remain aria-hidden. The raised indicator and `aria-current` identify selection without relying on motion. Reduced-motion mode disables letter rolls, sliding and connector nudges while preserving every interaction.

## State and navigation

Screen, selected case, and search remain in memory across workspace tabs. Do not persist customer-name queries or authentication tokens in URLs or browser storage. This deliberately overrides URL query persistence for a sensitive analyst workspace. Reload returns to the default public investigation view. Browser Back between screen states is not implemented in this prototype.

Search has an accessible clear action that restores input focus, a polite result count, and an explicit no-results state. Clearing is synchronous. No remote search race or debounce exists.

Requests time out, errors preserve safe existing content and provide retry/dismissal. Diagnostic and triage actions prevent duplicate requests while busy. An authorization failure clears the local operator session and explains the need to sign in again. No automatic mutation retry occurs.

## Form and overlay

Sign-in loads public environment configuration before enabling entry. Local fixtures are filled only after the server confirms local emulator mode. Cloud mode offers an explicit Google sign-in popup through the official Firebase SDK with in-memory persistence and the configured Firebase web-app project. Public Firebase configuration is separate from private Gemini credentials. Missing setup has an inline explanation and explicit retry. Provider errors are generic; server UID allowlist verification must succeed before a token is accepted. Closing cancels acceptance of pending setup/authentication results and restores trigger focus. No refresh-token persistence or automatic authentication retry is added.

Local email/password sign-in uses app-owned validation (`noValidate`), associated text errors, first-invalid-field focus, and preserved input. Password is masked initially and can be shown/hidden. Authentication permits paste/autofill. No passwords or tokens go into URLs, logs or persistent client storage.

The native `showModal()` dialog provides modal semantics, inert background and focus trapping. It has a title/description, Escape handling, a close button, viewport-bounded scrolling, scroll lock, and focus restoration to its trigger. Closing discards the sign-in attempt; no durable record is edited. Busy submission cannot be duplicated.

## Accessibility and locale

English/en-AU, AUD equivalents and UTC timestamps. Semantic tables, labeled navigation, current screen/selected case, visible focus, descriptive icon controls, reduced motion and system forced colors. Color never carries status alone. Target WCAG 2.2 AA; automated checks and keyboard verification are evidence, not certification.

## Flow ledger

| Action | Pending | Result | Failure | Recovery |
| --- | --- | --- | --- | --- |
| Load cases | Stable spinner region | Public queue and selected case | Persistent alert | Retry connection |
| Search | Immediate local count | Matching cases | No results | Clear search |
| Sign in locally | Fixed-width verifying action | Same case and operator controls | Inline alert/field errors | Correct and retry |
| Run discovery diagnostic | Fixed-width busy action | Discovery-only comparison | Persistent request alert | Retry after resolving cause |
| Check live triage | Busy action | Currently unavailable | Explicit 503 explanation | Cloud/worker dependency; no fake result |

## Gap-closure behavior — 16 October 2026

The newer triage contract replaces the historical 503 behavior above: local POST returns a persisted FAILED parent with `AI_NOT_CONNECTED`; A1 succeeded and A2 was not sent. Private alert reads own status, latest run and feedback eligibility. Public queue hints never act as that signal. No browser polling or model-output publication occurs.

Review is scoped to one selected alert. Verdict, notes and optional action override use labeled native controls, app-owned validation and an expected revision. Notes remain visible after server errors. A 409 instructs refresh rather than automatic overwrite. Case/alert/screen/sign-out navigation guards unsaved review with the shared dialog; actual page unload uses a narrow beforeunload handler. Successful save clears the draft and refreshes history. No draft or operator token is persisted in browser storage or URLs.

The shared public/operator usage renderer draws only reconciled, mutually exclusive categories, with provider total tokens in the center. Unknown provider outcomes say Unknown; deterministic and not-sent steps say Not applicable. Unreconciled categories use a list with an Unavailable chart; no fabricated slice. The operator completion toast is non-modal, deduplicated by parent ID, dismissible, automatically dismissed after 8 seconds and opens the shared modal dialog only on request. Each new parent notification gets its own timer; dismissal or unmount clears it. Critical run failures remain in the private alert status after toast dismissal.

Admin is visible only while signed in; operators can read summaries, recent runs and audit history. Controls render only after the server session reports is_admin. They are today's UTC live_enabled and a 1–120 attempt limit, never below reservations. All changes use the shared confirmation dialog and expected revision; a new day starts disabled. Cloud/credit gates remain authoritative server-side. There is no model selector, delete/retry control or activation endpoint.

Public usage refresh and private request effects cancel stale work. Signing out clears private run detail, completion notification and admin state. The page remains document-scrolled, tables own horizontal overflow and dialogs own viewport-bounded scrolling. New data visualizations use existing palette tokens, textual labels and no motion. English/en-AU, USD estimates and explicit UTC operational dates apply.

## Evolution and private brief — 17 October 2026

`Evolution.tsx` owns the private frozen-input/A5/candidate workflow and reuses `Dialog`, `request`, `UsageDisplay` and App's dirty-navigation guard. Operator-only history uses bounded cursor-based Load more. Public visitors see the workflow explanation and discovery access boundary, never private analyst notes or model output. Native selects use platform-owned popups; long hashes wrap and the document owns vertical scrolling.

Freezing analytical inputs creates a deterministic immutable snapshot and never supplies a human verdict. A5 queue requires genuine feedback and verified access, with an explicit model-call confirmation. Refresh reads stored status; there is no browser polling or automatic mutation retry. Output, counts, insufficiency, unknown usage and unevaluated optimization are shown as stored. Snapshot identity and label provenance remain visible. Missing proposals are empty states, not failed experiments or invented gains.

Candidate freezing requires a genuine stored A5 result, an explicit allowlisted selection and analyst notes. Its confirmation names the irreversible selection boundary and leaves focus on the safe close action. Insufficient feedback remains labeled. A separate confirmation opens held-out evaluation once; stored results show sample sizes and baseline/candidate counts without publishing private missed-case IDs. Review/reject notes use expected revisions; REVIEWED never means activated.

Freeze and recommendation notes are guarded when changing selection, switching screen, signing out or unloading. Refresh preserves drafts and the selected resource while reading authoritative state, including after a revision conflict. Errors retain notes and direct users to refresh authoritative state. Session expiry clears private data; no notes or tokens persist to URLs or browser storage. Requests and responses after unmount are cancelled/ignored. Routine status acknowledgements are inline; App remains the only terminal investigation-toast owner.

`OperatorReview.tsx` renders the private completed investigation from validated A2/A3/A4 records, including citation IDs, limitations and code-owned priority. The public header is labeled Published evidence; it never claims to be live operator status. Source-ID validity never claims manual semantic support or a human verdict.


Investigation completion indicators derive from authenticated alert states, including updates returned by explicit status refresh and successful feedback saves; they are not fixed visual checks. All case alerts must be complete or frozen for case-level AI completion, and all must have frozen reviews for review completion. No browser polling is introduced. An unfrozen alert remains reanalyzable; saved verdicts remain immutable and are summarized by the compact saved-review card. Transaction citations navigate to highlighted source rows; non-transaction IDs remain optional reference disclosures. Long transaction and feedback histories scroll within their own labeled, keyboard-focusable surfaces.

Optional usage categories (cached prompt, reasoning, tool prompt) render only when reported above zero, in both the shared usage summary and attempt details. Core prompt/output/total categories retain unknown and not-applicable states. Chart reconciliation still requires complete non-overlapping provider metadata. Local build candidates created before these UI edits are historical and require re-verification/repackaging before deployment.


Public/operator consistency: source identity, profile, account, queue hints, triggering movement, evidence snapshot, transaction trail and deterministic risk display are identical for a selected published case. Source/risk checks live in the shared evidence header. Authenticated AI completion and frozen-review checks live in the separate investigation workspace; public visitors see Operator-only status there, not a claim that work has not occurred. Private narrative output and human verdicts retain their existing access controls. Investigation/review/usage panels span both content columns below the shared evidence row. Verified for genuine Alex Example Demo 006 before/after sign-in and at 1440, 1024, 768, 390 and 320px.


## Rule intelligence and threshold learning - 18 October 2026

Evolution leads with the selected report and nine-row Outcomes/Configuration matrix. Native category/status filters preserve selection within results; supporting-case navigation retains the selected rule in memory. A shared discard revision clears drafts only after guarded navigation is accepted. Matrix filters and learning actions have explicit labels, bounded tables, clear unavailable values and native confirmation dialogs.

Sign-in preserves the demo selection. Discovery is an explicit operator-only dataset choice; its 40 cases never enter the public queue. Private traces show recorded states; A5 belongs to its own analytical run. A2 advisory totals never replace Python scores. A4 confidence means model-assessed evidence support. Historical absent fields say Not recorded.

Public summary publication has a draft, server preview, explicit confirmation and revision check; withdrawal preserves immutable history. A0 learning exposes insufficiency, class-specific identity diversity and forward-validation progress. Approval and application are separate; reassessment and restoration are explicit 50-record actions without model calls. No sensitive route parameters, authentication persistence or chart dependency are introduced.


## Brief reading order and usage explanation - 18 October 2026

InvestigationBrief owns an ordered evidence-to-action narrative: Overview, Key findings, Counter-evidence, Missing information, Next steps, Limitations. The final four sections follow a winding two-row desktop layout with decorative connectors; mobile reverts to DOM order in one column. Source links and disclosures remain native and unchanged. Supporting model scores/classification and confidence follow the narrative, ahead of analyst review. UsageDisplay draws a chart only from reconciled categories; otherwise it shows the reported total and a plain explanation of incomplete reporting, with available counts beneath. It never invents a breakdown or hides unknown usage.


### Case stage status

The same connected four-stage trail is visible to both roles. Public visitors receive source/risk status and locked private AI/review stages, never inferred per-case operator results. Operators see case-wide completion for applicable, frozen or in-progress alerts; individual alert review remains separately labeled. A case-run completion refreshes sibling statuses from the operator queue without polling or unmounting the review form. Frozen feedback updates its check immediately and remains immutable.


### Bulk case batches and synthetic learning

Workspace and combined-filter changes use the shared dirty-note guard. Async reads are aborted on scope/selection changes and session ownership guards late private results. Public computations stay in tab memory and never create provider/human evidence. Operator starts require preview and a stable idempotency key through submission retries; progress refresh is explicit. Native confirmation dialogs handle pause/resume/cancel and synthetic decisions with revisions. Continuing failed members requires explicit acknowledgement and does not retry their unknown attempts. Four cards label transaction/case/alert/review units and their own scope/denominators. Validation is frozen and opened once, and simulation policy application never changes genuine policies.


Unified queue revision: preloaded 10,000-case reference evaluation (25% of corpus) is separate from genuine provider and human evidence. The same queue offers reference / pending / awaiting-review / frozen filters, with actual counts and overlapping rule denominators. Start a 10- or 100-case batch at the top; reference cases are excluded from genuine enqueue. Review opens the canonical native dialog; dirty notes guard closing, frozen feedback remains immutable, failed saves preserve notes and focus restores to the queue action. Changing screens, rows or filters retains existing dirty-form protection. No new persistent browser state or identity URLs.


Controlled cutoff exercise: operator-only and local-emulator-only. The real cutoff fitter/application code runs against separate prefixed collections, with 40 fixed training, 20 independent validation and 100 later test observations. Explicit confirmation owns prepare, validate, approve, reject, apply and comparison. Approval requires a passing validation; apply requires approval; test requires the applied policy. Repeated preparation/comparison returns existing records. Version conflicts preserve state and require refresh. No corpus/operational policy, genuine feedback or attempt ledger is written. Controlled success is identified as fixture behavior, never actual predictive improvement. Corpus records without a candidate cannot open validation, approve or apply; historical records remain unchanged.
