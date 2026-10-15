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
| Form | `SignIn` in `frontend/main.tsx` | This contract + Firebase API | local operator sign-in | browser invalid/error/success |
| Scrollbar | `frontend/style.css` global baseline | DESIGN.md and root tokens | queue/table geometry only | computed styles + mobile |
| Search | queue search in `frontend/main.tsx` | Published fixed demo dataset | immediate local filtering | clear/no-results/count |
| Dialog | `SignIn` native modal dialog | This contract | sign-in only | focus, Escape, short viewport |
| Feedback | `.error` alert and inline field help | This contract | request error, validation | browser failure tests |
| Navigation | App screen state | This contract | three workspace screens | sibling screen + mobile |

No select/listbox, date input, bulk table selection, CRUD editor, or toast capability applies. Read-only tables are bounded: nine displayed transaction rows (explicit total), six agents, and three diagnostic candidates. Search operates over exactly twelve published cases; server pagination would not improve this bounded prototype.

`WorkflowExplainer` owns the five Evolution handover explanations. Hover, keyboard focus, or click/tap selects a step; the selection persists until another step is chosen. The associated description states what is added from the prior step. This is explanatory content about the designed workflow, not a running job or generated Evolution result. No live region announces hover changes; the visible explanation follows the step buttons in document order. Touch and keyboard users have the same access as pointer users.

Workspace navigation preserves stable accessible names while decorative per-letter duplicates remain aria-hidden. The raised indicator and `aria-current` identify selection without relying on motion. Reduced-motion mode disables letter rolls, sliding and connector nudges while preserving every interaction.

## State and navigation

Screen, selected case, and search remain in memory across workspace tabs. Do not persist customer-name queries or authentication tokens in URLs or browser storage. This deliberately overrides URL query persistence for a sensitive analyst workspace. Reload returns to the default public investigation view. Browser Back between screen states is not implemented in this prototype.

Search has an accessible clear action that restores input focus, a polite result count, and an explicit no-results state. Clearing is synchronous. No remote search race or debounce exists.

Requests time out, errors preserve safe existing content and provide retry/dismissal. Diagnostic and triage actions prevent duplicate requests while busy. An authorization failure clears the local operator session and explains the need to sign in again. No automatic mutation retry occurs.

## Form and overlay

Sign-in uses app-owned validation (`noValidate`), associated text errors, first-invalid-field focus, and preserved input. Password is masked initially and can be shown/hidden. Authentication permits paste/autofill. No passwords or tokens go into URLs, logs or persistent client storage.

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
