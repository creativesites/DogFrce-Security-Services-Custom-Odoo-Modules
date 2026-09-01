# DeployGuard Design System

Design guidelines for progressively restyling DogForce/DeployGuard to match the
shell + Home dashboard shipped in `security_shell` (see
`custom_addons/security_shell/` and the original build spec,
`HANDOFF-deployguard-shell.md`). This is the reference every future styling
change should follow — new screens and retrofits alike.

There are two layers. Never confuse them, never let one redefine the other's tokens.

| Layer | File | Scope |
|---|---|---|
| **Base design system** ("Clean Corporate Light") | `security_base/static/src/css/design_system.css` | Every stock Odoo view: lists, forms, kanban, buttons, badges, dropdowns, chatter. Loads first in `web.assets_backend`. |
| **Shell layer** | `security_shell/static/src/css/shell_tokens.css` | The rail, nav panel, canvas chrome, Home dashboard, and — going forward — every custom OWL dashboard/mega-menu retrofitted to match. Layers on top of the base system, never redefines `--ds-*`. |

A module being restyled always uses **both**: `--ds-*` for anything that already
looks right in stock views (borders, status colors, buttons, badges), and
`--dgs-*` only for shell-specific chrome values (radii scale, rail ink, the
metric ramp).

---

## 1. Tokens

### 1.1 Base tokens (`--ds-*`) — already applied everywhere via `design_system.css`

```
--ds-bg #F8FAFC   --ds-surface #FFFFFF   --ds-border #E2E8F0   --ds-border-light #EEF1F5
--ds-text #0D1117  --ds-text-2 #374151   --ds-text-muted #475569  --ds-text-subtle #64748B
--ds-accent #1B3A6B  --ds-accent-hover #142F58  --ds-accent-light #EBF1FB  --ds-accent-mid #C7D9F4
--ds-success #0D7A4E / bg #E6F4EE     --ds-warning #92400E / bg #FEF3C7
--ds-danger  #991B1B / bg #FEE2E2     --ds-info    #1D5FA4 / bg #E0EEFA
--ds-slate #F1F4F8  --ds-slate-hover #E8EDF4
--ds-radius-sm 4  --ds-radius 6  --ds-radius-md 8  --ds-radius-lg 12
--ds-shadow-sm 0 1px 3px rgba(15,23,42,.06)  --ds-shadow 0 2px 8px rgba(15,23,42,.08)  --ds-shadow-md 0 4px 16px rgba(15,23,42,.10)
--ds-font  -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", sans-serif
--ds-mono  "SF Mono", "Fira Code", "Consolas", monospace
```

Never invent a new hex for something these already cover — status colors,
borders, surfaces, and buttons are already solved. If a screen has its own
ad hoc `#hexcode`, that's the first thing to delete when retrofitting it.

### 1.2 Shell tokens (`--dgs-*`) — the newer, softer layer

```
--dgs-rail #101724            /* the ONLY dark surface allowed anywhere */
--dgs-rail-hover rgba(255,255,255,.08)
--dgs-rail-active #FFFFFF
--dgs-rail-icon #8494AC
--dgs-rail-divider rgba(255,255,255,.10)

--dgs-desk #E7EAF0            /* gap color behind rail/panel/canvas */
--dgs-panel #FFFFFF           /* nav panel + card surfaces */
--dgs-canvas #F5F6F9          /* page background inside the shell */

--dgs-r-shell 22px            /* rail, nav panel, canvas corners */
--dgs-r-card 20px             /* dashboard cards */
--dgs-r-tile 16px             /* quick-action / module tiles */
--dgs-r-control 13px          /* inputs, the company switcher */
--dgs-r-pill 22px             /* pills, search field */

--dgs-lift 0 1px 2px rgba(16,23,36,.05)
--dgs-lift-hover 0 10px 26px rgba(16,23,36,.10)

--dgs-font  var(--dg-font-family, -apple-system, "Segoe UI", sans-serif)
--dgs-mono  "IBM Plex Mono", "SF Mono", ui-monospace, monospace

--dgs-ramp linear-gradient(90deg,#F87171 0%,#F5A20B 38%,#84CC16 72%,#22C55E 100%)
```

