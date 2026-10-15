---
version: alpha
name: AML Insight
description: A precision investigation workspace built around source evidence and accountable review.
colors:
  primary: "#315dea"
  background: "#f3f5f9"
  surface: "#ffffff"
  ink: "#17243b"
  muted: "#627089"
  navigation: "#101c31"
  border: "#e2e7f0"
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

## Overview

The North Star is a financial investigation instrument: cool, measured, and immediately legible. The user is an AML analyst inspecting synthetic transaction evidence; the task is to understand signals before human review. This is a product workspace, not a marketing page. User request on 15 October 2026 authorizes a sleeker, modern visual direction.

The signature is the evidence-to-review strip: source evidence, numerical risk scoring, pending AI triage, and human review. It makes system boundaries visible without inventing progress. Midnight navigation anchors a bright investigation canvas; cobalt identifies interaction rather than financial danger.

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

The supplied Lighter/Raylon references inform sculpted navigation and icon-led summary cards without changing the bright investigation canvas. The sidebar has a quiet dotted texture and a beveled selection surface with inset highlights and a grounded shadow. Its indicator slides between workspace entries. Cards use a restrained surface gradient and small icon tiles; their label is on the left and value on the right. No glass blur over financial facts. Global scrollbar tokens cover every owned scroll region; forced colors revert to system behavior.

## Shapes

Frontmatter radii map to `--radius-panel` and `--radius-control`. Panels use 14px, inputs/actions 8px, status pills fully rounded. Avoid nested decorative cards when a divider suffices.

## Components

Shared CSS recipes own `.primary`, `.panel`, `.badge`, `.error`, `.search`, and `.nav-link`; `Icon.tsx` owns consistent outline SVGs. Every enabled action has hover, pressed and visible focus states. Disabled actions remain labeled with their reason. Busy actions preserve width. The canonical `SignIn` modal uses native dialog modality, focus restoration, inline validation, masked passwords and a show/hide control. No browser alert/confirm/prompt.

Search is immediate over a fixed 12-case publication, with clear, count and no-results recovery. Loading uses a stable app-owned spinner region, never simulated progress. Risk bars share a 6px height and fully rounded ends; only their value-dependent widths differ. Empty scores render as unavailable. Completed workflow checks use the success green; pending and missing-context stages never receive a completion check.

Sidebar labels roll downward one character after another on hover, focus, and selection: 440ms per character, 24ms stagger. A duplicate glyph enters from above; duplicates are hidden from assistive technology and the button has one stable accessible name. Selection movement lasts 380ms. No title, number, or content panel rolls or animates. The explicitly requested Evolution connector nudge is the only added motion outside the sidebar (600ms on hover/focus). Its explanation switches immediately in a reserved region. All motion is disabled under reduced motion; selected states remain visible. See `UX-CONTRACT.md` for interaction ownership and state rules.

## Do's and Don'ts

- Do keep evidence IDs, amounts and uncertainty legible at every viewport.
- Do reuse the same panels, buttons, status tones and empty/error treatments across all three screens.
- Don't fabricate model outputs, cost savings, completed stages or human verdicts.
- Don't replace a missing-context warning with a reassuring numerical score.
