# DeployGuard Desktop

Windows desktop pilot shell for DogForce Security Services. Tauri v2 + Rust
+ React/TypeScript, following `docs/deployguard/17-desktop-architecture.md`
and `docs/deployguard/05-ux-principles.md`.

**This is the P2A pilot slice**, not the full DeployGuard Platform desktop
client. It authenticates via DeployGuard ERP's (Odoo's) own login page and
embeds Odoo directly in the window — see [`DEVIATIONS.md`](./DEVIATIONS.md)
for exactly what's deferred until the Platform backend (BUILD-ORDER P1+)
ships, and why.

## What it does today

- **Single login, on Odoo's own page.** No DeployGuard-branded login form:
  the app loads Odoo's real `/web/login` directly, and once you're signed
  in there, the app knows who you are (read from the session cookie).
- **A persistent toolbar** docked to the top of the window — real Back /
  Forward / Reload controls for Odoo (driving its own browser history),
  a Home button, connection status, and your name — always visible, not
  hidden behind a hover gesture.
- **A DeployGuard mega menu** — click the brand button to drop down a
  panel with your DeployGuard home content, overlaying the top of Odoo
  without resizing it. Closes on click-again, click-outside, or Escape.
- Odoo fills the rest of the window below the toolbar — it's the primary
  surface, not something hidden behind DeployGuard's own chrome.
- Honest connection status (online / DeployGuard System unavailable) —
  never a silent failure.
- Home content shows only real information; features that don't exist yet
  (My Work, Training) say so plainly instead of showing fake data.

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Node.js | 24.x | `nvm install 24` |
| Rust | stable (1.77+) | `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \| sh` |
| Tauri CLI | via `npm` (already a devDependency) | `npm ci` |

**macOS (development machine):** Xcode Command Line Tools
(`xcode-select --install`).

**Windows (target platform):** builds are produced via GitHub Actions
(`.github/workflows/desktop-build.yml`), so a physical Windows machine is
*not* required for development. If you do want to build locally on
Windows: Visual Studio Build Tools with the "Desktop development with
C++" workload, and the WebView2 runtime (bundled by the installer for
end users automatically).

## Local development

```bash
cd desktop
cp .env.example .env.development
# edit .env.development if you're pointing at a local/staging Odoo
npm install
npm run tauri:dev
```

**Use `tauri:dev`, not `tauri dev` directly.** Vite's `VITE_*` env vars only
reach the frontend bundle — the Rust/Tauri process reads its own
`DEPLOYGUARD_ODOO_BASE_URL` / `DEPLOYGUARD_ODOO_DB` from the real process
environment (`src-tauri/src/config.rs`), which plain `npm run tauri dev`
never sets. Without them, Rust silently authenticates with `db: null`,
which Odoo rejects as "Missing database name" — surfaced to you as a
misleading "Incorrect username or password". `npm run tauri:dev` (backed
by `scripts/dev.sh`) reads `.env` and exports both sets of variables
before launching. See `desktop/DEVIATIONS.md` if you hit this anyway.

This opens the app pointed at whatever `VITE_ODOO_BASE_URL` you set —
**never point a development build at production credentials you don't
own.** For local Odoo, use the repo's existing `bash scripts/start.sh`
stack and set `VITE_ODOO_BASE_URL=http://localhost:8069`.

## Type checking, linting

```bash
npm run typecheck   # tsc --noEmit
npm run lint        # eslint
```

## Running tests

```bash
# Rust unit tests (odoo::is_unauthenticated_path, windowing::shell_bounds
# + odoo_bounds, config::odoo_base_url)
cd desktop/src-tauri
cargo test

# Frontend unit tests (extractErrorMessage, config/env)
cd desktop
npm install   # first time only
npm test
```

## Building a Windows installer

### Via CI

Push to `main` (paths under `desktop/`), or run the workflow manually from
the Actions tab (`DeployGuard Desktop — Windows build`, with
`workflow_dispatch`). The unsigned (see below) `.exe` (NSIS) and `.msi`
installers are uploaded as build artifacts.

