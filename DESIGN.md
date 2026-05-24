---
version: alpha
name: RL-MEC Operations Console
description: A dense dark-mode monitoring dashboard for reinforcement-learning benchmark runs, built around navy surfaces, blue telemetry accents, monospace data, and restrained operational states.
colors:
  primary: "#3B82F6"
  on-primary: "#FFFFFF"
  primary-hover: "#60A5FA"
  primary-pressed: "#2563EB"
  primary-container: "#1E3A5F"
  primary-container-muted: "#172A46"
  background: "#0A0E1A"
  background-mid: "#0C1222"
  background-soft: "#0F1420"
  surface: "#111827"
  surface-muted: "#0F172A"
  surface-elevated: "#1A2332"
  surface-console: "#060A12"
  surface-danger: "#320A14"
  surface-danger-deep: "#1E0A0F"
  on-surface: "#F1F5F9"
  on-surface-strong: "#FFFFFF"
  on-surface-muted: "#94A3B8"
  on-surface-subtle: "#CBD5E1"
  outline: "#1E3A5F"
  outline-soft: "#18243A"
  outline-strong: "#2563EB"
  focus-ring: "#3B82F6"
  selection: "#162544"
  info: "#06B6D4"
  info-container: "#0B3442"
  on-info: "#E0F2FE"
  success: "#10B981"
  success-strong: "#34D399"
  success-container: "#0B3A30"
  on-success: "#D1FAE5"
  warning: "#F59E0B"
  warning-container: "#332718"
  on-warning: "#FEF3C7"
  danger: "#EF4444"
  danger-strong: "#DC2626"
  danger-deep: "#B91C1C"
  danger-container: "#3B0F16"
  on-danger: "#FEE2E2"
  violet: "#8B5CF6"
  violet-container: "#2D1F4C"
  on-violet: "#EDE9FE"
  rose: "#F43F5E"
  chart-axis: "#BFCAE1"
  chart-legend: "#DBE6FF"
  chart-gridline: "#202A3A"
typography:
  page-title:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: 800
    lineHeight: 1.15
    letterSpacing: 0em
  section-title:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: 0.06em
  panel-subtitle:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: 0em
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.45
    letterSpacing: 0em
  caption:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: 0.04em
  button-label:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: 0.01em
  badge-label:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: 700
    lineHeight: 1
    letterSpacing: 0.03em
  data-lg:
    fontFamily: JetBrains Mono
    fontSize: 24px
    fontWeight: 800
    lineHeight: 1.2
    letterSpacing: 0em
  data-md:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: 700
    lineHeight: 1.45
    letterSpacing: 0em
  data-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: 500
    lineHeight: 1.45
    letterSpacing: 0em
  table-header:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: 0.04em
  log-line:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: 0em
spacing:
  space-00: 0px
  space-01: 2px
  space-02: 4px
  space-03: 6px
  space-04: 8px
  space-05: 10px
  space-06: 12px
  space-07: 14px
  space-08: 16px
  space-09: 18px
  space-10: 20px
  space-11: 24px
  space-12: 28px
  space-13: 32px
  content-max-width: 1520px
  control-height: 38px
  mini-control-height: 28px
  chart-height: 260px
  convergence-chart-height: 320px
  log-window-height: 280px
  run-list-max-height: 380px
  run-tile-min-width: 300px
rounded:
  xs: 4px
  sm: 6px
  md: 8px
  lg: 10px
  full: 9999px
radii:
  xs: 4px
  sm: 6px
  md: 8px
  lg: 10px
  full: 9999px
borders:
  hairline: 1px
  accent: 2px
  active-rail: 3px
  section-marker-width: 3px
  section-marker-height: 16px
  focus-ring: 2px
  focus-ring-offset: 2px
shadows:
  none:
    color: "#000000"
    opacity: 0
    offsetX: 0px
    offsetY: 0px
    blur: 0px
    spread: 0px
  panel:
    color: "#000000"
    opacity: 0.35
    offsetX: 0px
    offsetY: 4px
    blur: 24px
    spread: 0px
  floating:
    color: "#000000"
    opacity: 0.45
    offsetX: 0px
    offsetY: 12px
    blur: 40px
    spread: 0px
  hover:
    color: "#000000"
    opacity: 0.30
    offsetX: 0px
    offsetY: 4px
    blur: 12px
    spread: 0px
  active-glow:
    color: "#3B82F6"
    opacity: 0.10
    offsetX: 0px
    offsetY: 0px
    blur: 20px
    spread: 0px
  danger-glow:
    color: "#EF4444"
    opacity: 0.05
    offsetX: 0px
    offsetY: 0px
    blur: 30px
    spread: 0px
elevation:
  background:
    level: 0
  panel:
    level: 1
  selected-card:
    level: 2
  floating-header:
    level: 3
  danger-zone:
    level: 1
motion:
  duration-instant: 0ms
  duration-fast: 150ms
  duration-base: 200ms
  duration-chart: 400ms
  duration-pulse: 2000ms
  easing-standard: cubic-bezier(0.4, 0, 0.2, 1)
  easing-pulse: ease-in-out
  hover-lift: 1px
  tile-hover-lift: 2px
