I'll create the complete markdown file for you right now.

```markdown
# AML Triage — UI Improvement Tasks
# Master Implementation Document

> **Purpose:** Each task below is written for an AI coding agent. Every file
> path, component name, CSS variable, data field, and behaviour is explicitly
> specified. Do NOT infer, invent, or assume anything not listed here. If
> something is unclear, stop and ask rather than guess.

> **Tech Stack (do not change unless a task explicitly says otherwise):**
> - React + TypeScript (TSX)
> - CSS via component-level `.css` files
> - All colours via CSS custom properties (`var(--)`)
> - No external component libraries unless a task explicitly permits one
> - Recharts is permitted ONLY in Task 9
> - SQLite backend accessed via existing functions in `src/api/client.ts`

> **Files you MUST read in full before starting any task:**
> - `src/api/client.ts` — all existing API functions
> - `src/types/alert.ts` — alert type definitions
> - `src/index.css` — existing CSS variables under `:root`
> - `src/App.tsx` — router and app tree structure
> - `src/components/layout/NavigationBar.tsx` — navbar structure

---

## Table of Contents

1. [Task 1+2 — ViewModeContext + Dark Theme](#task-12--viewmodecontext--dark-theme)
2. [Task 3 — CurrentRunPanel](#task-3--currentrunpanel)
3. [Task 4 — CollapsibleSection](#task-4--collapsiblesection)
4. [Task 5 — Loop Progress Panel](#task-5--loop-progress-panel)
5. [Task 6 — Admin Layers: Dashboard](#task-6--admin-layers-dashboard)
6. [Task 7 — Admin Layers: Alert Queue](#task-7--admin-layers-alert-queue)
7. [Task 8 — Admin Layers: Labeling + Shared Admin Panels](#task-8--admin-layers-labeling--shared-admin-panels)
8. [Task 9 — Admin Layers: Evolution + Charts](#task-9--admin-layers-evolution--charts)
9. [Task 10 — Backend: Stub Admin Endpoints](#task-10--backend-stub-admin-endpoints)
10. [Task 11 — Live Processing Feedback](#task-11--live-processing-feedback)
11. [Task 12 — UI Polish & Fixes](#task-12--ui-polish--fixes)
12. [Global Rules](#global-rules)

---

## Task 1+2 — ViewModeContext + Dark Theme

### Context

This is the **foundation task**. Every other admin feature (Tasks 3, 5, 6, 7,
8, 9) depends on it. Do not start any other task until this is complete and
verified. Tasks 1 and 2 are merged because the dark token set lives in
`index.css` and is applied by the context — they are the same unit of work.

### What You Are Building

1. A React context (`ViewModeContext`) that holds a `'user' | 'admin'` mode
2. A toggle button (`AdminToggle`) in the navbar
3. A full dark theme CSS token block appended to `index.css`

---

### Files to CREATE

#### `src/context/ViewModeContext.tsx`

**Type definitions (write exactly these):**

```tsx
type ViewMode = 'user' | 'admin';

interface ViewModeContextValue {
  mode: ViewMode;
  isAdmin: boolean;
  toggleMode: () => void;
}
```

**Behaviour:**

- `useState<ViewMode>` initialised from
  `localStorage.getItem('aml_view_mode') as ViewMode ?? 'user'`
- `useEffect` that fires on every `mode` change:
  - Persist: `localStorage.setItem('aml_view_mode', mode)`
  - If `mode === 'admin'` → `document.documentElement.dataset.theme = 'dark'`
  - If `mode === 'user'` → `delete document.documentElement.dataset.theme`
- **Why `documentElement` not `document.body`:** CSS variable inheritance is
  more reliable from the `<html>` root. Portals and modals that render outside
  `<body>` still inherit correctly.
- Export named: `ViewModeProvider` (component) and `useViewMode` (hook)
- `useViewMode` must throw if called outside provider:

```tsx
if (!context) {
  throw new Error('useViewMode must be used within ViewModeProvider');
}
```

---

#### `src/components/AdminToggle.tsx`

**Visual spec:**

- A pill-shaped button in the navbar
- **User mode:** outlined, label `USER MODE`, no fill
- **Admin mode:** orange-filled, label `ADMIN MODE`
- Calls `toggleMode()` from `useViewMode()` on click

**CSS file: `src/components/AdminToggle.css`**

```css
.admin-toggle {
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  cursor: pointer;
  transition: background 150ms ease, color 150ms ease;
  border: 1.5px solid transparent;
}

.admin-toggle.user {
  background: transparent;
  border-color: var(--nav-text);
  color: var(--nav-text);
}

.admin-toggle.admin {
  background: var(--pwc-orange);
  border-color: var(--pwc-orange);
  color: #ffffff;
}
```

> `var(--nav-text)` and `var(--pwc-orange)` already exist in `:root`.
> Do not hardcode colour values.

---

### Files to MODIFY

#### `src/App.tsx`

Wrap the **entire** app tree in `<ViewModeProvider>` **outside** `<BrowserRouter>`:

```tsx
<ViewModeProvider>
  <BrowserRouter>
    {/* existing routes unchanged */}
  </BrowserRouter>
</ViewModeProvider>
```

Do not move or reorder any existing routes.

---

#### `src/components/layout/NavigationBar.tsx`

- Import `<AdminToggle />` from `../AdminToggle`
- Add it inside `.navbar-right` div, **after** the existing DEMO badge element
- Do not change any other part of the navbar

---

#### `src/index.css`

Append this **exact** block at the very bottom of the file, after the existing
`:root` block. Do not modify `:root` in any way.

```css
[data-theme="dark"] {
  --surface-base: #0D0D0D;
  --surface-raised: #161616;
  --surface-elevated: #1F1F1F;
  --surface-overlay: #272727;
  --surface-border: rgba(255, 255, 255, 0.08);
  --surface-border-strong: rgba(255, 255, 255, 0.15);
  --text-primary: #F0F0F0;
  --text-secondary: #C8C8C8;
  --text-muted: rgba(255, 255, 255, 0.40);
  --text-mono: #E8E8E8;
  --risk-critical: #FCA5A5;
  --risk-critical-bg: rgba(185, 28, 28, 0.20);
  --risk-critical-border: rgba(185, 28, 28, 0.35);
  --risk-high: #FDBA74;
  --risk-high-bg: rgba(154, 52, 18, 0.20);
  --risk-high-border: rgba(154, 52, 18, 0.35);
  --risk-medium: #FDE68A;
  --risk-medium-bg: rgba(146, 64, 14, 0.20);
  --risk-medium-border: rgba(146, 64, 14, 0.35);
  --risk-low: #86EFAC;
  --risk-low-bg: rgba(22, 101, 52, 0.20);
  --risk-low-border: rgba(22, 101, 52, 0.35);
  --status-pending: #9CA3AF;
  --status-pending-bg: rgba(55, 65, 81, 0.30);
  --status-pending-border: rgba(55, 65, 81, 0.50);
  --status-processing: #93C5FD;
  --status-processing-bg: rgba(29, 78, 216, 0.20);
  --status-processing-border: rgba(29, 78, 216, 0.35);
  --status-complete: #86EFAC;
  --status-complete-bg: rgba(22, 101, 52, 0.20);
  --status-complete-border: rgba(22, 101, 52, 0.35);
  --status-error: #FCA5A5;
  --status-error-bg: rgba(185, 28, 28, 0.20);
  --status-error-border: rgba(185, 28, 28, 0.35);
  --accent-subtle: rgba(253, 81, 8, 0.15);
  --accent-border: rgba(253, 81, 8, 0.30);
}

