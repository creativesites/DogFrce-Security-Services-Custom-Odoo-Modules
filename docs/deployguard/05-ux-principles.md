# 05 — UX Principles & Design System Application

> Status: Draft · Owner: UX
>
> **Normative sources:** [`docs/DEPLOYGUARD_DESIGN_SYSTEM.md`](../DEPLOYGUARD_DESIGN_SYSTEM.md) (tokens, hard rules, component patterns) and the shipped `custom_addons/security_shell/` (the canonical shell). This document explains how the Platform's desktop and web apps apply them. If this document and the design system disagree, **the design system wins**; open a design decision rather than diverging.

---

## 1. UX principles

| # | Principle | In practice |
|---|---|---|
| 1 | **One question per employee screen** | The employee Home answers "What do I need to do now?" and nothing else. Analytics never appear on employee screens. |
| 2 | **Exceptions, not dashboards, for management** | The manager starts in the Inbox. Charts support decisions; they are not the starting point. |
| 3 | **Every item has one obvious next action** | Cards carry a single primary action. Secondary actions sit in an overflow menu. |
| 4 | **Progressive disclosure** | Summary → reason → evidence. Detail is one click away, never forced up front. |
| 5 | **Help is always one action away** | "Get help" / "Report a problem" in the profile area and on every error state, pre-filled with context. |
| 6 | **Explain every number** | Any score, count or status that could surprise someone links to "why" (factors, events, rule). |
| 7 | **Supportive language, never punitive** | "You haven't posted attendance for Site 12 — need help?" not "Non-compliance detected." Adoption is framed as support ([09](09-adoption-engine.md) §8). |
| 8 | **Calm hierarchy** | Neutral surfaces; colour reserved for status. A screen with everything highlighted has nothing highlighted. |
| 9 | **Density matches role** | Employee: spacious, 1 column, large touch targets. Management: denser tables, split views, keyboard-driven triage. |
| 10 | **Honest system state** | Offline, syncing, stale and failed states are always visible. Nothing pretends to have succeeded ([20](20-offline-strategy.md)). |
| 11 | **Keyboard first for power users** | ⌘K/Ctrl+K palette, list navigation with `j`/`k`, `e` to resolve, `?` for shortcuts. |
| 12 | **One product across surfaces** | Moving between the Odoo shell and the desktop app should feel like changing rooms, not buildings. |

---

## 2. Token port (normative)

The Platform ships the design-system tokens **verbatim** in `packages/ui/src/tokens/`:

| File | Contents | Rule |
|---|---|---|
| `ds.css` | Every `--ds-*` token from `security_base/static/src/css/design_system.css` | Never edited in the Platform repo. Updated only by syncing from the Odoo repo. |
| `dgs.css` | Every `--dgs-*` token from `security_shell/static/src/css/shell_tokens.css`, plus the `.dgs-mono` utility | Same. Never redefines `--ds-*`. |
| `platform.css` | Platform-only aliases that **reference** existing tokens (e.g. `--dgp-focus-ring: var(--ds-accent-mid)`) | May not introduce new hex values without a recorded design decision. |

**Sync:** a CI check in the Platform repo compares `ds.css`/`dgs.css` against pinned copies from the Odoo repo, and fails on drift ([DG-ADR-017](adr/DG-ADR-017-design-system-and-shell-parity.md)).

**Tailwind mapping** (`packages/ui/tailwind.preset.ts`): Tailwind is configured with **only** token-backed values. Colours, radii, shadows and font families map to `var(--…)`. The default palette and arbitrary values (`bg-[#…]`, `rounded-[7px]`) are disabled by lint.

| Tailwind key | Maps to |
|---|---|
| `bg`, `surface`, `border`, `text`, `text-2`, `muted`, `subtle` | `--ds-bg`, `--ds-surface`, `--ds-border`, `--ds-text`, `--ds-text-2`, `--ds-text-muted`, `--ds-text-subtle` |
| `accent`, `accent-hover`, `accent-light`, `accent-mid` | `--ds-accent*` |
| `success`/`warning`/`danger`/`info` (+ `-bg`) | `--ds-success*` … `--ds-info*` |
| `rail`, `rail-icon`, `desk`, `panel`, `canvas` | `--dgs-rail`, `--dgs-rail-icon`, `--dgs-desk`, `--dgs-panel`, `--dgs-canvas` |
| `rounded-shell/card/tile/control/pill` | `--dgs-r-shell/card/tile/control/pill` |
| `rounded-sm/DEFAULT/md/lg` | `--ds-radius-sm/radius/radius-md/radius-lg` |
| `shadow-lift`, `shadow-lift-hover` | `--dgs-lift`, `--dgs-lift-hover` |
| `font-sans`, `font-mono` | `--dgs-font`, `--dgs-mono` |

