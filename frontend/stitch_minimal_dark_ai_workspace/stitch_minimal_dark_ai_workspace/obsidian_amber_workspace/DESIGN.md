---
name: Obsidian Amber Workspace
colors:
  surface: '#131315'
  surface-dim: '#131315'
  surface-bright: '#39393b'
  surface-container-lowest: '#0e0e10'
  surface-container-low: '#1c1b1d'
  surface-container: '#201f22'
  surface-container-high: '#2a2a2c'
  surface-container-highest: '#353437'
  on-surface: '#e5e1e4'
  on-surface-variant: '#dbc2b0'
  inverse-surface: '#e5e1e4'
  inverse-on-surface: '#313032'
  outline: '#a38c7c'
  outline-variant: '#554336'
  surface-tint: '#ffb77d'
  primary: '#ffb77d'
  on-primary: '#4d2600'
  primary-container: '#d97707'
  on-primary-container: '#432100'
  inverse-primary: '#904d00'
  secondary: '#ffb95f'
  on-secondary: '#472a00'
  secondary-container: '#ee9800'
  on-secondary-container: '#5b3800'
  tertiary: '#96ccff'
  on-tertiary: '#003353'
  tertiary-container: '#0297e8'
  on-tertiary-container: '#002c48'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdcc3'
  primary-fixed-dim: '#ffb77d'
  on-primary-fixed: '#2f1500'
  on-primary-fixed-variant: '#6e3900'
  secondary-fixed: '#ffddb8'
  secondary-fixed-dim: '#ffb95f'
  on-secondary-fixed: '#2a1700'
  on-secondary-fixed-variant: '#653e00'
  tertiary-fixed: '#cee5ff'
  tertiary-fixed-dim: '#96ccff'
  on-tertiary-fixed: '#001d32'
  on-tertiary-fixed-variant: '#004a75'
  background: '#131315'
  on-background: '#e5e1e4'
  surface-variant: '#353437'
typography:
  display-editorial:
    fontFamily: Newsreader
    fontSize: 40px
    fontWeight: '400'
    lineHeight: 48px
    letterSpacing: -0.02em
  display-editorial-mobile:
    fontFamily: Newsreader
    fontSize: 28px
    fontWeight: '400'
    lineHeight: 36px
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Geist
    fontSize: 24px
    fontWeight: '500'
    lineHeight: 32px
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Geist
    fontSize: 18px
    fontWeight: '500'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Geist
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
    letterSpacing: 0em
  body-sm:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: 0em
  label-code:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: -0.005em
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.06em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  space-2xs: 0.125rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-base: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
  space-2xl: 3rem
  space-3xl: 4rem
---

## Brand & Style

This design system embodies austere, focused minimalism engineered for deep creative and intellectual labor. Built for researchers, engineers, and technical thinkers, it strips away the chaotic visual noise of modern generative interfaces in favor of calm, architectural discipline.

The emotional resonance is focused, sovereign, and contemplative—evoking the quiet precision of an empty Unix console meeting the literary weight of an editorial folio. There are strictly no chromatic aberration gradients, no frosted glass layers, no neon bloom, and no decorative skeuomorphism. Depth is achieved purely through precise tone stepped surfaces, surgical 1px borders, and disciplined typographic rhythm.

## Colors

The palette relies on a pitch-dark, achromatic foundation illuminated by a single controlled ember of warm amber. 

- **Surfaces:**
  - Base canvas: `#09090b` (Deep Void)
  - Secondary containers and sidebars: `#121214` (Layer 1 Panel)
  - Active surfaces, code blocks, and elevated cards: `#18181b` (Layer 2 Surface)
  - Hover states and active selections: `#27272a` (Interactive Overlay)

- **Boundaries:**
  - Structural separators and containers: 1px solid `#27272a`
  - Subtle dividers and soft splits: 1px solid `#1f1f23`
  - Active/Focused boundaries: 1px solid `#d97706`

- **Text & Foreground Hierarchy:**
  - Primary text / Headings: `#f4f4f5` (High-contrast stark zinc)
  - Secondary body / Descriptions: `#a1a1aa` (Neutral zinc)
  - Muted captions / Placeholders / Metadata: `#71717a` (De-emphasized zinc)

- **Accent (Restrained Amber):**
  - Primary action / Caret / Terminal active nodes: `#d97706`
  - Hover / Interactive highlight: `#f59e0b`
  - Muted badge fill: `rgba(217, 119, 6, 0.08)` with border `rgba(217, 119, 6, 0.25)`

## Typography

The typographic hierarchy creates tension between classical thought and raw computational execution:

- **Editorial Display (`Newsreader`):** Reserved solely for welcoming statements, thesis prompts, model persona titles, and empty-state contemplative thoughts. Always set in natural weight (`400`) or italic variants to preserve human literary nuance.
- **Interface & System (`Geist`):** Delivers clean, objective, geometric clarity for operational layouts, dynamic conversation outputs, and interactive controls.
- **Computational Utility (`JetBrains Mono`):** Governs data feeds, token consumption counters, parameter badges, code blocks, and keyboard shortcuts. Caps variants must always feature uppercase transformation with positive tracking.