[data-theme="dark"] ::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.18);
}

[data-theme="dark"] .skeleton {
  background: linear-gradient(
    90deg,
    var(--surface-overlay) 25%,
    var(--surface-elevated) 50%,
    var(--surface-overlay) 75%
  );
}
```

> **Important:** Nav tokens (`--nav-bg`, `--nav-text`, `--pwc-orange`) are
> intentionally NOT overridden. The navbar is already dark — do not touch it.

---

### Verification Checklist

- [ ] Click AdminToggle → entire page background flips to dark
- [ ] Click AdminToggle again → page returns to light
- [ ] Reload page in admin mode → stays dark (localStorage persisted)
- [ ] Reload page in user mode → stays light
- [ ] DevTools console: `document.documentElement.dataset.theme` returns
      `"dark"` in admin mode, `undefined` in user mode
- [ ] All 6 pages (Dashboard, Alert Queue, Labeling, Evolution, Agents,
      Architecture) render without broken colours in both themes
- [ ] No console errors

---

## Task 3 — CurrentRunPanel

### Context

Displays the status and metadata of the most recent Evolution Agent run at the
top of the Evolution page. Gives analysts immediate context before they read
the charts and patterns below.

> ⚠️ **Depends on:** Task 1+2 (for `isAdmin`), Task 4 (for `CollapsibleSection`),
> Task 10 (for real API endpoint).
> Build with **mock data first**. Wire to real endpoint when Task 10 is done.

---

### Files to CREATE

#### `src/components/evolution/CurrentRunPanel.tsx`

**Mock data shape (use this until Task 10 endpoint exists):**

```ts
const MOCK_RUN = {
  run_number: 3,
  timestamp: '2024-05-27T10:32:00Z',
  total_alerts_analyzed: 3542,
  total_feedback_received: 3542,
  overall_fp_rate: 0.373,
  confidence: 'HIGH' as const,
  data_sufficiency: 'SUFFICIENT' as const,
  patterns_found: 6,
  recommendations_count: 5,
  status: 'COMPLETE' as const,
};
```

**Visible fields in user mode:**

| Field | Display Format |
|---|---|
| Run number | `Run #3` |
| Timestamp | `27 May 2024, 10:32 AM` (formatted, not raw ISO) |
| Total alerts analysed | `3,542` (comma separator) |
| Overall FP rate | `37.3%` |
| Confidence | Badge: `HIGH` green / `MEDIUM` amber / `LOW` red |
| Patterns found | `6 patterns` |
| Recommendations | `5 recommendations` |
| Status | Pill: `● COMPLETE` green / `● RUNNING` blue pulsing / `● ERROR` red |

**Additional fields visible in admin mode only
(wrap each in `{isAdmin && (...)}`):**

- `data_sufficiency` raw value
- `total_feedback_received` count
- Exact ISO timestamp (unformatted)

**Styling:**

- Outer wrapper: `<CollapsibleSection id="current-run-panel" title="Current Evolution Run" defaultOpen={true}>`
- Card background: `var(--surface-raised)`
- Border: `1px solid var(--surface-border)`
- Border radius: `8px`
- Padding: `16px 20px`

---

### Files to MODIFY

#### `src/pages/EvolutionPage.tsx`

- Import `CurrentRunPanel`
- Insert as the **first element** inside the page content area,
  **above** all existing sections
- Do not move or reorder any existing sections

---

### Verification Checklist

- [ ] Panel appears at top of Evolution page above all other content
- [ ] Mock data renders all fields correctly
- [ ] Confidence badge shows correct colour per level
- [ ] Status pill shows correct colour; RUNNING state pulses
- [ ] Admin-only fields hidden in user mode
- [ ] Admin-only fields visible in admin mode
- [ ] Panel collapses and expands via CollapsibleSection
- [ ] When Task 10 endpoint exists: swap MOCK_RUN with real API call

---

## Task 4 — CollapsibleSection

### Context

A generic reusable wrapper for collapse/expand behaviour. Keep this completely
generic — no AML-specific logic inside it. This establishes the `localStorage`
persistence pattern used throughout the app.

---

### Files to CREATE

#### `src/components/common/CollapsibleSection.tsx`

**Props interface:**

```ts
interface CollapsibleSectionProps {
  id: string;
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
  titleRight?: React.ReactNode;
}
```

**Behaviour:**

- On mount: read `localStorage.getItem(`collapsible_${id}`)`
  - `'false'` → start collapsed
  - `'true'` or `null` → start expanded (or use `defaultOpen`)
- On toggle: flip state + write to localStorage
- Render a chevron icon that rotates 180° when collapsed

**CSS file: `src/components/common/CollapsibleSection.css`**

```css
.collapsible-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  user-select: none;
  padding: 12px 0;
}

.collapsible-chevron {
  transition: transform 300ms ease;
  color: var(--text-muted);
}

.collapsible-chevron.open {
  transform: rotate(180deg);
}

.collapsible-body {
  max-height: 0;
  overflow: hidden;
  transition: max-height 300ms ease;
}

.collapsible-body.open {
  max-height: 9999px;
}
```

> Do not calculate heights in JavaScript. The `max-height` CSS approach is
> intentional and avoids ResizeObserver complexity.

---

### Verification Checklist

- [ ] Collapses and expands with smooth animation
- [ ] State persists correctly after page reload
- [ ] Multiple instances on same page have independent state
- [ ] `titleRight` prop renders on right side of header
- [ ] No layout shift when toggling
- [ ] Chevron rotates on open/close
- [ ] Works in both light and dark themes

---

## Task 5 — Loop Progress Panel

### Context

A dark-styled card on the Evolution page showing live status of the most
recent or currently-running Evolution Agent execution.

> **Critical:** This card must **always appear dark** — even in light/user mode.
> This is an intentional design exception. Use hardcoded dark values.
> Do NOT use `var(--)` tokens in this component's CSS.

---

### Files to CREATE

#### `src/components/evolution/LoopProgressPanel.tsx`

**Data shape** (poll `getRunHistory()` from `src/api/client.ts` every 3s):