**Fonts:** `--dgs-font` resolves from `--dg-font-family`, set at runtime from the tenant's theme (mirroring `security_theme`'s `theme_loader.js`). Because the desktop must work offline and Google Fonts are an external dependency, the Platform **bundles** the theme font set locally (IBM Plex Mono plus the tenant-selectable families offered by `security_theme`) as WOFF2 files. It never hardcodes a family in a component.

---

## 3. Hard rules applied to the Platform

The seven hard rules in design system §2 apply unchanged. Platform-specific interpretation:

| Design-system rule | Platform enforcement |
|---|---|
| 1. All numerals mono + tabular | `<Num>` component and `.dgs-mono` class; lint warns on numeric JSX text outside `<Num>` in metric components. Timestamps, counts, IDs, scores, percentages all use it. |
| 2. The rail is the only dark surface | `rail` colour tokens are only importable inside `packages/ui/shell/Rail*`; lint rule forbids `bg-rail` elsewhere. No dark mode is planned. |
| 3. Max two gradients (coverage bar, metric progress) | `--dgs-ramp` only through `<CoverageBar>` and `<MetricBar>`; `linear-gradient` banned in stylelint outside those files. |
| 4. Status colours only from `--ds-success/warning/danger/info` | `<StatusPill tone=…>` is the only way to colour status; raw hex banned by stylelint (`color-no-hex`) outside token files. |
| 5. No full-viewport overlays outside shell chrome | Shell-level overlays (command palette, profile card, notification centre) use a portal to the shell root. Screen-level modals and sheets render **inside the canvas** (`position: absolute` relative to the canvas container) so rail and nav stay usable. |
| 6. No `!important` | stylelint `declaration-no-important` = error, no exceptions in the Platform. |
| 7. Inline stroke SVG icons (~1.9 px) | Icon set: Lucide React (stroke-based) wrapped in `<Icon>` that fixes `strokeWidth={1.9}` and sizes; Font Awesome is not used in the Platform. |

---

## 4. Shell parity with `security_shell`

| `security_shell` element | Platform equivalent (`packages/ui/shell`) | Parity notes |
|---|---|---|
| `shell_frame.js` (mounts rail, nav, palette, launcher) | `<AppShell>` | Same three-region layout; `--dgs-desk` gap colour; canvas radius `--dgs-r-shell`. |
| `shell_rail.js` + `shell_rail_flyout.js` | `<Rail>`, `<RailFlyout>` | Hover popovers with the same delay behaviour; active icon focus; collapsed by default on narrow widths. |
| `shell_nav_panel.js` + `nav_catalog.js` | `<NavPanel>` + typed `navCatalog` | Leaf flags `soon`, `roles`, `countKey`; `SOON` and `NOT INSTALLED` chips identical and non-clickable. |
| `shell_command_palette.js` | `<CommandPalette>` | ⌘K / Ctrl+K, Esc closes, recent items. |
| `home_dashboard.js` (`get_home_payload`: attention, coverage, metrics) | Home (employee) / Today (manager) | Same card, tile and coverage-bar patterns; "attention" becomes the Inbox preview. |
| `shell_profile_card.js` | `<ProfileCard>` | Identity, roles/scopes, device, preferences, sign out. |
| `shell_loading_bar.js` | `<LoadingBar>` | Driven by the API client's in-flight request counter. |
| `shell_service.js` (state persisted under `dgs.nav.v1`) | `useShellStore` (Zustand) | Persisted per user and device; key namespaced `dgp.nav.v1`. |
| Breakpoints 1280 px / 900 px (nav panel → overlay, rail → bottom bar) | Same breakpoints | Web only; desktop minimum window width is 1024 px. |