`--dgs-font` resolves to `--dg-font-family`, which `security_theme`'s
`theme_loader.js` sets from the tenant's chosen font at runtime. **Never
hardcode a font-family in a retrofitted screen** — always reference
`--dgs-font` (prose) or `--dgs-mono` (numerals), so white-label font changes
keep working everywhere, including screens built before the shell existed.

---

## 2. Hard rules

These are non-negotiable, carried over verbatim from the shell build spec —
apply them to every retrofit, not just new screens.

1. **All numerals use `--dgs-mono` with `font-variant-numeric: tabular-nums`.**
   KPI values, counts, coverage percentages, timestamps, IDs. Prose uses
   `--dgs-font`. Mixing the two per-screen is the single most common
   inconsistency in the current codebase — most legacy dashboards render
   numbers in the same font as prose.
2. **The rail is the only dark surface in the product.** Everything else —
   cards, panels, tiles — is light. Don't introduce a second dark theme or
   dark-mode-style card anywhere else.
3. **Max two gradients, ever: the coverage bar and metric progress bars, both
   `--dgs-ramp`.** No decorative gradients on buttons, headers, icons, or
   cards. Several legacy screens (app launcher tiles, mega-menu icon boxes)
   currently use decorative `linear-gradient` icon backgrounds — leave them
   for now (see the App Switcher exception in §5), but do not add more.
4. **Status colors only come from `--ds-success/-warning/-danger/-info` (+ their
   `-bg` pairs).** Never a new hex for "this row is bad/good."
5. **No `position: fixed; inset: 0` full-viewport overlays outside the shell's
   own chrome** (command palette, full-menu, company switcher scrim, app
   launcher). A screen-level modal or "mega menu" must be
   `position: absolute` relative to `.o_action_manager` (already a positioned
   ancestor — see `shell_layout.css`), not the viewport. This was a real bug:
   five existing "mega menu" screens (`rmm-overlay`, shared by
   `security_shift_planner`, `security_fleet`, `security_equipment`,
   `security_operations`, `security_base`) used to cover the *entire*
   viewport at `z-index: 10050`, hiding the shell's rail and nav panel
   whenever opened. Fixed in `rostering_mega_menu.css` by switching
   `.rmm-overlay` to `position: absolute` at `z-index: 500` — treat that as
   the canonical example when auditing any other screen for the same
   mistake. In-page confirm/edit dialogs (`*-modal-backdrop` classes) are
   fine as-is; those are transient and expected to darken the current
   screen, same as a native Odoo wizard dialog.
6. **No `!important` outside the one navbar-suppression rule in
   `shell_layout.css`.** If a retrofit needs to beat an existing rule's
   specificity, fix the selector, don't reach for `!important`.
7. **Rail/nav-panel icons are inline SVG (stroke, no fill, ~1.9px stroke
   weight)** — see `shell_rail.xml` for the pattern. This is a shell-chrome
   rule, not a repo-wide one: existing dashboards use Font Awesome
   pervasively and ripping that out isn't in scope. When a screen is
   *rebuilt* (not just retrofitted with tokens), prefer inline SVG matching
   the shell's stroke weight so it doesn't look visually heavier than its
   neighbors.

---

## 3. Component patterns

### 3.1 Cards & tiles
- Dashboard card: `border-radius: var(--dgs-r-card)` (20px), `background:
  var(--dgs-panel)`, `box-shadow: var(--dgs-lift)`, hover →
  `var(--dgs-lift-hover)`.
- Quick-action / module tile: `border-radius: var(--dgs-r-tile)` (16px), same
  shadow pair, a small tinted icon square (42px quick-action / 32px module),
  title 13–14px/600, subline 12px `--ds-text-subtle`.
- Page/section radius (rail, nav panel, canvas, big containers):
  `var(--dgs-r-shell)` (22px).

### 3.2 Pills & chips
- Count pill: mono, 10.5px, `--ds-slate` background, `--ds-text-muted`,
  radius 9px.
- `SOON` chip: mono, 9px, `+0.5px` letter-spacing, `--ds-text-subtle` on
  `--ds-slate`, radius 8px, row not clickable, label at 60% opacity.
- `NOT INSTALLED` chip: same visual treatment as `SOON` — a leaf whose
  action doesn't resolve on this database must never look different from
  "not built yet." Both mean "don't click me," not "something is broken."