```ts
interface LoopRunData {
  run_number: number;
  status: 'IDLE' | 'RUNNING' | 'COMPLETE' | 'ERROR';
  current_round?: number;
  total_rounds?: number;
  alerts_processing?: number;
  fp_rate_before?: number;
  fp_rate_current?: number;
  started_at?: string;
  completed_at?: string;
}
```

**Display states:**

*IDLE:*
```
● No active run
Last run: Run #3 completed 27 May 2024
```

*RUNNING:*
```
● RUNNING
Round 3 / 10  ·  Processing 847 alerts  ·  FP rate: 37% → 23%
[████████████░░░░░░░░]  progress bar
```

*COMPLETE:*
```
✓ Run #3 Complete
3,542 alerts analysed  ·  6 patterns found  ·  37.3% FP rate
```

*ERROR:*
```
✗ Run #3 Failed
[error message, or "Unknown error" if none available]
```

**CSS file: `src/components/evolution/LoopProgressPanel.css`**

```css
/* HARDCODED — do not replace with var() tokens */
.loop-panel {
  background: #161616;
  border: 1px solid rgba(255, 255, 255, 0.10);
  border-radius: 8px;
  padding: 16px 20px;
  color: #F0F0F0;
  margin-bottom: 24px;
}
.loop-panel .lp-label {
  color: rgba(255, 255, 255, 0.50);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.loop-panel .lp-value { color: #F0F0F0; font-size: 14px; }
.loop-panel .lp-status-running  { color: #93C5FD; }
.loop-panel .lp-status-complete { color: #86EFAC; }
.loop-panel .lp-status-error    { color: #FCA5A5; }
.loop-panel .lp-status-idle     { color: rgba(255,255,255,0.40); }
.loop-panel .lp-progress-track {
  width: 100%;
  height: 4px;
  background: rgba(255,255,255,0.10);
  border-radius: 2px;
  margin-top: 10px;
}
.loop-panel .lp-progress-fill {
  height: 100%;
  background: #FD5108;
  border-radius: 2px;
  transition: width 500ms ease;
}
```

**Polling logic:**

```ts
useEffect(() => {
  const fetchStatus = async () => { /* call getRunHistory() */ };
  fetchStatus();
  const id = setInterval(fetchStatus, 3000);
  return () => clearInterval(id);
}, []);
```

> Increase interval to 30000ms when status is `COMPLETE` or `ERROR`.

---

### Files to MODIFY

#### `src/pages/EvolutionPage.tsx`

- Import `LoopProgressPanel`
- Insert **between** the "Top KRI Indicators" section and
  the "FP Patterns Identified" section
- Do not move any other sections

---

### Verification Checklist

- [ ] Panel always appears dark regardless of app theme
- [ ] All four display states render correctly
- [ ] Progress bar width = `current_round / total_rounds × 100%`
- [ ] `clearInterval` called on unmount (verify in DevTools)
- [ ] No `var(--)` tokens used in this component's CSS

---

## Task 6 — Admin Layers: Dashboard

### Context

Add three admin-only collapsible panels to the Dashboard page, invisible in
user mode and only visible when `isAdmin === true`.

> ⚠️ **Depends on:** Task 1+2, Task 4, Task 10.
> Build with mock data shells first.

---

### Files to MODIFY

#### `src/pages/DashboardPage.tsx`

Add three new sections **below** the existing "Recent Critical/High Alerts"
section, each wrapped in an `isAdmin` guard.

---

**Section A — Rule Weight Status**

```tsx
{isAdmin && (
  <CollapsibleSection id="admin-rule-weights" title="Rule Weight Status" defaultOpen={true}>
    {/* table */}
  </CollapsibleSection>
)}
```

Columns: `RULE NAME | CURRENT WEIGHT | LAST MODIFIED | CHANGE | STATUS`

Mock data:

```ts
const RULE_WEIGHTS_MOCK = [
  { rule: 'RULE_CASH',         weight: 0.82, lastModified: '2024-05-01', change: +0.05, status: 'ACTIVE' },
  { rule: 'RULE_MULTI_CCY',    weight: 0.74, lastModified: '2024-04-15', change: -0.10, status: 'ACTIVE' },
  { rule: 'RULE_DORMANT',      weight: 0.68, lastModified: '2024-03-22', change:  0.00, status: 'ACTIVE' },
  { rule: 'RULE_FOREIGN_WIRE', weight: 0.79, lastModified: '2024-05-10', change: +0.02, status: 'ACTIVE' },
  { rule: 'RULE_HV',           weight: 0.91, lastModified: '2024-02-14', change:  0.00, status: 'ACTIVE' },
  { rule: 'RULE_CRYPTO',       weight: 0.85, lastModified: '2024-04-30', change: +0.08, status: 'ACTIVE' },
  { rule: 'RULE_PEP',          weight: 0.95, lastModified: '2024-01-10', change:  0.00, status: 'ACTIVE' },
  { rule: 'RULE_DECEASED',     weight: 0.99, lastModified: '2024-01-10', change:  0.00, status: 'ACTIVE' },
];
```

`change` column colours:
- Positive → `var(--risk-low)`
- Negative → `var(--risk-critical)`
- Zero → `var(--text-muted)`

Wire to `GET /api/admin/rule-weights` when Task 10 is ready.

---

**Section B — System Health**

```tsx
{isAdmin && (
  <CollapsibleSection id="admin-system-health" title="System Health" defaultOpen={true}>
    {/* 2-column stat grid */}
  </CollapsibleSection>
)}
```

Mock data:

```ts
const SYSTEM_HEALTH_MOCK = [
  { label: 'DB Size',           value: '42.3 MB',  status: 'ok' },
  { label: 'Audit Log Entries', value: '187,432',  status: 'ok' },
  { label: 'API Latency (avg)', value: '124ms',    status: 'ok' },
  { label: 'Last Backup',       value: '2h ago',   status: 'ok' },
  { label: 'Active Sessions',   value: '1',        status: 'ok' },
  { label: 'Error Rate (24h)',  value: '0.02%',    status: 'ok' },
];
```

Status dot: `'ok'` = green, `'warn'` = amber, `'error'` = red.

---

**Section C — Autolabel Run History**

```tsx
{isAdmin && (
  <CollapsibleSection id="admin-run-history" title="Autolabel Run History" defaultOpen={false}>
    {/* table */}
  </CollapsibleSection>
)}
```

Columns: `RUN # | DATE | ALERTS PROCESSED | FP RATE | PATTERNS | CONFIDENCE | STATUS`

Use mock run history (3 rows, newest first).
Wire to `GET /api/evolution/run-history` when Task 10 is ready.

---

### Verification Checklist

- [ ] All 3 sections invisible in user mode
- [ ] All 3 sections visible in admin mode
- [ ] Each section collapses/expands independently
- [ ] `change` column colour coding correct
- [ ] Status dots show correct colours
- [ ] No existing dashboard content moved or broken

