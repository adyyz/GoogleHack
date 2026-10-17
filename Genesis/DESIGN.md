---
version: alpha
name: AML Insight
description: A precision investigation workspace built around source evidence and accountable review.
colors:
  primary: "#315dea"
  papaya: "#ed8a53"
  background: "#e4e9f1"
  surface: "#f5f5f2"
  paper: "#fafaf7"
  selection: "#cdd8ec"
  selection-border: "#6c85b9"
  selection-ink: "#203966"
  primary-strong: "#2448bd"
  ink: "#17243b"
  muted: "#4b5d75"
  navigation: "#101c31"
  border: "#c9d3e1"
  success: "#18745e"
  warning: "#946019"
  danger: "#b33f4b"
typography:
  display:
    fontFamily: "Bahnschrift, Segoe UI, sans-serif"
  body:
    fontFamily: "Segoe UI, Arial, sans-serif"
  mono:
    fontFamily: "Cascadia Code, Consolas, monospace"
rounded:
  DEFAULT: "14px"
  control: "8px"
spacing:
  panel: "24px"
  gap: "20px"
components:
  panel:
    rounded: "{rounded.DEFAULT}"
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
  button:
    rounded: "{rounded.control}"
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
  canvas:
    backgroundColor: "{colors.background}"
  navigation:
    backgroundColor: "{colors.navigation}"
    textColor: "{colors.surface}"
  caption:
    textColor: "{colors.muted}"
  divider:
    backgroundColor: "{colors.border}"
  success:
    textColor: "{colors.success}"
  warning:
    textColor: "{colors.warning}"
  error:
    textColor: "{colors.danger}"
---

# AML Insight design system

Identity filters, case progress and Evolution review/recommendation tables extend the existing evidence-first workspace. Preserve the midnight navigation, cobalt primary actions, existing type scale, native-select ownership and shared dialog/notice behavior. Review coverage uses four textual totals rather than speculative charts; category tables state their denominators and unavailable values. Recommendation effects distinguish forecast, synthetic replay and observed reviews without implying causal gains.

## Overview

The North Star is a financial investigation instrument: cool, measured, and immediately legible. The user is an AML analyst inspecting synthetic transaction evidence; the task is to understand signals before human review. This is a product workspace, not a marketing page. User request on 15 October 2026 authorizes a sleeker, modern visual direction.

The signature is the evidence-to-review strip: source evidence, numerical risk scoring, pending AI triage, and human review. It makes system boundaries visible without inventing progress. Midnight navigation anchors a muted blue-grey investigation canvas; cobalt identifies interaction rather than financial danger.

English, en-AU number/date conventions, AUD equivalent amounts, explicit UTC transaction times. Australia is the planning context; no Japanese locale or Japan-market scope is established. Desktop analyst work is primary; mobile inspection and sign-in remain available.

Avoid the earlier green/serif editorial treatment, neon trading-terminal styling, decorative financial charts, and fake agent activity.

Runtime CSS is canonical (mapping model B): `frontend/style.css` owns all tokens. This document mirrors accepted values; components consume CSS variables without a theme library. `scripts/check-design.cjs` checks token mirrors and documented type/radius values.

## Colors

Frontmatter colors map one-to-one to `--color-{name}` in `:root`. Navigation has its own pale text tokens. Supporting semantic tints live beside the base tokens in CSS. Warning and danger always include words; missing context never looks like low risk. One light workspace theme is supported, with system colors in forced-colors mode.

## Typography

Display maps to `--font-display`, body to `--font-body`, mono to `--font-mono`. Bahnschrift gives restrained instrument-like headings; Segoe UI handles prose and controls; Cascadia/Consolas handles evidence identifiers and tabular numbers. All fonts are local with fallbacks, so no font download or late swap occurs. Titles 30–32px, panel headings 15–18px, body 13–14px, utility labels at least 11px. Data uses tabular numerals. Full monetary precision remains stored in integer minor units; UI conventions are unchanged by this visual pass.

## Layout

230px navigation, a flexible investigation canvas, a 290px queue, and a natural-height detail column. The queue alone owns bounded list scrolling; the page remains document-scrolled. Tables own horizontal overflow. At 1180px the queue narrows; at 980px evidence panels stack; at 760px navigation becomes a horizontal mobile header, and the queue becomes a horizontal case strip. Spacing tokens map to `--space-panel` and `--space-gap`. No full-page fixed-height clipping.

## Elevation & Depth

The supplied Lighter/Raylon references inform sculpted navigation and icon-led summary cards without changing the muted blue-grey investigation canvas. The sidebar has a quiet dotted texture and a beveled selection surface with inset highlights and a grounded shadow. Its indicator slides between workspace entries. Cards use a restrained surface gradient and small icon tiles; their label is on the left and value on the right. No glass blur over financial facts. Global scrollbar tokens cover every owned scroll region; forced colors revert to system behavior.

## Shapes

Frontmatter radii map to `--radius-panel` and `--radius-control`. Panels use 14px, inputs/actions 8px, status pills fully rounded. Avoid nested decorative cards when a divider suffices.

## Components

Evolution evidence uses the existing panel rhythm, native form controls and shared confirmation dialog. Frozen-input counts and provenance lead; full candidate/snapshot hashes wrap as utility text. Private investigation prose uses the same source-ID treatment as the transaction trail. The approved slate palette uses teal, violet and amber category accents, labeled decorative emoji and existing native controls. No chart dependency is added.

Gap closure retains this visual identity. `Dialog.tsx` owns native modal variants for sign-in, usage and confirmations. `Usage.tsx` owns the public/private usage renderer and the single parent completion notification. Token charts use the existing primary/success/warning/danger/muted colors with textual category labels; the provider total stays central. When data cannot reconcile, a restrained labeled unavailable surface replaces the chart. Operator review and Admin use existing panels and controls, platform-native select popups, document scrolling and bounded history tables. No new font, theme, motion or package is introduced.

