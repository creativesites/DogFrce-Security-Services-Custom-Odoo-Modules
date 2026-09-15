# DG-ADR-017 — Design-System Token Port, `security_shell` Parity & Enforcement

- **Status:** Accepted in principle (product decisions R-3, 2026-09-15); mechanics Proposed
- **Date:** 2026-09-15
- **Related:** [05-ux-principles](../05-ux-principles.md), [`docs/DEPLOYGUARD_DESIGN_SYSTEM.md`](../../DEPLOYGUARD_DESIGN_SYSTEM.md), `custom_addons/security_shell/`, `custom_addons/security_base/static/src/css/design_system.css`

## Context

The product owner requires all Platform UI to follow the DeployGuard design system, and states that **`security_shell` is very important**: it is the canonical DeployGuard experience.

The design system has two token layers:

- `--ds-*` base tokens in `security_base`;
- `--dgs-*` shell tokens in `security_shell`.

It also has seven hard rules (mono numerals, rail as the only dark surface, max two gradients, status colours only from tokens, no viewport overlays outside shell chrome, no `!important`, stroke SVG icons), plus component patterns and a retrofit checklist.

The Platform is built in React/Tailwind, not OWL, so tokens and patterns must be ported without divergence. Legacy DeployGuard surfaces already drifted: the mobile app uses indigo `#4F46E5`, and some dashboards used full-viewport overlays and decorative gradients.

## Decision

1. **Single source of truth stays in the Odoo repo.**
   - `design_system.css` and `shell_tokens.css` remain the authoritative token definitions.
   - `docs/DEPLOYGUARD_DESIGN_SYSTEM.md` remains the authoritative rules document.
   - New tokens are added there first, by design decision.
2. **Verbatim port.** `packages/ui/src/tokens/ds.css` and `dgs.css` are byte-identical copies of the token blocks, with a header noting the source commit.
   - A `tooling/token-sync` script updates them.
   - CI fails if the pinned copies differ from the declared source commit's content.
3. **Tailwind token-only preset.** The default palette is removed; only token-backed colours, radii, shadows and fonts exist. Arbitrary values are disallowed.
4. **Lint enforcement (CI errors):**
   - stylelint: `color-no-hex` outside `tokens/`, `declaration-no-important`, `function-linear-gradient` banned outside `CoverageBar`/`MetricBar`;
   - no `position: fixed` in screen components (allowed only in `packages/ui/shell/overlays`).
   - ESLint custom rules:
     - `bg-rail`/`text-rail*` classes only in `shell/Rail*`;
     - icons only via `<Icon>` (Lucide, `strokeWidth` 1.9);
     - numerals inside `<Metric*>`/`<Kpi*>`/`<Num>` components.
5. **Shell parity.** `packages/ui/shell` is a React port of `security_shell` behaviour and look ([05](../05-ux-principles.md) §4):
   - rail with flyouts;
   - typed nav catalogue with `soon` / `NOT INSTALLED` chips and count pills;
   - ⌘K command palette;
   - Home/Today composition;
   - profile card;
   - loading bar;
   - identical breakpoints.
6. **Visual parity tests.** Playwright screenshot comparisons of shell primitives (rail, nav panel, card, tile, pills, chips, coverage bar) against reference screenshots captured from the Odoo `security_shell` at the same viewport sizes, with tolerance thresholds. Reference captures are refreshed when the Odoo shell changes.
7. **Fonts.**
   - `--dgs-font` resolves from tenant theme `--dg-font-family` (the same concept as `security_theme`'s loader).
   - The Platform bundles WOFF2 files for IBM Plex Mono and the theme-selectable families locally (offline, no external font CDN).
8. **Component catalogue.** A Storybook (or Ladle) instance for `packages/ui` documents every component with all required states ([05](../05-ux-principles.md) §6), and runs accessibility checks (axe) in CI.
9. **No dark mode.** The rail is the only dark surface (hard rule 2). A dark theme would require a design-system decision first.

## Alternatives

| Option | Why not |
|---|---|
| Recreate "inspired-by" styling in Tailwind defaults | Guaranteed drift; violates R-3. |
| Off-the-shelf component kit theme (MUI, Chakra, shadcn defaults) | Imports its own visual language and tokens; fights hard rules (gradients, radii, fonts). Headless primitives styled with our tokens are allowed. |
| Publish tokens as an npm package from the Odoo repo | The Odoo repo has no JS package pipeline; verbatim sync + CI check is simpler. Revisit if a third consumer (e.g. mobile retrofit) appears. |
| Embed the Odoo shell itself in the desktop app | Iframing Odoo breaks isolation and SSO ticket design ([DG-ADR-007](DG-ADR-007-authentication.md)), and couples Platform screens to Odoo's web client. |

## Tradeoffs

| We gain | We accept |
|---|---|
| One recognisable product across ERP and Platform | Token changes need a two-repo flow (Odoo first, then sync) |
| Automated enforcement instead of review vigilance | Custom lint rules to maintain |
| Accessible, state-complete components | Upfront component-catalogue work in P0–P2 |

## Consequences

- P0 builds `packages/ui` tokens, the Tailwind preset, lint rules and the first shell primitives. P2 acceptance includes the visual parity checklist.
- Any request for a new colour, radius, gradient or dark surface is recorded as a design decision in `docs/DEPLOYGUARD_DESIGN_SYSTEM.md` before implementation.
- A future retrofit of DeployGuard Mobile (C-8) should reuse the same token files through a React Native token adapter.