---

## Task 7 — Admin Layers: Alert Queue

### Context

Enhance the Alert Queue with three admin-only columns and admin detail panels
inside the alert detail modal.

> ⚠️ **Depends on:** Task 1+2, Task 4, Task 8 (shared admin panels).
> Read `src/components/alerts/AlertTable.tsx` in full before editing.

---

### Files to MODIFY

#### `src/components/alerts/AlertTable.tsx`

Add 3 new columns **after** the existing `TYPOLOGY` column:

| Column Header | Data Field | Display Format |
|---|---|---|
| `FP PROB` | `alert.fp_probability` | `0.82` → `82%` |
| `THRESHOLD` | `alert.active_threshold` | `0.30` (decimal) |
| `CALIBRATION` | `alert.calibration_status` | Coloured badge |

Calibration badge colours:
- `'ON_TRACK'` → `var(--risk-low-bg)` bg, `var(--risk-low)` text
- `'DRIFTING'` → `var(--risk-medium-bg)` bg, `var(--risk-medium)` text
- `'MISCALIBRATED'` → `var(--risk-critical-bg)` bg, `var(--risk-critical)` text

**Hide/show via CSS only — no JS conditional rendering:**

```css
.col-admin {
  display: none;
}
[data-theme="dark"] .col-admin {
  display: table-cell;
}
```

Apply class `col-admin` to **both** the `<th>` and every `<td>` for these
three columns.

---

#### Alert Detail Modal

Find the existing alert detail modal in `src/components/alerts/`.
Add at the **bottom** of the modal content:

```tsx
{isAdmin && (
  <>
    <ScoreBreakdownPanel alert={alert} />
    <ActiveThresholdPanel alert={alert} />
    <LabelHistoryPanel alert={alert} />
  </>
)}
```

---

### Verification Checklist

- [ ] Three columns appear in admin/dark mode
- [ ] Three columns hidden in user/light mode
- [ ] No layout shift when toggling mode
- [ ] FP PROB displays as percentage
- [ ] Calibration badge colours correct for all three states
- [ ] Admin panels appear in modal in admin mode
- [ ] Admin panels hidden in modal in user mode
- [ ] Pagination, filtering, sorting still work correctly

---

## Task 8 — Admin Layers: Labeling + Shared Admin Panels

### Context

Two parts:
1. Build 3 shared admin panel components
2. Add those panels and a calibration column to the Labeling page

> **Critical:** Build panels once in `src/components/admin/`.
> Import from that path in both Task 7 and Task 8. Do not duplicate.

---

### Files to CREATE

#### `src/components/admin/ScoreBreakdownPanel.tsx`

**Props:** `{ alert: Alert }`

**Data source:** `alert.score_breakdown`

```ts
interface ScoreBreakdown {
  transaction_risk: number;  // weight 30%
  customer_risk: number;     // weight 25%
  behavioural_risk: number;  // weight 20%
  account_risk: number;      // weight 15%
  network_risk: number;      // weight 10%
  overall_score: number;
}
```

Layout: horizontal bar per dimension, label left, score right,
bar width = `score × 100%`.

Bar colour:
- `>= 0.7` → `var(--risk-critical)`
- `0.4–0.69` → `var(--risk-medium)`
- `< 0.4` → `var(--risk-low)`

Null handling: render `"Score breakdown not available"` in `var(--text-muted)`.

---

#### `src/components/admin/ActiveThresholdPanel.tsx`

**Props:** `{ alert: Alert }`

**Data source:** `alert.active_threshold`

```ts
interface ActiveThreshold {
  rule: string;
  current_threshold: number;
  recommended_threshold: number;
  fp_rate_at_current: number;
  fp_rate_at_recommended: number;
  last_calibrated: string;
}
```

Layout:

```
Rule: RULE_HV
Current threshold:      0.30  →  FP rate: 49%   [red]
Recommended threshold:  0.50  →  FP rate: 21%   [green]
Last calibrated: 15 Apr 2024
```

Null handling: render `"Threshold data not available"`.

---

#### `src/components/admin/LabelHistoryPanel.tsx`

**Props:** `{ alert: Alert }`

**Data source:** `alert.label_history` (array)

```ts
interface LabelEvent {
  timestamp: string;
  action: string;   // 'AUTO_FP' | 'AUTO_TP' | 'ANALYST_VERIFIED' | 'OVERRIDE'
  verdict: string;  // 'TRUE_POSITIVE' | 'FALSE_POSITIVE' | 'INCONCLUSIVE'
  actor: string;
  notes?: string;
}
```

Layout: vertical timeline, newest first.

Verdict badge colours:
- `TRUE_POSITIVE` → `var(--risk-low-bg)` / `var(--risk-low)`
- `FALSE_POSITIVE` → `var(--risk-critical-bg)` / `var(--risk-critical)`
- `INCONCLUSIVE` → `var(--risk-medium-bg)` / `var(--risk-medium)`

Empty handling: render `"No label history for this alert"`.

---

### Files to MODIFY

#### `src/pages/LabelingPage.tsx`

Add calibration column (JS conditional is fine here):

```tsx
{isAdmin && (
  <td>
    <span className={`calibration-badge calibration-badge--${alert.calibration_status?.toLowerCase()}`}>
      {alert.calibration_status ?? '—'}
    </span>
  </td>
)}
```

Add admin panels to alert detail/expand view:

```tsx
{isAdmin && (
  <>
    <ScoreBreakdownPanel alert={selectedAlert} />
    <ActiveThresholdPanel alert={selectedAlert} />
    <LabelHistoryPanel alert={selectedAlert} />
  </>
)}
```

---

### Verification Checklist

- [ ] All 3 panels exist in `src/components/admin/`
- [ ] Task 7 and Task 8 import from the same file paths
- [ ] Score bars render with correct colours
- [ ] Threshold panel shows current vs recommended with colour coding
- [ ] Label history renders newest-first
- [ ] All panels handle null/undefined/empty gracefully
- [ ] Calibration column hidden in user mode
- [ ] Admin panels hidden in user mode

---

## Task 9 — Admin Layers: Evolution + Charts

### Context

Add two new charts and expanded tooltips. Charts are admin-only.

> **Charting:** Use **Recharts** only. Run `npm install recharts`.
> Do not use any other charting library.

---

### Files to CREATE

#### `src/components/evolution/ThresholdDriftChart.tsx`

Line chart of overall FP rate across Evolution runs.

**Data shape:**

```ts
interface DriftDataPoint {
  run_number: number;
  fp_rate: number;
  date: string;
}
```

Mock data:

```ts
const MOCK_DRIFT = [
  { run_number: 1, fp_rate: 0.489, date: '12 May 2024' },
  { run_number: 2, fp_rate: 0.421, date: '20 May 2024' },
  { run_number: 3, fp_rate: 0.373, date: '27 May 2024' },
];
```

