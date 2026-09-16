# DeployGuard Desktop

Windows desktop pilot shell for DogForce Security Services. Tauri v2 + Rust
+ React/TypeScript, following `docs/deployguard/17-desktop-architecture.md`
and `docs/deployguard/05-ux-principles.md`.

**This is the P2A pilot slice**, not the full DeployGuard Platform desktop
client. It authenticates directly against DeployGuard ERP (Odoo) and opens
it in an isolated window — see [`DEVIATIONS.md`](./DEVIATIONS.md) for
exactly what's deferred until the Platform backend (BUILD-ORDER P1+) ships,
and why.

## What it does today

- Single login with your existing DogForce Odoo username and password.
- A real DeployGuard shell (rail, canvas, status) built from the same
  design tokens as `security_shell` — see `src/styles/ds.css` / `dgs.css`.
- One click ("Open DeployGuard ERP") into your production Odoo, already
  signed in — no second login.
- Honest connection status (online / Odoo unreachable / offline) instead
  of silent failures.
- Secure session storage in your OS keychain — never a plaintext file.
- Home shows only real information; features that don't exist yet (My
  Work, Training) say so plainly instead of showing fake data.

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

## Building a Windows installer

### Via CI (recommended)

Push to `main` (paths under `desktop/`), or run the workflow manually from
the Actions tab (`DeployGuard Desktop — Windows build`, with
`workflow_dispatch`). The signed... **unsigned** (see below) `.exe` (NSIS)
and `.msi` installers are uploaded as build artifacts.

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

- Passwords are **never** stored — only the Odoo session cookie, and only
  in the OS keychain (`src-tauri/src/keychain.rs`), via the `keyring`
  crate (Windows Credential Manager / macOS Keychain).
- The "Open DeployGuard ERP" window (`src-tauri/src/odoo_window.rs`) has
  **zero** Tauri IPC capabilities — see
  `src-tauri/capabilities/main.json`, scoped to `"windows": ["main"]`
  only. Nothing in Odoo's page JavaScript can call back into this app.
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
│   ├── auth/                AuthProvider abstraction + Odoo implementation
│   ├── shell/                Rail, icons, AppShell, StatusBar
│   ├── home/                  Home screen
│   ├── odoo/                   "Open Odoo" trigger
│   ├── config/                  env.ts — the only place URLs are read from
│   └── styles/                   ds.css / dgs.css (verbatim token ports) + shell.css
└── src-tauri/               Rust core
    ├── src/
    │   ├── odoo.rs            Direct Odoo auth (MVP deviation — see DEVIATIONS.md)
    │   ├── odoo_window.rs        Isolated Odoo webview + cookie seeding
    │   ├── keychain.rs             OS-native secure storage
    │   ├── commands.rs               IPC command surface
    │   ├── connectivity.rs             Honest online/offline/degraded reporting
    │   └── diagnostics.rs                Non-sensitive diagnostics bundle
    └── capabilities/main.json    IPC scoped to the "main" window only
```

## Testing checklist (before handing to a pilot user)

See the desktop build mission §23 for the full list. Minimum before any
install goes to a real DogForce employee:

- [ ] Fresh Windows VM: install → launch → sign in with real Odoo
      credentials → Home loads → Open DeployGuard ERP lands on a real,
      authenticated Odoo screen.
- [ ] Wrong password shows a clear error, not a stack trace.
- [ ] Quit and relaunch: session restores without re-entering credentials.
- [ ] Sign out, then relaunch: back at the login screen.
- [ ] Turn off Wi-Fi mid-session: status bar shows "DeployGuard ERP is
      unavailable", not a frozen or blank screen.
- [ ] Uninstall, reinstall: clean state, no leftover keychain entry
      causing a confusing auto-login.
- [ ] Window resizes down to 1024×700 without breaking layout.
- [ ] Full keyboard navigation through the login form and rail.
- [x] Automated coverage for `odoo::is_unauthenticated_path` (many cases,
      `src-tauri/src/odoo.rs`).
- [x] Automated coverage for `windowing::shell_bounds` — collapsed/expanded
      geometry at default, minimum, and edge-case window sizes
      (`src-tauri/src/windowing.rs`).
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
      contrast audit that already found real gaps (focus-ring contrast,
      chip opacity) still needing a fix in `shell.css`.

## Running tests

```bash
# Rust unit tests (odoo::is_unauthenticated_path, windowing::shell_bounds,
# config::odoo_base_url)
cd desktop/src-tauri
cargo test