layout:
  desktop-page-padding: 24px
  tablet-page-padding: 14px
  mobile-page-padding: 10px
  desktop-grid-gap: 18px
  card-grid-gap: 12px
  control-gap: 10px
  breakpoint-large: 1100px
  breakpoint-medium: 768px
  breakpoint-small: 480px
components:
  app-header:
    backgroundColor: "{colors.surface-elevated}"
    textColor: "{colors.on-surface}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.lg}"
    padding: "{spacing.space-11}"
  panel:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    typography: "{typography.body-md}"
    rounded: "{rounded.lg}"
    padding: "{spacing.space-10}"
  run-tile:
    backgroundColor: "{colors.surface-muted}"
    textColor: "{colors.on-surface}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.lg}"
    padding: "{spacing.space-07}"
  run-tile-active:
    backgroundColor: "{colors.selection}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.lg}"
    padding: "{spacing.space-07}"
  metric-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.lg}"
    padding: "{spacing.space-08}"
  progress-track:
    backgroundColor: "{colors.primary-container-muted}"
    rounded: "{rounded.md}"
    height: 26px
  progress-fill:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.data-sm}"
    rounded: "{rounded.sm}"
    height: 26px
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.button-label}"
    rounded: "{rounded.sm}"
    height: "{spacing.control-height}"
    padding: "{spacing.space-08}"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "{colors.on-primary}"
  button-secondary:
    backgroundColor: "{colors.primary-container}"
    textColor: "{colors.on-surface}"
    typography: "{typography.button-label}"
    rounded: "{rounded.sm}"
    height: "{spacing.control-height}"
    padding: "{spacing.space-08}"
  button-danger:
    backgroundColor: "{colors.danger-strong}"
    textColor: "{colors.on-primary}"
    typography: "{typography.button-label}"
    rounded: "{rounded.sm}"
    height: "{spacing.control-height}"
    padding: "{spacing.space-08}"
  input-field:
    backgroundColor: "{colors.surface-muted}"
    textColor: "{colors.on-surface}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.sm}"
    height: "{spacing.control-height}"
    padding: "{spacing.space-06}"
  mini-button:
    backgroundColor: "{colors.primary-container-muted}"
    textColor: "{colors.on-surface-subtle}"
    typography: "{typography.caption}"
    rounded: "{rounded.xs}"
    height: "{spacing.mini-control-height}"
    padding: "{spacing.space-05}"
  badge-running:
    backgroundColor: "{colors.selection}"
    textColor: "{colors.primary-hover}"
    typography: "{typography.badge-label}"
    rounded: "{rounded.full}"
    padding: "{spacing.space-04}"
  badge-success:
    backgroundColor: "{colors.success-container}"
    textColor: "{colors.on-success}"
    typography: "{typography.badge-label}"
    rounded: "{rounded.full}"
    padding: "{spacing.space-04}"
  badge-warning:
    backgroundColor: "{colors.warning-container}"
    textColor: "{colors.on-warning}"
    typography: "{typography.badge-label}"
    rounded: "{rounded.full}"
    padding: "{spacing.space-04}"
  badge-danger:
    backgroundColor: "{colors.danger-container}"
    textColor: "{colors.on-danger}"
    typography: "{typography.badge-label}"
    rounded: "{rounded.full}"
    padding: "{spacing.space-04}"
  table-header:
    backgroundColor: "{colors.surface-muted}"
    textColor: "{colors.on-surface-muted}"
    typography: "{typography.table-header}"
    padding: "{spacing.space-06}"
  log-window:
    backgroundColor: "{colors.surface-console}"
    textColor: "{colors.on-surface}"
    typography: "{typography.log-line}"
    rounded: "{rounded.lg}"
    padding: "{spacing.space-06}"
  danger-zone:
    backgroundColor: "{colors.surface-danger}"
    textColor: "{colors.on-danger}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.lg}"
    padding: "{spacing.space-10}"
---

# RL-MEC Operations Console

## Overview

This design system describes a professional monitoring surface for long-running RL-MEC benchmark and training workflows. It should feel like an operations console: compact, precise, trustworthy, and ready for repeated inspection. The visual identity is not decorative or brand-led. It is a dark telemetry environment where hierarchy comes from structured navy layers, thin blue borders, small section rails, data-dense tables, and status color.

The interface should preserve a quiet, technical temperament. It can use vivid accents, but only to clarify state, progress, evidence, warnings, or destructive actions. The main memory of the product should be a dark control room with clear machine-readable data, not a marketing dashboard.

## Colors

The palette is built from deep blue-black backgrounds and cool slate text, with electric blue as the primary structural accent.