Recharts components: `LineChart`, `Line`, `XAxis`, `YAxis`,
`CartesianGrid`, `Tooltip`, `ResponsiveContainer`

- Line colour: `#FD5108`
- Y-axis formatter: `(v) => \`${(v * 100).toFixed(0)}%\``
- X-axis formatter: `(v) => \`Run ${v}\``
- Height: `220px`

Wrapper:

```tsx
{isAdmin && (
  <CollapsibleSection id="threshold-drift-chart" title="FP Rate Trend Across Runs" defaultOpen={true}>
    <ThresholdDriftChart />
  </CollapsibleSection>
)}
```

---

#### `src/components/evolution/ScoreDistributionChart.tsx`

Histogram of alert counts per 0.1-wide score bucket.

**Data shape:**

```ts
interface ScoreBucket {
  bucket: string;
  total: number;
  fp_count: number;
  tp_count: number;
  fp_rate: number;
}
```

Use the 10-bucket mock data from Task 10's `GET /api/admin/score-distribution`.

Recharts components: `BarChart`, `Bar`, `XAxis`, `YAxis`,
`CartesianGrid`, `Tooltip`, `Legend`, `ResponsiveContainer`

- FP bar: `#FCA5A5`
- TP bar: `#86EFAC`
- Height: `220px`

Wrapper:

```tsx
{isAdmin && (
  <CollapsibleSection id="score-distribution-chart" title="Score Distribution Histogram" defaultOpen={true}>
    <ScoreDistributionChart />
  </CollapsibleSection>
)}
```

---

### Files to MODIFY

#### `src/pages/EvolutionPage.tsx`

- Insert `ThresholdDriftChart` wrapper **above** "FP Rate by Rule" section
- Insert `ScoreDistributionChart` wrapper **above** "FP Rate by Risk Score Range" section
- Check `src/api/client.ts` for `applyRecommendations()`. If it exists
  and is already called, **do not re-implement**
- Add `title` attributes to existing hand-rolled bar elements:
  `title={\`${name}: ${fpCount} FPs out of ${total} (${fpRate}%)\`}`

---

### Verification Checklist

- [ ] `recharts` added to `package.json`
- [ ] Both charts render with mock/real data
- [ ] Both charts only visible in admin mode
- [ ] Both use `ResponsiveContainer`
- [ ] Tooltips appear on hover
- [ ] Y-axis formatted as percentages
- [ ] Existing charts not broken
- [ ] `applyRecommendations()` not duplicated

---

## Task 10 — Backend: Stub Admin Endpoints

### Context

These four endpoints do not yet exist. Build them with hardcoded mock data
so frontend tasks can proceed without waiting.

> `X-View-Mode` is a UI signal only. Do not gate any real security behind it.

---

### Endpoints to CREATE

#### `GET /api/evolution/current-run`

```json
{
  "run_number": 3,
  "timestamp": "2024-05-27T10:32:00Z",
  "status": "COMPLETE",
  "total_alerts_analyzed": 3542,
  "total_feedback_received": 3542,
  "overall_fp_rate": 0.373,
  "confidence": "HIGH",
  "data_sufficiency": "SUFFICIENT",
  "patterns_found": 6,
  "recommendations_count": 5,
  "started_at": "2024-05-27T10:30:00Z",
  "completed_at": "2024-05-27T10:32:00Z"
}
```

---

#### `GET /api/evolution/run-history`

```json
[
  {
    "run_number": 3,
    "timestamp": "2024-05-27T10:32:00Z",
    "status": "COMPLETE",
    "total_alerts_analyzed": 3542,
    "overall_fp_rate": 0.373,
    "confidence": "HIGH",
    "patterns_found": 6
  },
  {
    "run_number": 2,
    "timestamp": "2024-05-20T09:15:00Z",
    "status": "COMPLETE",
    "total_alerts_analyzed": 2891,
    "overall_fp_rate": 0.421,
    "confidence": "MEDIUM",
    "patterns_found": 4
  },
  {
    "run_number": 1,
    "timestamp": "2024-05-12T14:45:00Z",
    "status": "COMPLETE",
    "total_alerts_analyzed": 1204,
    "overall_fp_rate": 0.489,
    "confidence": "MEDIUM",
    "patterns_found": 2
  }
]
```

---

#### `GET /api/admin/rule-weights`

```json
[
  { "rule": "RULE_CASH",         "weight": 0.82, "last_modified": "2024-05-01", "change":  0.05, "status": "ACTIVE" },
  { "rule": "RULE_MULTI_CCY",    "weight": 0.74, "last_modified": "2024-04-15", "change": -0.10, "status": "ACTIVE" },
  { "rule": "RULE_DORMANT",      "weight": 0.68, "last_modified": "2024-03-22", "change":  0.00, "status": "ACTIVE" },
  { "rule": "RULE_FOREIGN_WIRE", "weight": 0.79, "last_modified": "2024-05-10", "change":  0.02, "status": "ACTIVE" },
  { "rule": "RULE_HV",           "weight": 0.91, "last_modified": "2024-02-14", "change":  0.00, "status": "ACTIVE" },
  { "rule": "RULE_CRYPTO",       "weight": 0.85, "last_modified": "2024-04-30", "change":  0.08, "status": "ACTIVE" },
  { "rule": "RULE_PEP",          "weight": 0.95, "last_modified": "2024-01-10", "change":  0.00, "status": "ACTIVE" },
  { "rule": "RULE_DECEASED",     "weight": 0.99, "last_modified": "2024-01-10", "change":  0.00, "status": "ACTIVE" }
]
```

---

#### `GET /api/admin/score-distribution`

```json
[
  { "bucket": "0.0-0.1", "total": 120, "fp_count": 119, "tp_count":   1, "fp_rate": 0.99 },
  { "bucket": "0.1-0.2", "total": 234, "fp_count": 228, "tp_count":   6, "fp_rate": 0.97 },
  { "bucket": "0.2-0.3", "total": 456, "fp_count": 431, "tp_count":  25, "fp_rate": 0.94 },
  { "bucket": "0.3-0.4", "total": 389, "fp_count": 267, "tp_count": 122, "fp_rate": 0.69 },
  { "bucket": "0.4-0.5", "total": 381, "fp_count": 174, "tp_count": 207, "fp_rate": 0.46 },
  { "bucket": "0.5-0.6", "total": 412, "fp_count": 102, "tp_count": 310, "fp_rate": 0.25 },
  { "bucket": "0.6-0.7", "total": 202, "fp_count":  22, "tp_count": 180, "fp_rate": 0.11 },
  { "bucket": "0.7-0.8", "total": 387, "fp_count":   4, "tp_count": 383, "fp_rate": 0.01 },
  { "bucket": "0.8-0.9", "total": 498, "fp_count":   0, "tp_count": 498, "fp_rate": 0.00 },
  { "bucket": "0.9-1.0", "total": 459, "fp_count":   0, "tp_count": 459, "fp_rate": 0.00 }
]
```