**⚠️ Currently blocked:** the repository's GitHub account has a billing
lockout ("The job was not started because your account is locked due to a
billing issue"), confirmed via a real triggered run
([PR #1](https://github.com/creativesites/DogFrce-Security-Services-Custom-Odoo-Modules/pull/1))
that failed in ~3 seconds before any build step ran. This affects **every**
workflow on this repo, not something specific to the desktop build — it
predates this app (checked `main`'s CI history back to 2026-09-02, same
failure on unrelated commits). **A human needs to resolve billing on the
account before any CI can run.** The workflow YAML itself has been
statically verified against the real `tauri-apps/tauri-action` inputs and
this project's actual scripts/config — no known bugs are blocking it once
billing is fixed.

### Locally, cross-compiling isn't supported

Tauri does not support cross-compiling a Windows bundle from macOS. If you
need a local Windows build, run on an actual Windows machine or a Windows
VM:

```powershell
cd desktop
npm install
npm run tauri build -- --target x86_64-pc-windows-msvc
```

Output: `desktop/src-tauri/target/x86_64-pc-windows-msvc/release/bundle/`
(`nsis/*.exe` and `msi/*.msi`).

## Code signing

**Not yet configured.** Current builds are unsigned, which means:

- Windows SmartScreen will warn on first run ("Windows protected your PC").
- The Tauri auto-updater is disabled (`"active": false` in
  `tauri.conf.json`) because signing is what makes update verification
  meaningful.

This is tracked as `docs/deployguard/32-open-questions.md` OQ-7. Once a
certificate (or Azure Trusted Signing enrollment) exists:

1. Add `WINDOWS_CERTIFICATE` / `WINDOWS_CERTIFICATE_PASSWORD` (or the
   Trusted Signing equivalents) as GitHub Actions secrets.
2. Generate a Tauri updater keypair (`npm run tauri signer generate`),
   store the private key as a secret, put the public key in
   `tauri.conf.json`'s `plugins.updater.pubkey`.
3. Uncomment the signing env vars in
   `.github/workflows/desktop-build.yml` (search `TODO(signing)`).
4. Flip `plugins.updater.active` to `true`.

## Environment configuration

Three environments, matching `docs/deployguard/26-deployment-strategy.md`:
`development`, `staging`, `production`. Copy `.env.example` to
`.env.<environment>` and fill in the (non-secret) values — see the
comments in that file. **Never commit an `.env.*` file except
`.env.example`.**

The same env vars exist on the Rust side under different names
(`DEPLOYGUARD_ODOO_BASE_URL`, `DEPLOYGUARD_ODOO_DB`) — see
`src-tauri/src/config.rs`. CI sets these directly rather than reading a
`.env` file (see the workflow's "Write build-time config" step).

## Security notes

- Passwords are **never** stored anywhere in this app — they go straight
  from Odoo's own login form to Odoo. The app only reads back the
  resulting session cookie (`src-tauri/src/odoo.rs`) to know who's signed
  in; it never persists it beyond in-memory app state.
- The "odoo" webview has **zero** Tauri IPC capabilities — see
  `src-tauri/capabilities/main.json`, scoped by `"webviews": ["shell"]`
  (not by window — both webviews share the "main" window). Nothing in
  Odoo's page JavaScript can call back into this app. Back/Forward/Reload
  are one-off `Webview::eval()` calls from Rust (`history.back()` etc.),
  the same effect a real browser's own buttons have — not a persistent
  injected bridge.
- No credential, token or session value is ever logged, included in
  diagnostics (`src-tauri/src/diagnostics.rs`), or sent to the frontend.
- Before touching production credentials, read
  `docs/deployguard/16-security-architecture.md` and
  `docs/deployguard/00-current-state.md` §7 (known ERP-side gaps this
  pilot inherits until Stage 0 of the rollout plan closes them).

## Where things live

```
desktop/
├── src/                    React/TypeScript app
│   ├── session/              Session context (mirrors Rust's AppState.session)
│   ├── shell/                 Toolbar + mega menu, icons, status
│   ├── config/                  env.ts — the only place URLs are read from
│   └── styles/                   ds.css / dgs.css (verbatim token ports) + shell.css
└── src-tauri/               Rust core
    ├── src/
    │   ├── windowing.rs        Window + two-webview layout, toolbar/menu bounds,
    │   │                        session sync, Odoo history control
    │   ├── odoo.rs               Session-cookie readback + Odoo HTTP calls
    │   ├── state.rs                Shared in-process AppState
    │   ├── commands.rs               IPC command surface ("shell" webview only)
    │   ├── connectivity.rs             Honest online/unavailable reporting
    │   └── diagnostics.rs                Non-sensitive diagnostics bundle
    └── capabilities/main.json    IPC scoped to the "shell" webview only
```

## Testing checklist (before handing to a pilot user)

See the desktop build mission §23 for the full list. Minimum before any
install goes to a real DogForce employee:

- [ ] Fresh Windows VM: install → launch → Odoo's own login page loads
      below the toolbar → sign in with real Odoo credentials → mega menu
      auto-opens once, showing your name.
- [ ] Wrong password shows Odoo's own error on its login page (not a
      DeployGuard-branded one) — confirm it's legible and not broken by
      the toolbar's presence.
- [ ] Quit and relaunch: still signed in (Odoo's own persistent cookie),
      no re-entry of credentials needed.
- [ ] Sign out from the mega menu: lands back on Odoo's login page.
- [ ] Turn off Wi-Fi mid-session: toolbar status dot shows "DeployGuard
      System is unavailable", not a frozen or blank screen.
- [ ] Back / Forward / Reload actually control Odoo's page history after
      navigating within Odoo.
- [ ] Window resizes down to 1024×700 without breaking the toolbar or
      mega menu layout.
- [ ] Full keyboard navigation: Tab to the brand button, Enter opens the
      mega menu, Escape closes it and — check this specifically — returns
      focus to the brand button (see `AGENT-FINDINGS.md` §1, this was
      found broken and needs a fix).
- [x] Automated coverage for `odoo::is_unauthenticated_path` (many cases,
      `src-tauri/src/odoo.rs`).
- [x] Automated coverage for `windowing::shell_bounds` and `odoo_bounds` —
      toolbar/menu geometry and Odoo's bounds below it, at default and
      edge-case window sizes (`src-tauri/src/windowing.rs`).
- [x] Automated coverage for `config::odoo_base_url` — env var precedence,
      trailing-slash stripping, whitespace handling
      (`src-tauri/src/config.rs`).
- [x] Automated coverage for `extractErrorMessage` — all input shapes,
      including a regression test for a real bug found during this pass
      (`src/lib/extractErrorMessage.test.ts`).
- [x] Automated coverage for `config/env.ts` — env var precedence and
      defaults for every field (`src/config/env.test.ts`).
- [ ] Manual accessibility pass against
      `docs/deployguard/05-ux-principles.md` §9 — see
      [`AGENT-FINDINGS.md`](./AGENT-FINDINGS.md) for a computed WCAG
      contrast audit; the findings there were written against the
      earlier hover-handle design and need re-checking against the
      current toolbar, but the same token-level issues (focus ring
      contrast, chip opacity) likely still apply since the tokens
      haven't changed.

## Relationship to the planning docs

Read in this order if you're new to this codebase:

1. `docs/deployguard/README.md`
2. `docs/deployguard/BUILD-ORDER.md` — this app is an accelerated P2A
   slice of planned phase P2.
3. `docs/deployguard/17-desktop-architecture.md`
4. `docs/deployguard/adr/DG-ADR-007-authentication.md`
5. [`DEVIATIONS.md`](./DEVIATIONS.md) — every place this code differs from
   those documents, and why.

## Agent verification log (background CI/test hardening pass)

**2026-09-16, background agent pass** (scope: CI/build verification, Rust
and frontend unit test coverage, WCAG contrast audit — against the
hover-handle overlay design that was live when the pass started; the main
session subsequently redesigned the chrome into the toolbar + mega menu
described above, so file/line references below are historical):

- **CI (`.github/workflows/desktop-build.yml`):** static review against
  `package.json`'s real scripts, `tauri.conf.json`, `Cargo.toml`, and
  `tauri-apps/tauri-action`'s actual `action.yml` inputs (fetched live).
  No concrete bugs found. A real Windows Actions run was triggered via a
  pushed branch + PR to close the loop on what static review can't
  confirm — **it failed immediately on a repository-wide GitHub billing
  lockout**, unrelated to this code (see "Building a Windows installer"
  above).
- **Rust unit tests added:** `src-tauri/src/odoo.rs` (`is_unauthenticated_
  path`, 12 cases), `src-tauri/src/config.rs` (`odoo_base_url`, 7 cases).
  (`windowing.rs`'s tests from this pass targeted the pre-toolbar geometry
  and were superseded by new tests for the toolbar/mega-menu geometry
  written during the redesign.)
- **Frontend tests added:** Vitest 1.6.1 (pinned to match the existing
  Vite 5 devDependency — `vitest@latest` requires Vite 6/7).
  `src/lib/extractErrorMessage.test.ts` (15 cases) and
  `src/config/env.test.ts` (13 cases).
- **Bug found + fixed:** `src/lib/extractErrorMessage.ts` returned an
  empty string instead of its fallback message for an `Error` with an
  empty `.message` — fixed, with a regression test.
- **Accessibility audit:** computed real WCAG contrast ratios against the
  design existing at the time (see [`AGENT-FINDINGS.md`](./AGENT-FINDINGS.md)
  §1 for full numbers). Findings worth re-checking against the current
  toolbar since the same tokens are reused: focus-ring contrast
  (`--ds-accent-mid` ≈1.4:1 vs. required 3:1), the "Coming soon" chip's
  effective contrast once `opacity: .6` is accounted for (≈2.16:1 vs.
  required 4.5:1), and Escape not returning focus to its trigger.
