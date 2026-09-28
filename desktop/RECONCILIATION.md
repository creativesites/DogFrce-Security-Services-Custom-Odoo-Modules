# DeployGuard Desktop — Reconciliation

> **Status:** source of truth for the desktop as of 2026-09-28. Where this
> document disagrees with `docs/deployguard/BUILD-STATUS-AND-PHASE-PLAN.md`,
> `desktop/README.md` or `desktop/DEVIATIONS.md`, this document wins; those are
> being updated to point here.
>
> **North star:** *DeployGuard turns the DogForce roster into guided,
> measurable, teachable work.*

This file records the result of a full audit of the desktop code, its git
history, the planning docs (README, BUILD-ORDER, BUILD-STATUS, 05, 16, 17, 20,
24–26, 28, 31, ADR-001/007/011/017) and the Odoo modules the desktop depends on.
Every claim below was checked against code, not against a status document.

---

## A. What the original plan required

| Area | Plan (source) |
|---|---|
| Framework | Tauri v2, thin Rust core, React + TS; Electron as fallback (DG-ADR-001) |
| Repo | Separate `deployguard-platform` pnpm/Turborepo monorepo: `apps/desktop`, `packages/{app,ui,odoo,contracts,domain,ai}` (DG-ADR-005, 17 §1) |
| Auth | Odoo is the identity provider; Platform is the session authority. Bridge assertion → `/v1/auth/exchange` → device-bound tokens; Odoo opened via brokered SSO ticket (DG-ADR-007) |
| Webviews | Two windows: `main` (full IPC allowlist) and `odoo` (zero IPC, no injected scripts, navigation restricted to the tenant's Odoo host; anything else opens in the system browser) (17 §2, 16 §7) |
| IPC | Typed allowlist of ~18 commands (17 §3) |
| Offline | SQLCipher store + command outbox with UUIDv7 command ids, 72 h staleness cap, honest sync states (DG-ADR-011, 20) |
| Updater | Signed updater, `pilot`/`stable` channels, 6-hourly checks, downgrade prevention; NSIS + MSI; Authenticode signing before pilot (17 §8, 26 §4) |
| Design system | Byte-identical `ds.css`/`dgs.css` in `packages/ui`, drift CI, token-only Tailwind preset, stylelint, React port of `security_shell`, Playwright parity (DG-ADR-017, 05) |
| API | REST `/v1` on a Fastify Platform (24) |
| Business logic | Backend only — "the client never decides whether work is overdue" (17 §1) |

## B. What the desktop actually implements (verified 2026-09-28)

**Architecture**
- One window `main` with two sibling child webviews (`src-tauri/src/windowing.rs`):
  `odoo` (Odoo's own UI, below a 48 px toolbar) and `shell` (the React app —
  the toolbar strip, or the full window while the *app view* is open).
- Capabilities are scoped by **webview**, not window
  (`src-tauri/capabilities/main.json` → `"webviews": ["shell"]`). The `odoo`
  webview has zero IPC. No persistent init scripts. This is correct and retained.
- Auth: the user signs in on Odoo's own `/web/login`. After each page load,
  Rust reads the `session_id` cookie from the `odoo` webview, verifies it with
  `/web/session/get_session_info`, keeps the cookie in Rust (`AppState`) and
  sends only `{uid, login, name, db}` to React.
- Data access: a generic `odoo_call_kw` Tauri command proxies
  `/web/dataset/call_kw` using the employee's own session (their ACLs, no
  elevation). Domain TS modules in `src/api/*.ts` wrap it.
- Capability probing (`src/api/capabilities.ts`): one `fields_get` per feature
  model; screens whose module is absent disappear rather than erroring
  (commit d051d72).

**Screens:** Home (inline in `Toolbar.tsx`), My Work & Sweeps (tasks,
checklists, roster sign-offs), My Training (courses, lessons, assessments,
lesson AI assist via Gemini), Adoption, Exceptions Inbox, Owner Overview,
Help drawer, Problem report, Task feedback, First-run onboarding with the
monitoring notice, Update notice, Diagnostics.

**Release path:** Tauri updater active (v0.2.0, minisign pubkey, GitHub
releases endpoint, user-initiated install). NSIS via `scripts/build-windows-xcompile.sh`
from macOS. CI (`.github/workflows/desktop-build.yml`) runs typecheck, lint,
Vitest and `cargo test` on `windows-latest` and builds unsigned installers.