---

### Enrich Existing Alert Endpoints

For `GET /api/alerts/:id`, add these fields when `X-View-Mode: admin` header
is present:

```json
"score_breakdown": {
  "transaction_risk": 0.72,
  "customer_risk": 0.45,
  "behavioural_risk": 0.61,
  "account_risk": 0.30,
  "network_risk": 0.55,
  "overall_score": 0.57
},
"active_threshold": {
  "rule": "RULE_HV",
  "current_threshold": 0.30,
  "recommended_threshold": 0.50,
  "fp_rate_at_current": 0.49,
  "fp_rate_at_recommended": 0.21,
  "last_calibrated": "2024-04-15T00:00:00Z"
},
"label_history": [
  {
    "timestamp": "2024-05-27T10:32:00Z",
    "action": "AUTO_FP",
    "verdict": "FALSE_POSITIVE",
    "actor": "Agent 0",
    "notes": null
  }
]
```

---

### `src/api/client.ts` — Add These Functions

```ts
export const getCurrentRun = () =>
  fetch('/api/evolution/current-run').then(r => r.json());

export const getAdminRuleWeights = () =>
  fetch('/api/admin/rule-weights', {
    headers: { 'X-View-Mode': 'admin' }
  }).then(r => r.json());

export const getAdminScoreDistribution = () =>
  fetch('/api/admin/score-distribution', {
    headers: { 'X-View-Mode': 'admin' }
  }).then(r => r.json());
```

> Check if `getRunHistory()` already exists before adding. Do not duplicate.

---

### Verification Checklist

- [ ] All 4 endpoints return HTTP 200 with correct JSON shape
- [ ] `X-View-Mode` header accepted without errors
- [ ] Enriched fields returned when admin header is present
- [ ] Fields absent when header is not present
- [ ] All client functions added to `src/api/client.ts`
- [ ] No existing endpoints broken

---

## Task 11 — Live Processing Feedback

### Context

The UI is currently silent during all async operations. This task adds six
types of live feedback. Build Task 11f (Toast) first or in parallel as other
sub-tasks depend on it.

---

### Task 11a — PipelineStepper

#### `src/components/common/PipelineStepper.tsx`

**Props:**

```ts
interface PipelineStepperProps {
  currentStatus:
    | 'ENRICHING'
    | 'ASSESSING'
    | 'CATEGORISING'
    | 'SUMMARISING'
    | 'COMPLETE'
    | 'TRIAGED';
}
```

**Steps (always this order):** `ENRICHING → ASSESSING → CATEGORISING → SUMMARISING`

**Step visual states:**

| State | Circle | Label |
|---|---|---|
| Past | Filled, muted | `var(--text-muted)` |
| Current | Filled, pulsing orange | `var(--pwc-orange)` |
| Future | Empty outline | `var(--text-muted)` |

**Pulse CSS:**

```css
@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.3; }
}
.step-current .step-dot {
  animation: pulse-dot 1.2s ease-in-out infinite;
}
```

**Where to use:**
- `src/components/alerts/AlertTable.tsx` — replace status badge only for
  alerts with status `ENRICHING`, `ASSESSING`, `CATEGORISING`, `SUMMARISING`
- `src/pages/AlertDetailPage.tsx` — replace status badge under same condition
- Keep existing green `TRIAGED` badge for all finished alerts

---

### Task 11b — Agent Activity Feed

#### `src/components/agents/ActivityFeed.tsx`

**Data shape** (poll `GET /api/activity/feed` every 2000ms):

```ts
interface ActivityLogLine {
  timestamp: string;
  agent: 'ENRICHMENT' | 'ASSESSMENT' | 'CATEGORY' | 'SUMMARY' | 'AUTOLABEL' | 'EVOLUTION';
  message: string;
  alert_id?: string;
}
```

Layout: scrollable log panel, `max-height: 400px`, auto-scrolls to bottom.

Format per line:
```
[ENRICHMENT]  10:32:05  Fetching transaction history for CUS-10006318...
```

Agent label colours:

| Agent | Colour |
|---|---|
| `ENRICHMENT` | `var(--status-processing)` |
| `ASSESSMENT` | `var(--risk-medium)` |
| `CATEGORY` | `var(--risk-high)` |
| `SUMMARY` | `var(--pwc-orange)` |
| `AUTOLABEL` | `var(--risk-low)` |
| `EVOLUTION` | `var(--risk-critical)` |

**Where to use:**
- `src/pages/AgentsPage.tsx` — primary panel on this page
- `src/pages/AlertQueuePage.tsx` — inside a `<CollapsibleSection id="activity-feed" defaultOpen={false}>`

**Backend:** Add `GET /api/activity/feed` returning last 50 log lines,
newest last.

---

### Task 11c — Typewriter Effect

#### `src/hooks/useTypewriter.ts`

```ts
import { useState, useEffect } from 'react';

export function useTypewriter(text: string, speed: number = 18): string {
  const [displayText, setDisplayText] = useState('');

  useEffect(() => {
    setDisplayText('');
    if (!text) return;
    let i = 0;
    const id = setInterval(() => {
      setDisplayText(text.slice(0, i + 1));
      i++;
      if (i >= text.length) clearInterval(id);
    }, speed);
    return () => clearInterval(id);
  }, [text, speed]);

  return displayText;
}
```

**Where to apply:**

`src/components/alerts/InvestigationSummary.tsx`:

```tsx
const displayed = useTypewriter(alert.investigation_summary ?? '');
return <p className="investigation-text">{displayed}</p>;
```

Also apply to categorisation reason text fields in alert detail views.

---

### Task 11d — Evolution Run Live Counter

No new file needed. This is the RUNNING display state in `LoopProgressPanel`
(Task 5). Ensure the panel polls every 3s and the RUNNING state shows:

```
● RUNNING
Round 3 / 10  ·  Processing 847 alerts  ·  FP rate: 37% → 23%
[progress bar, width = current_round / total_rounds × 100%]
```

Reduce to 30s polling when status is `COMPLETE` or `ERROR`.

---

### Task 11e — Labeling Progress Bar

#### Modify `src/pages/LabelingPage.tsx`

State to add:

```ts
const [isLabeling, setIsLabeling]     = useState(false);
const [labeledCount, setLabeledCount] = useState(0);
const [totalToLabel, setTotalToLabel] = useState(0);
const [elapsedSeconds, setElapsedSeconds] = useState(0);
```

When "Run Auto-Label" is clicked:
1. `setIsLabeling(true)`
2. Show progress section, hide button
3. Poll labeling count endpoint every 2s
4. Compute estimate: `Math.ceil((totalToLabel - labeledCount) / (labeledCount / elapsedSeconds))`
5. On complete: `setIsLabeling(false)`, fire success Toast