- Status pill (role toggle, period selector): dark pill group on
  `--dgs-rail`, active segment white-on-ink. Light pill group: white,
  `--ds-border`, active = `--dgs-rail` (dark) background.

### 3.3 Modals & overlays
Two kinds, styled differently:
- **Shell-level overlays** (command palette, full menu, company switcher):
  `position: fixed`, cover the viewport, `z-index` ≥ 1049. These are the
  shell's own chrome — the only place a full-viewport overlay is correct.
- **Screen-level modals** (a mega menu, a confirm dialog, an edit sheet):
  `position: absolute` relative to `.o_action_manager`, `z-index` in the
  low hundreds (500 is the convention set by the mega-menu fix). The rail
  and nav panel must stay visible and interactive around them.

### 3.4 Numerals
Wrap every KPI value, count, percentage, and timestamp in a class that sets
`font-family: var(--dgs-mono); font-variant-numeric: tabular-nums;` — see
`.dgs-mono` in `shell_tokens.css`. Copy that utility class into any module's
own CSS file when retrofitting rather than inlining the rule everywhere.

### 3.5 Lists, forms, kanban
Already correct via `design_system.css` — do not touch these per-module.
The base design system's job is exactly this; a retrofit should never
reintroduce local list/form CSS.

---

## 4. Layout

- Every backend screen renders inside `.o_action_manager`, which is the
  shell's canvas — flex `1 1 auto`, `background: var(--dgs-canvas)`,
  `border-radius: var(--dgs-r-shell)`, its own `overflow: auto`. A screen's
  root element should never re-declare page-level background, height, or
  positioning; let the canvas own that.
- `.o_control_panel` (breadcrumbs, view switcher, search) is untouched by
  the shell and by any retrofit — it's owned by stock Odoo + the base
  design system.
- A screen that needs a full-bleed hero/header (like Home) should pad
  itself, not fight the canvas's own padding assumptions — see
  `.dgs-home { padding: 24px 28px 40px; max-width: 1360px; margin: 0 auto; }`
  as the template for a retrofitted dashboard's outer wrapper.

---

## 5. Known, deliberate exceptions

- **App switcher tiles** (`security_theme/static/src/css/app_launcher.css`)
  keep their decorative per-category gradients (`bg-gradient-blue`,
  `-purple`, etc.) and dark glassy backdrop. This predates the "max two
  gradients" rule and is being left alone deliberately — it's a distinct,
  self-contained "everything" overlay, not part of the flat canvas system.
  Don't extend this pattern to new screens; don't feel obligated to rip it
  out either.
- **Product tour spotlight** (`security_tour`) is intentionally a
  full-viewport overlay — it's a guided-tour focus effect, not a screen.

---

## 6. Retrofit checklist

Run this against any existing dashboard/mega-menu/wizard when its turn comes
in the rollout plan (`docs/DESIGN_SYSTEM_ROLLOUT_PLAN.md`):

1. Replace every hardcoded hex with the matching `--ds-*` token; anything
   that doesn't map to an existing token (a genuinely new brand color) gets
   flagged for a design decision, not invented on the spot.
2. Add `.dgs-mono`-equivalent styling to every number on screen.
3. Swap the page/card/tile radii onto the `--dgs-r-*` scale.
4. If the screen has its own full-page overlay or "mega menu" pattern,
   apply the §2.5 fix (`position: absolute` on `.o_action_manager`, not
   `position: fixed` on the viewport).
5. Remove decorative gradients that aren't the coverage/metric ramp.
6. Check the screen still reads correctly at 1280px and 900px — the shell's
   own breakpoints (nav panel becomes an overlay, rail becomes a bottom bar).
   A few module-level dashboards (e.g. `rostering_hub.css`) currently ship
   their own mobile bottom-nav — audit for a visual collision with the
   shell's mobile rail bottom bar when retrofitting that screen (see
   rollout plan Phase 1).
7. Confirm the screen is reachable from the curated nav tree
   (`nav_catalog.js`) or, if it's a secondary/config screen, from Full Menu
   (`···` in the nav panel) — never leave a working screen orphaned.
8. Spot-check contrast ≥ 4.5:1, `title`/`aria-label` on icon-only controls,
   and that Esc closes any new overlay.