**Backend modules used:** `security_work`, `security_training`,
`security_adoption`, `security_exceptions`, `security_deployguard_bridge`
(monitoring notice), `security_operations` (roster sign-offs),
`security_help`, and `security_support` (see D below — the source was missing).

**Platform:** does not exist. There is no Fastify API, Platform DB,
`packages/ui` or `packages/app`. `packages/ai` exists and is unused by the desktop.

## C. Intentional deviations (keep)

| # | Deviation | Why it is right for now |
|---|---|---|
| C-1 | **Track A.** Features are Odoo modules; the desktop talks to Odoo, not to a Platform | DogForce production Odoo exists; the Platform does not. BUILD-STATUS §2 recommended it; this document ratifies it |
| C-2 | **Cookie-read auth** (DEVIATIONS D-1). Odoo's own login page; no DeployGuard password form | Odoo stays the authentication authority; no credential ever touches app code |
| C-3 | **One window, two sibling webviews** instead of two windows | Explicit product direction. Isolation is preserved by webview-scoped capabilities |
| C-4 | **Full-window app view** + toolbar, replacing the corner overlay and mega menu | Supersedes DEVIATIONS D-2's overlay design. The DeployGuard side is a real app |
| C-5 | **Generic `odoo_call_kw`** instead of a typed per-feature allowlist | Avoids dozens of bespoke Rust commands. Odoo ACLs are the authority. Hardened by identifier validation (see G) |
| C-6 | **Gemini in training** (`lesson.ask_ai`) despite 28 §3.1's "no AI in MVP" | Founder-approved 2026-09-17. Scoped to approved lesson content |
| C-7 | **Adoption shipped before the privacy/legal gate** (09, 16 §9) | Founder override. The UI hides adoption until the monitoring notice is acknowledged. Server-side enforcement is in NEXT |
| C-8 | **React 18 / Vite 5** rather than React 19 (DG-ADR-016) | No functional reason to churn. Upgrade when `packages/app` is extracted |
| C-9 | **No monorepo.** The app lives in `desktop/` in the ERP repo | No second consumer exists yet. Extract when one does |
| C-10 | **Guided tasks run inside Odoo** as an Odoo module asset (`security_guidance`), not injected by the desktop | Lets guidance highlight real Odoo UI while the `odoo` webview keeps zero IPC and no injected scripts. The desktop and the Odoo runner sync only through a server-side guidance session record |

## D. Accidental deviations (fix)

**Security**
1. `on_navigation(|_| true)` — the `odoo` webview could navigate anywhere (plan: tenant host only).
2. `navigate_odoo` built `format!("{base}{path}")` from unvalidated input; a path like `@evil.com` changes the host.
3. The session cookie was taken from *any* domain's `session_id`.
4. `odoo_call_kw` accepted arbitrary model/method strings (Odoo blocks `_private`, but nothing else was validated).
5. Server HTML (help articles, lesson bodies) was rendered with unsanitized `dangerouslySetInnerHTML`.
6. `vite.config.ts` `envPrefix` included `DEPLOYGUARD_`, which would bake any such env var into the bundle.
7. Full Odoo error payloads (including `data.debug` tracebacks) were written to the local log.
8. `never_deploy.md` contained plaintext production credentials (now redacted — **rotate them**; they remain in git history).
9. Adoption decided "is manager" in the UI from `uid === 2` or hard-coded staff names in the login.

**Correctness**
10. `AppError` unit variants serialised without `message`, so every network/server error showed generic fallback text.
11. ~14 CSS classes used but never defined (`dg-modal*`, `dg-sr-only`, `dg-badge`, `dg-spinner`, …), so five dialogs were unstyled.
12. Help, Report and ⌘K opened while the shell was a 48 px strip and were clipped.
13. Direct `invoke("app_view_close")` calls desynced React from native view state; the Inbox navigated Odoo without closing the app view.
14. Session expiry was not surfaced: `auth_expired` was never produced, `isExpired` never read, and one failed verification during a network blip signed the user out.
15. `StatusBar` was mounted twice, so connectivity was polled twice.
16. The CSP had no `frame-src`, so video lessons could not play.
17. Opening the assessment modal consumed an attempt.
18. Number checklist answers could not be cleared.
19. Inbox shortcuts ignored modifiers (Ctrl+A acknowledged an exception).
20. Adoption rendered UTC times as local.
21. `appVersion` was hard-coded `0.1.0` in problem reports.
22. CI enabled `createUpdaterArtifacts` without a signing key, so the bundle step cannot succeed.