Progress section JSX:

```tsx
{isLabeling && (
  <div className="labeling-progress">
    <span className="labeling-progress-label">Labeling alerts...</span>
    <div className="progress-bar-track">
      <div
        className="progress-bar-fill"
        style={{ width: `${(labeledCount / totalToLabel) * 100}%` }}
      />
    </div>
    <span className="labeling-progress-count">
      {labeledCount.toLocaleString()} / {totalToLabel.toLocaleString()}
      {elapsedSeconds > 2 && ` · ~${estimatedSeconds}s remaining`}
    </span>
  </div>
)}
```

CSS (add to `LabelingPage.css`):

```css
.progress-bar-track {
  width: 100%;
  height: 6px;
  background: var(--surface-border);
  border-radius: 3px;
  overflow: hidden;
}
.progress-bar-fill {
  height: 100%;
  background: var(--pwc-orange);
  border-radius: 3px;
  transition: width 300ms ease;
}
.labeling-progress {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 0;
}
.labeling-progress-label,
.labeling-progress-count {
  font-size: 13px;
  color: var(--text-secondary);
}
```

---

### Task 11f — Toast Notifications

#### `src/components/common/Toast.tsx`

```ts
interface ToastItem {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info';
  duration?: number;  // ms, default 4000
}
```

Visual spec:
- Position: `fixed; bottom: 24px; right: 24px; z-index: 9999`
- `min-width: 280px`, `max-width: 400px`
- Slide in: `transform: translateX(110%)` → `translateX(0)`, `300ms ease`
- Auto-dismiss after `duration` ms
- Stackable with `8px` vertical gap
- `×` button for manual dismiss

Type styling:

| Type | Left border | Icon |
|---|---|---|
| `success` | `var(--risk-low)` | `✓` |
| `error` | `var(--risk-critical)` | `✗` |
| `info` | `var(--status-processing)` | `ℹ` |

#### `src/context/ToastContext.tsx`

```ts
interface ToastContextValue {
  addToast: (message: string, type: ToastItem['type'], duration?: number) => void;
  removeToast: (id: string) => void;
}
```

#### `src/App.tsx`

```tsx
<ViewModeProvider>
  <ToastProvider>
    <BrowserRouter>
      {/* existing routes */}
    </BrowserRouter>
  </ToastProvider>
</ViewModeProvider>
```

**Trigger events:**

| Event | Message | Type |
|---|---|---|
| Auto-label completes | `✓ {n} alerts labeled — {x}% confidence` | `success` |
| Evolution run completes | `✓ Evolution complete — {n} recommendations ready` | `success` |
| Batch triage completes | `✓ Batch triage complete — {n} alerts processed` | `success` |
| Any API error | `✗ {error.message}` | `error` |
| Recommendation applied | `✓ Recommendation logged as applied` | `success` |

---

### Task 11 — Combined Verification Checklist

- [ ] PipelineStepper renders on in-flight alert rows
- [ ] Finished alerts still show existing TRIAGED badge
- [ ] Pulse animation works on current step
- [ ] Activity Feed renders on Agents page and auto-scrolls
- [ ] Agent label colours match table above
- [ ] Typewriter plays on fresh AI text, does not replay on re-renders
- [ ] Live counter shows in LoopProgressPanel during RUNNING state
- [ ] Labeling progress bar appears and animates during auto-label
- [ ] Estimated time updates as rate changes
- [ ] Toast slides in from right, auto-dismisses after 4s
- [ ] Multiple toasts stack without overlap
- [ ] `×` button dismisses individual toasts
- [ ] All 5 trigger events produce correct toasts
- [ ] All intervals cleaned up on component unmount

---

## Task 12 — UI Polish & Fixes

### Context

Standalone visual improvements. Each fix is small and surgical.
Change only what is specified. Do not refactor surrounding code.

---

### 12a — Coverage Progress Bar on Labeling Page

**File:** `src/pages/LabelingPage.tsx`

Add immediately below the stats row:

```tsx
<div className="coverage-bar-wrapper">
  <div className="progress-bar-track">
    <div
      className="progress-bar-fill"
      style={{ width: `${coveragePercent}%` }}
    />
  </div>
  <span className="coverage-label">{coveragePercent}% labeled</span>
</div>
```

`coveragePercent = Math.round((analystLabeled / totalAlerts) * 100)`

Reuse `.progress-bar-track` and `.progress-bar-fill` CSS from Task 11e.

---

### 12b — "View All" Button Shows Count

**File:** `src/pages/DashboardPage.tsx`

Change button label from `View All` to `View All ({count})`.
`count = criticalCount + highCount` from already-loaded dashboard data.
**Do not make a new API call.**

---

### 12c — Show 5 Rows in Recent Alerts

**File:** `src/pages/DashboardPage.tsx`

Find where the recent alerts array is sliced. Change the limit from `2` to `5`.

---

### 12d — Pattern Card Severity Tints

Find the FP pattern card component in `src/components/evolution/` or
`src/pages/EvolutionPage.tsx`.

```tsx
className={`pattern-card pattern-card--${pattern.severity.toLowerCase()}`}
```

```css
.pattern-card--high {
  background: var(--risk-critical-bg);
  border-left: 3px solid var(--risk-critical-border);
}
.pattern-card--medium {
  background: var(--risk-medium-bg);
  border-left: 3px solid var(--risk-medium-border);
}
```

---

### 12e — Prominent "SEEN Nx" Badge

Find where `seen_count` renders. Apply:

```css
.seen-badge {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
  background: var(--surface-elevated);
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid var(--surface-border-strong);
}
```

---

### 12f — What-If Simulator Verdict Display

Find the What-If Simulator component.

```tsx
const VERDICT_CONFIG = {
  APPLY: {
    label: 'APPLY',
    color: 'var(--risk-low)',
    bg: 'var(--risk-low-bg)',
  },
  CAUTION: {
    label: 'CAUTION',
    color: 'var(--risk-medium)',
    bg: 'var(--risk-medium-bg)',
  },
  DO_NOT_APPLY: {
    label: 'DO NOT APPLY',
    color: 'var(--risk-critical)',
    bg: 'var(--risk-critical-bg)',
  },
} as const;
```

Add explanation sentence below verdict numbers:
- `APPLY` → `"This change avoids {fpsAvoided} FPs with minimal TP risk. Safe to apply."`
- `CAUTION` → `"This change avoids {fpsAvoided} FPs but puts {tpsAtRisk} TPs at risk. Review carefully."`
- `DO_NOT_APPLY` → `"Suppressing this rule risks {tpsAtRisk} true positives — net negative impact. Do not apply."`

Use real values from simulation result. Do not hardcode numbers.

---

### 12g — Default Simulator to Highest-Priority Recommendation

**File:** What-If Simulator component