# Frontend unit tests (extractErrorMessage, config/env)
cd desktop
npm install   # first time only
npm test
```

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

**2026-09-16, background agent pass.** Scope: CI/build verification, Rust
and frontend unit test coverage, and a WCAG contrast audit. Did not touch
`Overlay.tsx`, `StatusBar.tsx`, `src/session/**`, `src-tauri/src/
windowing.rs` (only appended a new `#[cfg(test)]` block at its end), or
`src/styles/shell.css` — those were being actively iterated on in the main
session; see [`AGENT-FINDINGS.md`](./AGENT-FINDINGS.md) for what would
need to change there.

- **CI (`.github/workflows/desktop-build.yml`):** static review against
  `package.json`'s real scripts, `tauri.conf.json`, `Cargo.toml`, and
  `tauri-apps/tauri-action`'s actual `action.yml` inputs (fetched live).
  No concrete bugs found — script names match, the action's
  omit-`tagName`-to-skip-releases behavior is used correctly, all
  dependencies are cross-platform (`rustls-tls`, no Unix-only assumptions),
  all 5 referenced icon files exist. A real Windows Actions run was
  triggered via `gh` from a pushed branch to close the loop on what static
  review can't confirm (actual MSVC/NSIS build success) — see
  AGENT-FINDINGS.md §2 for what remains unverified if that run hadn't
  finished by the time this pass ended.
- **Rust unit tests added:** `src-tauri/src/odoo.rs` (`is_unauthenticated_
  path`, 12 cases), `src-tauri/src/windowing.rs` (`shell_bounds`, 8 cases
  covering collapsed/expanded geometry at default, minimum, and clamped
  edge-case window sizes — purely additive `mod tests` block at the file's
  end), `src-tauri/src/config.rs` (`odoo_base_url`, 7 cases covering env
  var precedence, trailing-slash stripping, whitespace handling). **29/29
  passed** — `cd desktop/src-tauri && cargo test`.
- **Frontend tests added:** Vitest 1.6.1 (pinned to match the existing
  Vite 5 devDependency — `vitest@latest` requires Vite 6/7).
  `src/lib/extractErrorMessage.test.ts` (15 cases) and
  `src/config/env.test.ts` (13 cases, using `vi.resetModules()` +
  `vi.stubEnv()` since `config` is computed eagerly at import time).
  **28/28 passed** — `cd desktop && npm test`. `npm run typecheck` and
  `npm run lint` both still pass clean.
- **Bug found + fixed:** `src/lib/extractErrorMessage.ts` returned an
  empty string instead of its fallback message for an `Error` with an
  empty `.message` — fixed, with a regression test. See
  AGENT-FINDINGS.md §3.
- **Accessibility audit:** computed real WCAG contrast ratios for every
  text/background and UI-component/background pair used in the overlay
  panel and handle, against the 4.5:1 / 3:1 AA thresholds in
  `docs/deployguard/05-ux-principles.md` §9. Found 3 real failures (focus
  ring ~1.4:1 vs. required 3:1, "Coming soon" chip effective contrast
  ~2.16:1 once its `opacity: .6` is accounted for, loading-state text at
  4.40:1 on `--dgs-canvas`) plus one keyboard-focus-management gap (Escape
  collapses the panel but doesn't return focus to the handle). Full
  numbers, severity, and suggested one-token fixes in
  [`AGENT-FINDINGS.md`](./AGENT-FINDINGS.md) §1 — not applied directly
  since they require editing boundary files.