- **Background:** Use `background`, `background-mid`, and `background-soft` as a subtle vertical field. The page should read nearly black, but never pure black except inside log consoles.
- **Surfaces:** Use `surface`, `surface-muted`, and `surface-elevated` to stack panels, run tiles, headers, and controls. Surfaces should stay close in value so the UI feels dense rather than card-heavy.
- **Primary blue:** Use `primary` for selected states, active language tabs, progress bars, focus rings, section markers, and the top border of the main header.
- **Semantic accents:** Use cyan for fixed or system-level indicators, violet for convergence or secondary algorithm context, green for completion, amber for caution and boundary notes, and red only for failures or destructive actions.
- **Text:** Use high-contrast off-white for primary copy, slate blue-gray for metadata, and mono white for numeric values. Muted text should still be readable on dark surfaces.

## Typography

Typography uses Inter for interface language and JetBrains Mono for telemetry. This pairing is central to the product's identity.

Headlines are heavy and compact. They establish the dashboard as a serious technical surface, but they remain modest in scale so the first screen can prioritize controls and data. Section titles are uppercase, small, and tracked; they pair with a slim accent rail to create recognizable scan anchors.

All values, run identifiers, timestamps, file counts, log lines, and table data should use JetBrains Mono. The mono face signals precision and makes changing metrics easy to compare at a glance. Avoid decorative type, oversized display text, or broad marketing-style hierarchy.

## Layout

The layout is a dense responsive grid with a maximum desktop content width and compact page padding. The dashboard should prioritize vertical scan flow: header controls first, run overview second, core metrics third, then progress, charts, backups, tables, logs, and danger controls.

Panels are full-width bands or grid cells, not floating marketing cards. Run tiles use a repeatable grid on desktop and stack on narrow screens. Metric cards are short, stable rectangles with a colored top border. Tables stay horizontally scrollable when needed rather than compressing technical labels until they break.

Spacing follows a mostly 2px and 4px-derived rhythm, with 10px to 24px doing most of the practical work. Keep density high, but avoid cramped rows: controls need enough height for accurate clicking, and log windows need generous inner padding so monospace text remains legible.

## Elevation & Depth

Depth is achieved through tonal separation, borders, and restrained shadow. The design should not look like glassmorphism, heavy skeuomorphism, or a stack of floating cards.

Most panels use a low, soft black shadow and a 1px blue outline. The header receives the strongest elevation because it is the command surface. Active run tiles use a left rail and faint blue glow rather than dramatic scale. Danger zones use red border light and a deeper red-black surface, but the treatment stays operational and controlled.

Charts and logs should feel embedded into the dashboard. Chart gridlines are faint, and the log console is the darkest area of the product.

## Shapes

The shape language is slightly softened but still engineered. Most structural surfaces use 10px radius. Controls and segmented buttons use 6px. Small action buttons use 4px. Badges use full pills because they are status labels rather than containers.

Avoid large rounded rectangles that make the interface feel playful. Corners should support durability and precision, not friendliness.

## Components

**Header:** The header is a command bar with a dark gradient surface, blue top border, compact title block, run selector, language segmented control, reconnect action, and destructive server stop action. It should remain sober and high contrast.

**Panels:** Panels use dark navy fill, blue outline, 20px padding, and a small blue rail before the section title. The rail is a recurring navigation cue and should appear consistently.

**Run tiles:** Run tiles are compact summaries with title, source metadata, status badges, progress, and update time. Active tiles use blue border emphasis and a left rail. Fixed or special tiles may use cyan. Warnings inside tiles use amber text on a darker amber-tinted strip.

**Metric cards:** Metric cards display one value and one supporting line. Values are mono, large, and high contrast. The colored top border distinguishes status, algorithm, progress, overall progress, and ETA without adding icons or illustration.

**Progress bars:** Progress bars use dark tracks and bright horizontal fills. The algorithm progress fill is blue; overall progress is green. Labels inside fills should be mono and compact.

**Tables:** Tables are utilitarian. Headers are uppercase and slate blue-gray. Body cells use mono text. Hover states use a very subtle blue wash. Do not add row cards or large vertical padding.

**Badges:** Badges are small uppercase pills with semantic tinting. They should communicate state quickly without dominating the surrounding data.

**Charts:** Charts should use muted gridlines, light legends, and restrained color. The dashboard is about monitoring status, not creating publication figures.

**Logs:** Logs use the darkest console surface, monospace type, and level colors. Log interaction should be subtle: hover rows can brighten slightly, but the console should remain stable during scanning.

**Danger zone:** Destructive operations live in a red-black section with red borders and red buttons. It must look materially different from normal panels while still belonging to the same dark console family.

## Do's and Don'ts

- Do keep the interface dark, dense, and operational.
- Do use blue for structure, selection, focus, and normal progress.
- Do reserve red for destructive or failed states.
- Do keep data, timestamps, paths, and log content in monospace.
- Do preserve the slim section rail before panel titles.
- Do use tables and compact grids for repeated technical data.
- Don't introduce large hero areas, marketing copy, decorative illustrations, or oversized cards.
- Don't replace semantic status color with arbitrary accent colors.
- Don't lighten the background into a generic SaaS dark theme; the console should stay close to blue-black.
- Don't overuse shadows. Borders and tonal layers should carry most hierarchy.
- Don't make mobile views decorative. Mobile should stack the same operational controls and panels with stable full-width rows.