Set default selected rule from `recommendations[0].rule` (data-driven).
Fallback to first dropdown option if `recommendations` is empty or null.

---

### 12h — Standardise Amount Formatting

**Files:** `src/components/alerts/AlertTable.tsx` and all amount-rendering
components.

```ts
const formatAmount = (amount: number): string =>
  `$${amount.toLocaleString('en-AU', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
```

Replace all existing amount formatting with this function.

---

### 12i — Flag Suspicious Low Amounts

**File:** `src/components/alerts/AlertTable.tsx`

When **both**: `amount < 100` AND `risk === 'HIGH' || risk === 'CRITICAL'`:

```tsx
<span className={amount < 100 && isHighRisk ? 'amount-suspicious' : ''}>
  {amount < 100 && isHighRisk ? '⚠ ' : ''}{formatAmount(amount)}
</span>
```

```css
.amount-suspicious { color: var(--risk-medium); }
```

---

### 12j — Evolution Page Sticky Sub-Navigation

**File:** `src/pages/EvolutionPage.tsx`

```tsx
const EVOLUTION_SECTIONS = [
  { id: 'current-run',     label: 'Current Run'     },
  { id: 'loop-progress',   label: 'Loop Progress'   },
  { id: 'fp-analytics',    label: 'FP Analytics'    },
  { id: 'fp-patterns',     label: 'Patterns'        },
  { id: 'recommendations', label: 'Recommendations' },
  { id: 'unresolvable',    label: 'Unresolvable'    },
  { id: 'simulator',       label: 'Simulator'       },
];
```

Add `id` attribute to each matching section heading on the page.

Click handler:
```ts
document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
```

Use `IntersectionObserver` to mark active section (threshold: `0.5`).

```css
.evolution-subnav {
  position: sticky;
  top: 48px;
  z-index: 10;
  background: var(--surface-base);
  border-bottom: 1px solid var(--surface-border);
  display: flex;
  gap: 0;
  padding: 0 24px;
  overflow-x: auto;
}
.evolution-subnav-item {
  padding: 10px 16px;
  font-size: 13px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  color: var(--text-secondary);
  white-space: nowrap;
  transition: color 150ms ease, border-color 150ms ease;
}
.evolution-subnav-item:hover { color: var(--text-primary); }
.evolution-subnav-item.active {
  border-bottom-color: var(--pwc-orange);
  color: var(--text-primary);
}
```

---

### 12k — Per-Recommendation Apply Buttons with Confirmation

Find the Recalibration Recommendations component.

Per-card button:

```tsx
<button
  className={`btn-apply ${rec.applied ? 'btn-apply--done' : ''}`}
  onClick={() => setConfirmingId(rec.id)}
  disabled={rec.applied}
>
  {rec.applied ? '✓ Applied' : 'Log as Applied'}
</button>
```

Confirmation modal when `confirmingId` is set:

```
Title:   Apply Recommendation P{n}?
Body:    "{recommendation.title}"
         This action will be recorded in the audit trail.
Buttons: [Cancel]  [Confirm & Apply]
```

On "Confirm & Apply":
1. Call `applyRecommendations(confirmingId)`
2. Mark `rec.applied = true` in local state
3. `setConfirmingId(null)`
4. `addToast('✓ Recommendation logged as applied', 'success')`

On "Cancel": `setConfirmingId(null)` only.

---

### 12l — Section Header Visual Enhancement

**File:** `src/index.css` (append after dark theme block)

```css
.section-header {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-secondary);
  padding-left: 12px;
  border-left: 3px solid var(--pwc-orange);
  margin-bottom: 16px;
  line-height: 1.4;
}
```

Apply class `section-header` to existing section titles in:

- `src/pages/EvolutionPage.tsx`:
  `FP RATE BY RULE`, `FP RATE BY TYPOLOGY`, `FP PATTERNS IDENTIFIED`,
  `RECALIBRATION RECOMMENDATIONS`, `UNRESOLVABLE ALERTS`, `WHAT-IF SIMULATOR`
- `src/pages/DashboardPage.tsx`:
  `ALERTS BY RISK TIER`, `ALERTS BY TYPOLOGY`, `RECENT CRITICAL / HIGH ALERTS`
- `src/pages/LabelingPage.tsx`:
  Main labeling section header

Do not change any heading text content. Only add the CSS class.

---

### Task 12 — Combined Verification Checklist

- [ ] Coverage bar renders and reflects actual percentage
- [ ] "View All (n)" shows correct count without new API call
- [ ] 5 rows visible in Recent Alerts
- [ ] HIGH pattern cards have red tint
- [ ] MEDIUM pattern cards have amber tint
- [ ] SEEN badge is bold and distinct
- [ ] Simulator verdict displays large with background colour
- [ ] Explanation sentence uses real simulation values
- [ ] Simulator defaults to P1 rule from recommendations
- [ ] All amounts show exactly 2 decimal places
- [ ] Suspicious low amounts on high-risk alerts show `⚠`
- [ ] Evolution sub-nav sticks at correct scroll position
- [ ] Sub-nav smooth-scrolls to sections on click
- [ ] Active section highlighted while scrolling
- [ ] Per-recommendation apply buttons on every card
- [ ] Confirmation modal appears before applying
- [ ] Applied button shows `✓ Applied` and is disabled
- [ ] Success toast fires after applying
- [ ] Section headers have left orange border across all three pages

---

## Global Rules

> These rules apply to **every single task** without exception.

1. **Never hardcode a colour value** that has a corresponding CSS variable
   in `:root`. Always use `var(--)`. The sole exception is `LoopProgressPanel`
   (Task 5), which hardcodes dark values intentionally by design.

2. **Never duplicate a component.** If it exists, import it. If needed in
   two places, build it once in `src/components/common/` or
   `src/components/admin/` and import in both.

3. **Never remove existing functionality.** All tasks are purely additive.
   Modify only the lines specified. Do not refactor, rename, or reorganise
   surrounding code.

4. **Always clean up side effects.** Every `setInterval`, `setTimeout`,
   and `addEventListener` created inside a `useEffect` must return a
   cleanup function: `return () => clearInterval(id)`.

5. **Handle null and undefined defensively.** Every component that reads
   from an API must gracefully handle `null`, `undefined`, and `[]` without
   crashing. Always render a fallback.

6. **Admin content must never appear in user mode.** Toggle to user mode
   and verify all admin content is hidden before marking any task complete.

7. **Read before writing.** Read any file you intend to modify in full
   before making changes. Make only the surgical edits described in the task.

8. **Verify the checklist.** Do not mark a task done until every item
   in its verification checklist is confirmed.
```

---

Save that entire block as **`aml-triage-ui-tasks.md`**. It is the complete, self-contained file containing all 12 tasks, every code snippet, all mock data, all CSS, all type definitions, and all verification checklists — ready to hand directly to an AI coding agent.