A **visual parity checklist** (screenshot comparison of rail, nav panel, cards, tiles, pills against the Odoo shell) is part of the P2 acceptance criteria in [BUILD-ORDER](BUILD-ORDER.md).

---

## 5. Component patterns

| Component | Spec (from design system §3) | Used for |
|---|---|---|
| `Card` | radius `--dgs-r-card`, `--dgs-panel`, `--dgs-lift` → `--dgs-lift-hover` | Home items, inbox groups, summaries |
| `Tile` | radius `--dgs-r-tile`, tinted 42 px (quick action) / 32 px (module) icon square, title 13–14 px/600, subline 12 px `--ds-text-subtle` | Quick actions, section entry points |
| `CountPill` | mono 10.5 px, `--ds-slate` bg, `--ds-text-muted`, radius 9 px | Nav counts, list counts |
| `Chip` (`SOON`, `NOT INSTALLED`) | mono 9 px, +0.5 px tracking, `--ds-text-subtle` on `--ds-slate`, radius 8 px, 60 % label opacity | Unavailable features |
| `SegmentedControl` | dark pill group on `--dgs-rail` (active white-on-ink) or light group (active `--dgs-rail`) | Period selectors, scope toggles |
| `StatusPill` | tone from `--ds-*` status pairs only | Task/exception/training status |
| `SeverityBadge` | Critical = danger, Attention = warning, Watch = info | Inbox |
| `CoverageBar`, `MetricBar` | `--dgs-ramp` | Coverage, adoption score, completion |
| `Num` | `--dgs-mono`, tabular-nums | Every numeral |
| `EvidenceList` | Linked rows with source icon (Odoo / Platform / Mobile), timestamp in `Num` | Exceptions, adoption explanations, AI citations |
| `ConfidenceIndicator` | Text label + 3-step meter (Low / Medium / High), never colour alone | AI insights (V1) |
| `DataTable` | Base-system list styling equivalents: `--ds-border`, 36 px dense rows (management), 44 px comfortable (employee) | Management lists |

---

## 6. Required states

Every screen and data component must design all applicable states **before** implementation is considered done.

| State | Pattern | Copy guidance |
|---|---|---|
| Loading | Skeletons shaped like the final content; global `LoadingBar`; never a full-screen spinner after first load | — |
| Empty (nothing to do) | Positive confirmation + next useful action | "You're all caught up for today." |
| Empty (not set up) | Explain what will appear and who configures it | "No checklists are assigned to your sites yet. Your operations manager can set them up." |
| Insufficient data | Neutral panel; no score or chart shown | "Not enough activity yet to calculate — check back after 5 working days." |
| Offline | Top-of-canvas banner with last-sync time; cached content marked; actions show "Will send when online" | "You're offline. Showing data from 08:42." |
| Sync pending / failed | Per-item badge (`Pending`, `Failed — retry`) | Never claim success until acknowledged by the server. |
| Error (recoverable) | Inline, next to the failed action, with Retry and Get help (pre-filled) + reference code | "Couldn't submit the checklist. Try again, or get help (ref DG-7F3K)." |
| Error (blocking) | Canvas-level message; rail and nav remain usable | Same, plus alternative path (e.g. open in Odoo). |
| Permission denied | Explain which role or scope grants access and who to ask | "Only supervisors of Site 12 can verify this." |
| Success | Brief inline confirmation; toast only for background completions | "Checklist submitted for verification." |
| Not installed / Soon | `Chip` treatment, non-clickable | — |

---

## 7. Low-fidelity wireframes

### 7.1 Employee Home (Site Supervisor)

```
┌ Good morning, Supervisor ──────────────────────────── Tue 16 Sep ┐
│ Current shift  Day · 06:00–18:00 · North sector (4 sites)       │
├──────────────────────────────────────────────────────────────────┤
│ OVERDUE (1)                                                      │
│ ▢ Post attendance — Site 12, yesterday night shift   [Open in Odoo]
├──────────────────────────────────────────────────────────────────┤
│ DUE TODAY (3)                                                    │
│ ▢ Site visit checklist — Site 4          due 12:00   [Start]     │
│ ▢ Review incident #214 (guard submitted) due 17:00   [Review]    │
│ ▢ Verify: handover checklist — Site 9                [Verify]    │
├──────────────────────────────────────────────────────────────────┤
│ TRAINING                                                         │
│ ▢ Posting attendance correctly · 12 min · due Fri    [Continue]  │
├──────────────────────────────────────────────────────────────────┤
│ Need help with something?                     [Report a problem] │
└──────────────────────────────────────────────────────────────────┘
```