**Missing source**
23. `security_support` (support requests, task feedback, owner overview) is called by the desktop, marked ✅ in BUILD-STATUS Phase 7, listed as approved for production, and relied on by adoption's `system_fault` excusal — **but it has never been committed to this repository.** It is rebuilt in this recovery to match the calls the desktop makes.

**Business rules in UI**
24. Adoption factor weights and confidence thresholds are duplicated in `src/api/adoption.ts`.
25. Exception counts are computed by downloading all open instances.
26. Training "everything done" is re-derived in the UI.

**Docs**
27. `DEVIATIONS.md` D-2, D-5 and D-6 and `README.md` "What it does today" describe superseded designs.
28. BUILD-STATUS §1.1 contradicts its own §5, and scope docs contradict each other on `security_tour` and the bridge. This document supersedes them for the desktop.

## E. Architecture decisions retained

- DG-ADR-001: Tauri v2 + React.
- DG-ADR-007: the **isolation** and "no credentials in app code" parts. Odoo is the identity provider.
- DG-ADR-011 / doc 20: the offline design, *as the future design* (not built now).
- DG-ADR-017: `security_shell` + `security_base` tokens are the only visual source. `ds.css`/`dgs.css` are copies; no new palette. Enforced by `scripts/check-tokens.mjs`.
- 17 §1 "thin client": the backend owns business truth. Overdue, escalation, scores and permissions are computed in Odoo and rendered by the desktop.
- 16 §7: the `odoo` webview has zero IPC, no injected scripts, and navigation limited to the Odoo origin.

## F. Architecture decisions deferred

| Decision | Deferred until |
|---|---|
| Platform auth exchange, device keypair, refresh tokens, revocation (ADR-007) | The Platform exists |
| SQLCipher store + outbox (ADR-011) | A real offline use case. Office staff at DogForce have connectivity |
| `packages/ui` / `packages/app` extraction, Tailwind preset, Storybook, Playwright parity (ADR-017) | A second consumer (web app) |
| `pilot`/`stable` channels, `min_supported_version` 426 enforcement | More than one release ring |
| Sentry / remote telemetry | Pilot feedback shows the local log is insufficient |

## G. Must fix before DogForce rollout

Done in this recovery (see `git log` on `claude/relaxed-allen-qbvh6q`):
1. Security items D-1 to D-9.
2. Correctness items D-10 to D-22.
3. `security_support` rebuilt in the repo (D-23).
4. Business rules moved to the server (D-24 to D-26).
5. The V2 slice (roster → Register/Confirm/Verify → guided task → Team Today),
   with HR's missing "verify & lock" screen added and roster approval
   gated to HR/GM, per the revised roles matrix.

Still open (owner: Winston unless noted):
6. **Rotate** the credentials previously committed (`never_deploy.md`, `CLAUDE.md` history, `odoo.conf`). *Owner: Winston.*
7. Updater signing key backed up off the single laptop and stored as a CI secret (`TAURI_SIGNING_PRIVATE_KEY`). *Owner: Winston.*
8. One clean-VM Windows 10/11 install → sign in → N→N+1 update pass (`desktop/RELEASING.md`). *Owner: Winston.*
9. The V2 slice installed on **staging**, set up with the pipeline wizard, and walked through end to end (RELEASING.md, Manual QA).
10. Give the GM's production user the Security Owner group (full access, as agreed with Kuume and Wilbert).

## H. Belongs to the future Platform

Fastify `/v1` API, Platform Postgres + RLS tenancy, event bus and outbox
consumers, cross-tenant analytics, device management and revocation,
brokered Odoo SSO, the `packages/*` monorepo, SSE streams, and Platform-side AI
(`packages/ai`). The desktop's `src/api/*.ts` modules are the seam: today they
call `odoo_call_kw`; later they call `/v1`. No component calls `invoke()` for
data directly.

## I. Explicitly NOT to build now

- The Platform API, DB, RLS, events, Kafka, Kubernetes or microservices.
- Offline mode, partial caches, or "pending sync" UI.
- A second login or password system.
- A monorepo move or mass file renames.
- Surveillance metrics: time-in-app, mouse or keystroke activity, screen capture. Adoption measures **expected work vs. actual work** only.
- AI features that are not grounded in operational records or approved content.
- Automation that performs the employee's Odoo work for them. Guidance highlights and verifies; the employee acts.