Shared CSS recipes own `.primary`, `.panel`, `.badge`, `.error`, `.search`, and `.nav-link`; `Icon.tsx` owns consistent outline SVGs. Every enabled action has hover, pressed and visible focus states. Disabled actions remain labeled with their reason. Busy actions preserve width. The canonical `SignIn` modal uses native dialog modality, focus restoration, inline validation, masked passwords and a show/hide control. No browser alert/confirm/prompt.

Search is immediate over a fixed 12-case publication, with clear, count and no-results recovery. Loading uses a stable app-owned spinner region, never simulated progress. Risk bars share a 6px height and fully rounded ends; only their value-dependent widths differ. Empty scores render as unavailable. Completed workflow checks use the success green; pending and missing-context stages never receive a completion check.

Sidebar labels roll downward one character after another on hover, focus, and selection: 440ms per character, 24ms stagger. A duplicate glyph enters from above; duplicates are hidden from assistive technology and the button has one stable accessible name. Selection movement lasts 380ms. No title, number, or content panel rolls or animates. The explicitly requested Evolution connector nudge is the only added motion outside the sidebar (600ms on hover/focus). Its explanation switches immediately in a reserved region. All motion is disabled under reduced motion; selected states remain visible. See `UX-CONTRACT.md` for interaction ownership and state rules.

## Do's and Don'ts

- Do keep evidence IDs, amounts and uncertainty legible at every viewport.
- Do reuse the same panels, buttons, status tones and empty/error treatments across workspace screens.
- Don't fabricate model outputs, cost savings, completed stages or human verdicts.
- Don't replace a missing-context warning with a reassuring numerical score.


Investigation density: the source title and profile lead the case header; identity/account metadata occupies a quiet right-hand panel and stacks on narrow screens. Full reference IDs live in native disclosures, with transaction citations linking to the matching trail row. The trail owns a sticky-header scroll surface after ten 48px rows; feedback history owns a 260px maximum-height list. Evidence, investigation results and analyst decisions have separate bordered/banner headings. Frozen reviews collapse to a compact saved card with an expandable original note. Existing colors, typography and native controls remain canonical.

Cross-screen spacing: notices separate from the next section by 20px. Panel headings wrap their actions; inputs share the existing border/radius/spacing tokens. At 1050px and below the investigation queue becomes a horizontal card list above the detail, preventing tablet compression. System-role cards use a three-column grid, two on mobile. Optional cached/reasoning/tool token rows appear only for reported positive values; absent metadata never implies a measured zero or a reconciled chart.


Investigation layout boundary: the queue and shared evidence form the first grid row. The investigation workspace starts a new row spanning both columns; triage, private analysis, analyst review and aggregate usage use the full main-content width. The desktop queue stretches only through the evidence row, with its own scrolling list. Published evidence headings and source/risk checks are identical across access levels; private triage/review indicators and active-policy information belong to the investigation workspace.


## Rule intelligence - 18 October 2026

The approved palette shifts the canvas to blue-grey #e4e9f1 and panels to warm paper #f4f1e9, with #c9d3e1 borders and #4b5d75 muted text. Inputs use ivory paper #fbf8f0. Midnight navigation, typography and cobalt actions persist. The rule matrix is the focal instrument: colored category chips, equal native view controls, zero-review rows, textual denominators and compact stored-trend bars. Teal, violet and amber distinguish categories without implying human verdicts. Labeled decorative emoji are aria-hidden. Shared dialogs, scroll owners, reduced motion and 320px containment remain canonical.


## Paper surfaces and selected states - 18 October 2026

User-approved refinement: matte warm paper panels (#f4f1e9) with a restrained CSS fiber pattern, ivory paper inputs (#fbf8f0), and the existing slate canvas. Selected queue cards, matrix rows and workflow steps share a deeper blue fill (#cdd8ec), ink (#203966) and border (#6c85b9); active matrix tabs use cobalt #2448bd. Selection also retains its edge marker and pressed/current semantics. Decorative, aria-hidden emoji introduce a few stage headings inspired by Evo_Pitch; the native controls, midnight navigation, typography and semantic verdict colors remain unchanged.


## Connected investigation brief - 18 October 2026

The brief leads with Overview and Key findings. Counter-evidence, Missing information, Next steps and Limitations form a connected two-row winding trail on desktop and a single ordered vertical trail on mobile. Numbered nodes express reading order, colored header bands distinguish evidence, gaps and actions, and connectors are decorative. Native source links and evidence disclosures remain intact. Panels now use neutral off-white #f5f5f2, inputs #fafaf7, and no fiber texture; this supersedes the stronger paper treatment above. Usage with incomplete categories uses a plain token total and explanation instead of an unavailable-chart box.


## Toast countdown - 18 October 2026

Completion toasts use a papaya #ed8a53 time-remaining bar, driven by the same eight-second duration as auto-dismiss. Each parent ID remounts the bar and restarts its timer. The bar is decorative; a visible duration label provides the same information without motion. Reduced-motion mode hides the animation and retains the label.


### Connected case stages ? 18 October 2026

Source evidence, Risk scoring, AI triage and Analyst review share one ordered four-stage rail in both public and operator sessions. Success-green links show completed stages; neutral links keep locked/pending stages visibly connected. At small widths the trail wraps into two rows without crossing text. Public AI/review states stay locked. Case completion excludes inactive policy-excluded alerts, retaining frozen/in-progress work; missing context never gains a false risk-scoring check.
