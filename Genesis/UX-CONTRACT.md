# AML Insight UI contract

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

The shared public/operator usage renderer draws only reconciled, mutually exclusive categories, with provider total tokens in the center. Unknown provider outcomes say Unknown; deterministic and not-sent steps say Not applicable. Unreconciled categories use a list with an Unavailable chart; no fabricated slice. The operator completion toast is non-modal, deduplicated by parent ID, dismissible and opens the shared modal dialog only on request. Critical run failures remain in the private alert status after toast dismissal.

Admin is visible only while signed in; operators can read summaries, recent runs and audit history. Controls render only after the server session reports is_admin. They are today's UTC live_enabled and a 1–120 attempt limit, never below reservations. All changes use the shared confirmation dialog and expected revision; a new day starts disabled. Cloud/credit gates remain authoritative server-side. There is no model selector, delete/retry control or activation endpoint.

Public usage refresh and private request effects cancel stale work. Signing out clears private run detail, completion notification and admin state. The page remains document-scrolled, tables own horizontal overflow and dialogs own viewport-bounded scrolling. New data visualizations use existing palette tokens, textual labels and no motion. English/en-AU, USD estimates and explicit UTC operational dates apply.

## Evolution and private brief — 17 October 2026

`Evolution.tsx` owns the private frozen-input/A5/candidate workflow and reuses `Dialog`, `request`, `UsageDisplay` and App's dirty-navigation guard. Operator-only history uses bounded cursor-based Load more. Public visitors see the workflow explanation and discovery access boundary, never private analyst notes or model output. Native selects use platform-owned popups; long hashes wrap and the document owns vertical scrolling.

Freezing analytical inputs creates a deterministic immutable snapshot and never supplies a human verdict. A5 queue requires genuine feedback and verified access, with an explicit model-call confirmation. Refresh reads stored status; there is no browser polling or automatic mutation retry. Output, counts, insufficiency, unknown usage and unevaluated optimization are shown as stored. Snapshot identity and label provenance remain visible. Missing proposals are empty states, not failed experiments or invented gains.

Candidate freezing requires a genuine stored A5 result, an explicit allowlisted selection and analyst notes. Its confirmation names the irreversible selection boundary and leaves focus on the safe close action. Insufficient feedback remains labeled. A separate confirmation opens held-out evaluation once; stored results show sample sizes and baseline/candidate counts without publishing private missed-case IDs. Review/reject notes use expected revisions; REVIEWED never means activated.

Freeze and recommendation notes are guarded when changing selection, switching screen, signing out or unloading. Refresh preserves drafts and the selected resource while reading authoritative state, including after a revision conflict. Errors retain notes and direct users to refresh authoritative state. Session expiry clears private data; no notes or tokens persist to URLs or browser storage. Requests and responses after unmount are cancelled/ignored. Routine status acknowledgements are inline; App remains the only terminal investigation-toast owner.

`OperatorReview.tsx` renders the private completed investigation from validated A2/A3/A4 records, including citation IDs, limitations and code-owned priority. The public header is labeled Published evidence; it never claims to be live operator status. Source-ID validity never claims manual semantic support or a human verdict.