## Layout & Spacing

The workspace uses a dense, architectural grid system designed for uninterrupted workflow:

- **Grid Architecture:** 
  - Dual-panel or tri-panel layout using fixed or collapsible utility rails (sidebar width: 260px; contextual drawer: 320px) pinned to a fluid primary central execution canvas.
  - Max text column width for conversational reading streams strictly throttled to `46rem` (736px) to maximize cognitive retention and reading ergonomics.
- **Spacing Rhythm:**
  - Baseline 4px / 8px incremental scale.
  - Component internals use compressed padding (`space-xs` to `space-md`) to mirror IDE density.
  - Canvas margins use expansive breathing room (`space-2xl` to `space-3xl`) to center focus during active generation.
- **Breakpoints:**
  - Mobile (`< 768px`): Sidebars collapse into an off-screen drawer; single-column fluid layout with `space-base` margins.
  - Desktop (`≥ 768px`): Full multi-panel docked workspace with hairline persistent panel borders.

## Elevation & Depth

This design system rejects heavy blur filters, diffuse soft glows, and drop shadows. Visual depth is established through tonal stepping and razor-sharp boundaries:

- **Layer 0 (Canvas):** `#09090b` acts as the infinite baseline.
- **Layer 1 (Panels & Shells):** `#121214` framed by 1px borders of `#27272a`.
- **Layer 2 (Cards, Prompts, Floats):** `#18181b` with 1px border `#27272a`.
- **Layer 3 (Modals & Command Palettes):** `#18181b` with a deliberate 1px border of `#3f3f46` and an opaque, zero-blur hard offset shadow: `0 8px 0px 0px rgba(0, 0, 0, 0.6)`.
- **Focus & Selection:** Never signaled by diffused rings; signaled strictly by crisp 1px borders shifting to `#d97706`.

## Shapes

The geometric silhouette is sharp and tactical, using subtle corner softening without becoming friendly or organic:

- Base elements (buttons, inputs, menu rows, pills) use `0.25rem` (4px) corner radii.
- Larger structural surfaces (chat prompts, floating toolbars, dialogs) use `0.375rem` (6px) up to a hard maximum of `0.5rem` (8px).
- Status indicators, execution state dots, and token pills use pure circles or `0.125rem` (2px) micro-radii to maintain high-density data legibility.

## Components

- **Buttons:**
  - *Primary:* Background `#d97706`, text `#09090b` (bold, readable contrast), border transparent. Hover shifts to `#f59e0b`.
  - *Secondary / Ghost:* Background transparent, border 1px solid `#27272a`, text `#f4f4f5`. Hover triggers background `#18181b` and border `#3f3f46`.
  - *Subtle / Icon Only:* Text `#a1a1aa`, background transparent. Hover triggers text `#f4f4f5` and background `#121214`.

- **Input Prompt / Command Bar:**
  - The signature element of the tool. Positioned in the central focus plane with background `#121214`, framed by 1px solid `#27272a`.
  - Focused state transitions border directly to `#d97706`.
  - Text entry utilizes `Geist` for inputs and `JetBrains Mono` for modifier tags and shortcuts (`⌘K`).

- **Chips & Parameter Tags:**
  - Compact height (22px), font `label-caps` in `JetBrains Mono`.
  - Surface `#18181b`, border 1px solid `#27272a`, text `#a1a1aa`.
  - Active/Enabled state: Border `rgba(217, 119, 6, 0.4)`, background `rgba(217, 119, 6, 0.08)`, text `#f59e0b`.

- **Lists & Tree Navigation:**
  - Low-profile padding (`0.375rem` vertical), flat layout without dividers between individual items.
  - Hover highlighted with background `#18181b`. Selected item highlighted with a 2px vertical indicator in `#d97706` pinned to the left edge.

- **Checkboxes & Toggles:**
  - Checkboxes: 14px squares, 1px border `#3f3f46`, background `#09090b`. Checked state fills with `#d97706` and renders a sharp dark checkmark.
  - Toggles: 28px width, 16px height track in `#27272a`, 12px circular nub in `#a1a1aa`. Active state turns track to `rgba(217, 119, 6, 0.3)` and nub to `#d97706`.

- **Cards & Execution Nodes:**
  - Background `#121214`, border 1px solid `#27272a`, padding `space-lg`. Zero ambient shadow.
  - Header displays metadata formatted with `label-caps` in `#71717a`.

- **Terminal Stream & Code Blocks:**
  - Background `#09090b`, embedded within `#121214` surfaces with a 1px border `#1f1f23`.
  - Syntax highlighted using a restrained warm spectrum: monochrome whites and grays, with amber reserved for keywords, functions, and active execution highlights.