### 7.2 Manager Inbox

```
┌ Inbox ─────────────────────────────── [All sites ▾] [This week ▾] ┐
│ CRITICAL (1)                                                     │
│ ● Site 12 has no night supervisor assigned tonight               │
│   Rule: roster.supervisor_missing · from Odoo roster · 14:02     │
│   Recommended: assign from available supervisors  [Open in Odoo] │
├──────────────────────────────────────────────────────────────────┤
│ ATTENTION (3)                                                    │
│ ● 4 incident reports awaiting review > 24 h        [Review list] │
│ ● 3 employees overdue on mandatory training        [Remind]      │
│ ● Supervisor North: attendance posted late 3 of 5 days [Why?]    │
├──────────────────────────────────────────────────────────────────┤
│ WATCH (1)                                                        │
│ ● Workflow coverage down 8 % this week (72 % → 64 %) [Explain]   │
└──────────────────────────────────────────────────────────────────┘
  j/k move · e resolve · a acknowledge · Enter open · ? shortcuts
```

### 7.3 Adoption explanation

```
┌ Adoption · Site Supervisor (North) ─────── 64 ▼8 vs last week ──┐
│ ▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░  (metric ramp)       Confidence: High (38 items)
├──────────────────────────────────────────────────────────────────┤
│ What changed                                                     │
│ Workflow coverage   18/25 expected done in system  ▼ -12 pts     │
│   Missing: attendance posting Site 12 (Mon, Tue, Wed)  [Evidence] │
│ Timeliness          on time 14/18                   ▲ +2 pts     │
│ Training currency   1 mandatory course overdue      ▼ -3 pts     │
│ Friction signals    2 "Something isn't working" reports (Mon)    │
├──────────────────────────────────────────────────────────────────┤
│ Possible cause: reported permission error on Site 12 batch (Mon) │
│ Suggested: resolve support request #88 before any follow-up      │
│                               [Open request]  [Start a check-in] │
└──────────────────────────────────────────────────────────────────┘
```

### 7.4 Owner overview (web)

```
┌ DogForce · Operations health ─────────────────── Week 38 ─────────┐
│ [Operations ●] [Staffing ●] [Compliance ●] [Training ●] [Adoption ●]
│  coverage 97%   gaps 2       expiring 6     overdue 5    64% ▼8   │
├──────────────────────────────────────────────────────────────────┤
│ Needs attention                                                  │
│ 1 critical · 5 attention — oldest open 3 days          [View]    │
├──────────────────────────────────────────────────────────────────┤
│ This week's brief (digest)                                       │
│ What happened · What changed · Risks · Positive developments     │
│ Each statement links to its evidence                   [Read]    │
└──────────────────────────────────────────────────────────────────┘
```

(Status dots use `StatusPill` tones. Tiles use `Num` for all values.)

---

## 8. Writing guidelines

- Plain English at roughly an 8th-grade reading level for employee screens; operational terms as DogForce uses them (post, site, occurrence book, handover).
- Name the thing and the next step: "Post attendance for Site 12" beats "Attendance compliance task".
- Adoption and exceptions: describe the observable fact, then offer help. Never infer intent ("ignored", "refused").
- AI-generated text is always labelled ("Draft — generated, needs review" / "Summary generated from 14 records") with a link to its evidence.
- Dates relative when near ("today 14:02", "yesterday"), absolute otherwise; always tenant timezone (Africa/Windhoek for DogForce).

## 9. Accessibility checklist (per screen)

WCAG 2.2 AA; design system §6 retrofit checks 6 and 8 apply:

- Contrast ≥ 4.5:1 for text, ≥ 3:1 for UI components and focus rings.
- Every interactive element reachable and operable by keyboard, with visible focus.
- `aria-label` / `title` on icon-only controls; status never conveyed by colour alone.
- Esc closes any overlay; focus returns to the trigger.
- Layout reads correctly at 1280 px and 900 px (web), and at 1024 px minimum desktop window width.
- Respects OS reduced-motion and text scaling up to 200 %.
