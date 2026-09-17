# BUILD STATUS & PHASE PLAN — from here to a shippable product

> Status: Living · Created 2026-09-17 · Owner: Winston (founder/engineer)
>
> **What this document is.** [BUILD-ORDER.md](BUILD-ORDER.md) says what the
> phases *should* be. [00-current-state.md](00-current-state.md) captured the
> ERP baseline on 2026-09-15. Neither says *where the build actually is today*
> or what the remaining path looks like given the decisions we've since made in
> code (notably: the desktop app was built straight onto Odoo, not onto the
> planned Platform backend).
>
> This document is the single place that answers: **what is actually done, what
> is claimed-but-unverified, what is left, and in what order we finish it.**
> It supersedes nothing — it reconciles BUILD-ORDER's plan with the repository
> as it stands, and re-sequences the rest.
>
> **Keep it updated.** Every phase below has checkboxes. Tick them as work
> lands; don't create a second status doc.

Every factual claim below is tagged:
**[V-code]** verified by reading this repository at commit `4ab7400` ·
**[V-git]** verified against git history/refs ·
**[Claimed]** asserted in a repo doc but not independently verifiable here ·
**[Assumption]** needs a human to confirm.

---

## 1. Executive summary — where we are

We have **a working desktop pilot shell and a reasonably deep Odoo ERP**, and
**none of the DeployGuard Platform** the planning docs are written around.

The desktop app is real and demoable: it embeds Odoo, authenticates on Odoo's
own login page, carries DogForce branding, has a persistent toolbar, a command
palette, and one genuinely functional Platform-style feature (My Work, backed by
the new `security_work` Odoo module). That is roughly **BUILD-ORDER P2's user
experience, delivered without P0 or P1 underneath it** — a deliberate shortcut,
documented honestly in [`desktop/DEVIATIONS.md`](../../desktop/DEVIATIONS.md).

The cost of that shortcut is that everything downstream of P1 (training,
adoption, exceptions, digests, offline, notifications, multi-tenancy) has **no
foundation to be built on yet**, and the one piece that would give it a
foundation — `security_deployguard_bridge` — is **reported complete but does not
exist in this repository or in any git ref** (§4.1).

Two things are also true that no amount of feature work fixes: **production
credentials are still committed in this repo** (§4.2), and **CI has never
successfully run** (§4.3). Both are pilot blockers, not tidy-up items.

### 1.1 Phase status at a glance

| Phase (BUILD-ORDER) | Planned scope | Actual status |
|---|---|---|
| **P0** Foundations | Platform DB, tenancy/RLS, events, audit, Fastify API, worker, `packages/ui`, IaC, CI | ⬜ **Not started.** No Platform backend, no TypeScript API/worker, no `packages/ui`, no tenancy model. `packages/ai` (AIProvider + Gemini + validator) is the only `packages/*` that exists. [V-code] |
| **P1** Odoo bridge & identity | `security_deployguard_bridge`, projections, auth exchange, webhooks | 🟥 **Reported done (T-8, T-10), not in the repo.** §4.1. Prerequisite refactor T-5 (bus subscriber registry) *is* in `security_base`. [V-git] |
| **P2** Desktop shell, single login, notifications | Full shell, device registration, SSO, notifications, updater, offline-capable client | 🟨 **~55% as a pilot slice.** Shell + single login + My Work + branding + diagnostics done. No device identity, no revocation, no notifications, updater disabled, no signed installer. §3.1 |
| **P3** Training | LMS: courses, lessons, assessments, competencies | ⬜ **Not started.** No models, no screens. [V-code] |
| **P4** Work management | Templates, recurrence, checklist runner, verification, auto-complete, offline | 🟨 **~30%.** `security_work` gives task + checklist primitives and a working desktop runner. No recurrence, no auto-complete from ERP events, no evidence capture, no offline. §3.2 |
| **P5** Adoption engine | Expected work, scoring, explanations, abandonment, check-ins | ⬜ **Not started.** |
| **P6** Exceptions & inbox | Rules, lifecycle, escalations, manager inbox | 🟨 **Adjacent primitives only.** `security_notifications` produces deterministic alerts (roster gaps, missed check-ins, expiries) and `security_shell`'s home "attention" payload exists — neither is the exception engine. [V-code] |
| **P7** Feedback & support | Feedback, support queue, knowledge base | 🟨 **Seed only.** `security_help` articles + portal feedback exist in ERP. |
| **P8** Owner view & digests | Rollups, weekly digest, analytics | ⬜ **Not started** (ERP reporting ≠ adoption analytics). |
| **P9** AI (V1) | Capabilities, citations, budgets, evals | 🟨 **Infrastructure only, deliberately.** `packages/ai` (AIProvider, Gemini, output validator) and `security_ai_engine` exist; no MVP-facing AI, which is correct per [28](28-mvp-scope.md) §3.1. |
| **P10** Pilot hardening | Security review, perf gates, signing, runbooks, restore drill, a11y | ⬜ **Not started**, and partly *blocked* (§4.2–4.3). |

---

## 2. The strategic decision this plan hangs on

**Read this before the phase plan; it changes the size of everything after
Phase 2.**

BUILD-ORDER assumes a **separate DeployGuard Platform**: its own PostgreSQL with
row-level security, a Fastify API, a worker, an event store, its own tenancy —
with Odoo as an upstream system of record reached through a bridge addon.
That is the right architecture for a multi-tenant SaaS sold to many security
firms. It is also, realistically, **8–12 weeks of foundation work (P0+P1) before
a single new user-facing feature ships**, for one engineer.

What we actually built instead, under live testing pressure, is the opposite:
the desktop app talks to Odoo directly via `call_kw`, and the first Platform
feature (My Work) was implemented as **an Odoo module** (`security_work`) rather
than a Platform service. That worked — it shipped in days, not weeks.

So there is a fork, and it should be chosen deliberately rather than drifted
into:

| | **Track A — Odoo-native (recommended for now)** | **Track B — build the Platform (BUILD-ORDER as written)** |
|---|---|---|
| Where new features live | New `security_*` addons; desktop is a client | New Fastify/Postgres services behind `/v1/*` |
| Time to next user-visible feature | Days | Weeks (after P0+P1) |
| Multi-tenancy | One Odoo DB per client (today's model) | RLS, one Platform, many tenants |
| Adoption analytics | Harder — must not pollute the ERP schema; needs its own module and care | Natural — it's the Platform's purpose |
| Offline/evidence sync | Must be built on Odoo's API; no command outbox exists | Designed for it ([20](20-offline-strategy.md)) |
| Risk | Couples the product to Odoo; later extraction costs real money | Long stretch with nothing shippable; classic founder death march |

**Recommendation:** stay on **Track A through the pilot** (Phases 1–4 below),
with two hard constraints that keep Track B reachable:

1. **The bridge addon still gets built** (Phase 2). It is the seam. Whether the
   consumer is a future Platform or today's desktop app, a signed, versioned,
   allowlisted facade over Odoo is the thing that makes extraction possible
   later and is worth building now.
2. **New Platform-domain data models stay in their own addons** (`security_work`,
   `security_training`, `security_adoption`), never bolted onto ERP models via
   `_inherit`. Extraction later is then a data migration, not a rewrite.

Re-evaluate at the end of the pilot (Phase 8), when there is a second paying
client in sight or a real multi-tenancy requirement — whichever comes first.

> **Decision needed from you.** If you'd rather go Track B, Phases 2–6 below get
> re-cut around P0/P1 as BUILD-ORDER writes them, and the pilot moves out by
> roughly two months. Everything in Phase 0 and Phase 1 is required either way,
> so that work starts now regardless.

---

## 3. Audit — what actually exists

### 3.1 Desktop app (`desktop/`) — the pilot shell

**Stack** [V-code]: Tauri v2 (`unstable` multi-webview) + Rust 2021 + React 18 +
TypeScript 5.6 + Vite 5 + Vitest 1.6. ~2,550 lines across Rust and TS.
Bundle targets NSIS + MSI, `identifier com.deployguard.desktop`, product name
"DogForce Security Services", version 0.1.0.

**Done:**

- [x] Two sibling webviews in one window: `odoo` (the whole app surface) and
      `shell` (DeployGuard chrome). Odoo has **zero IPC capability** — scoped by
      `"webviews": ["shell"]` in `capabilities/main.json`, correctly by webview
      rather than by window. This is the security property the architecture
      asked for and it is implemented properly. [V-code]
- [x] Single login on Odoo's own `/web/login`; Rust reads the resulting
      `session_id` cookie back and calls `get_session_info`. No password ever
      touches our code. Persistence is the webview's own cookie jar. [V-code]
- [x] Custom title bar + persistent toolbar: real Odoo Back/Forward/Reload
      (via `Webview::eval` of `history.*`), Home, minimize/maximize/close,
      connection status, user name + cached Odoo avatar. [V-code]
- [x] Full-window app view with left nav (Home, My Work & Sweeps) and honest
      "Coming soon" entries for Training and Adoption — no fake data anywhere.
      [V-code]
- [x] Command palette (⌘K) covering navigation, Odoo history, window controls,
      sign out. [V-code]
- [x] **My Work**: real feature end-to-end — lists `security.work.task` rows for
      the signed-in user's employee, task detail, state-machine actions
      (start/submit/could-not-complete/cancel), checklist runner writing
      `security.work.checklist.response`, `cnc_reason` options read from
      `fields_get` rather than hardcoded. Goes through a single generic
      `odoo_call_kw` Rust command — no bespoke endpoint, no elevated access.
      [V-code]
- [x] Honest connectivity reporting (`connectivity.rs`), non-sensitive
      diagnostics bundle (`diagnostics.rs`), error extraction with fallbacks.
- [x] Design-token parity: `ds.css` / `dgs.css` are verbatim ports of
      `security_base` / `security_shell` tokens per DG-ADR-017. [V-code]
- [x] DogForce branding, real logo assets, generated app icons. [V-git]
- [x] Tests: Rust unit tests for `odoo::is_unauthenticated_path`,
      `config::odoo_base_url`, `windowing::shell_bounds`/`odoo_bounds`;
      Vitest for `extractErrorMessage`, `config/env`, `avatarCache`,
      `myWork.logic`. Reported ~25 Rust + ~28 frontend cases. [Claimed / V-code
      for file existence]
- [x] A macOS→Windows cross-compile fallback (`scripts/build-windows-xcompile.sh`,
      cargo-xwin) producing a **portable .exe, not an installer**. [V-code]

**Not done (the honest gap list):**

- [ ] **No signed installer.** `updater.active: false`, empty `pubkey`, no
      certificate. Windows SmartScreen will warn every pilot user. (D-5, OQ-7)
- [ ] **No device identity, no remote revocation.** (D-3; PR-IAM-05/10)
- [ ] **No notifications** — the plugin is a dependency, nothing is wired. (D-6)
- [ ] **No offline anything** — no SQLite/SQLCipher store, no command outbox.
      The app needs connectivity to do anything. (D-4)
- [ ] **No crash/error telemetry** — Sentry is in the architecture doc
      ([17](17-desktop-architecture.md)), absent from `Cargo.toml` and
      `package.json`.
- [ ] **No first-run experience** beyond "here's Odoo's login page" — no company
      code / tenant discovery, no monitoring-notice acknowledgement (PR-IAM-11,
      required before adoption measurement is lawful under [16](16-security-architecture.md)).
- [ ] **Accessibility findings open**: focus ring contrast ≈1.4:1 against 3:1
      required, "Coming soon" chip ≈2.2:1 against 4.5:1 required. Partly fixed in
      the hover-handle era, **needs re-auditing against the current toolbar**.
      ([`desktop/AGENT-FINDINGS.md`](../../desktop/AGENT-FINDINGS.md))
- [ ] **No manual test pass on real Windows** — the pre-pilot checklist in
      `desktop/README.md` has 6 unticked manual items.
- [ ] `desktop/README.md` is **stale**: it says cross-compiling from macOS isn't
      supported, but `scripts/build-windows-xcompile.sh` now does exactly that
      (commit `4ab7400`). [V-code]

### 3.2 Odoo ERP (`custom_addons/`) — 52 modules

37 installed in production per [00-current-state.md](00-current-state.md);
Odoo 19.0 Community throughout (`CLAUDE.md`'s "Odoo 17" is still wrong [V-code]).

**Landed since the baseline audit:** [V-git]

- [x] `security_work` — BUILD-ORDER P4 primitives: `security.work.task` (state
      machine open → in_progress → submitted → verified, with
      could_not_complete / rejected / cancelled), checklist template + typed item
      defs (boolean/text/number/photo) + responses, `mail.thread` tracking,
      ACLs, and **two record rules** (own tasks for `base.group_user`, all for
      `group_work_supervisor`). Tested locally, **not installed on production**.
      [V-code]
- [x] `security.bus.subscriber` mixin registry replacing the hardcoded 5-bridge
      dispatch list (defect D-4 closed; mobile + portal bridges now actually
      receive events). [Claimed, per cowork README T-5]
- [x] AI defaults moved to Gemini, `gemini-3.8-flash` primary /
      `gemini-3.6-flash` fallback (D-1). [Claimed]
- [x] Certification scan model-name fix (D-3). [Claimed]
- [x] `security_suite` removed as the install baseline; explicit per-client
      module list including `security_shell` (T-6). [Claimed]
- [x] Two new modules from the merged branch: `security_armed_response`,
      `security_telephony` — **installed nowhere yet**. [V-code]

**Gaps relative to the Platform vision:** no training/LMS models, no
competencies, no recurrence/schedule rules, no adoption or usage measurement,
no tenant model, no API tokens/OAuth, no exception rule engine.

### 3.3 Platform backend — does not exist

No Fastify app, no Platform PostgreSQL, no worker, no pg-boss, no `packages/ui`,
no `packages/domain`, no Terraform. [V-code] The only `packages/*` member is
`packages/ai` (AIProvider interface, Gemini provider, output validator, tests,
smoke-test script) — genuinely useful, and correctly ahead of its phase since
[29](29-roadmap.md) §3 says the interface ships in MVP while the features don't.

### 3.4 Mobile (`mobile/`) — Expo app, separate track

Functional guard/supervisor app against `security_mobile`'s REST API, with
offline queue and PIN lock. **Carries three of the six open security findings**
(S-4 public unrate-limited PIN login, S-5 fabricated HTTP 200 for queued writes —
both still present [V-code]) and does not follow the design system. It is out of
the desktop critical path but **in the pilot's blast radius** if it's in real use.

### 3.5 CI/CD and release

- `.github/workflows/ci.yml` — Odoo module install + tests + mobile typecheck.
- `.github/workflows/desktop-build.yml` — Windows NSIS/MSI via
  `tauri-apps/tauri-action`, statically reviewed, never successfully executed.
- `.github/workflows/fly-deploy.yml` — likely stale (`fly.toml` only on an old
  branch).
- **No workflow runs desktop tests on PRs** (`npm test` / `cargo test` are absent
  from `desktop-build.yml`; it runs typecheck + lint only). [V-code]
- **No workflow lints or tests `packages/ai`.** [V-code]
- Deployment is still rsync + container restart; `promote_staging_to_prod.sh`
  **does not roll back on failure**, contrary to two docs. [per 00-current-state]

### 3.6 Security posture — Stage 0 prerequisites

From [31-dogforce-rollout.md](31-dogforce-rollout.md) §2, as of today:

| # | Stage 0 item | Status |
|---|---|---|
| 1 | Rotate + purge exposed credentials (S-1) | 🟥 **Not done.** `odoo.conf` in the repo root still contains a plaintext `admin_passwd` value and live Render PostgreSQL connection credentials (values deliberately not repeated here); the `Dockerfile` still `COPY`s it into the image. `CLAUDE.md` still lists the demo server root SSH, DB password and admin password in plaintext. [V-code] |
| 2 | Replace tokenised git remote (S-2) | [Assumption] — not verifiable from here. |
| 3 | HTTPS verified, nginx vs Caddy confirmed (OQ-16) | [Assumption] — desktop CI targets `https://dogforcesecurityservices.com`, which implies TLS works, but the proxy question is open. |
| 4 | Authenticate WhatsApp webhook, unpublish sidecar port (S-3) | 🟥 **Not done.** `/api/whatsapp/webhook` is still `auth="none"` with no signature check. [V-code] |
| 5 | Odoo users for all pilot staff (OQ-8) | [Assumption] — 4 internal users at baseline. |
| 6 | TOTP policy + enrolment (OQ-20) | ⬜ Open. |
| 7 | AI default → Gemini (D-1) | ✅ Done. [Claimed] |
| 8 | Per-client module baseline incl. `security_shell` | ✅ Done. [Claimed] |
| 9 | Certification scan model fix (D-3) | ✅ Done. [Claimed] |
| 10 | Restart/validate ERP staging | 🟥 Not done — staging containers exited ~4 weeks before the baseline audit; the xcompile script notes staging is localhost-only on the prod host, so **there is no staging a desktop build can point at**. [V-code] |
| 11 | Privacy/legal review of adoption monitoring (OQ-6) | ⬜ Open — **blocks Phase 5.** |
| 12 | Confirm pilot participants + machines | ⬜ Open. |

---

## 4. Blockers, ranked

### 4.1 🟥 P1 bridge work is reported complete but does not exist

[`docs/deployguard/cowork/README.md`](cowork/README.md) records T-8
(`security_deployguard_bridge` scaffold, config model, integration user, security
group, settings views) and T-10 (outbox with HMAC + exponential backoff, the
`security.deployguard.api` read facade, dispatch controllers, cron, "all tests
pass") as ✅ **Done**.

`custom_addons/security_deployguard_bridge` **does not exist** — not in the
working tree, not on `main`, not on any remote branch, and no commit in any ref
has ever added a file under that path. [V-git]

The same doubt attaches to T-1, T-2, T-5 and T-6, which are also marked Done by
the same agent; T-5's mixin is the one most worth verifying first, because
`security_work` and the bridge both depend on the bus registry design.

**Action (Phase 0):** get the work pushed, or treat it as unbuilt and rebuild it.
Until then, **assume P1 is at zero** for planning purposes. Do not schedule
anything that depends on the bridge.

### 4.2 🟥 Live production credentials are committed to this repository

`odoo.conf` (repo root, and baked into the Docker image) and `CLAUDE.md` contain
the Odoo master password, the Render PostgreSQL host/user/password, and demo SSH
root access. Anyone with repo access — or with any image built from this
Dockerfile — has them. Rotation is not optional and is not a Phase 8 item.

### 4.3 🟥 No CI has ever run — GitHub account billing lockout

Every workflow fails in ~3 seconds ("account is locked due to a billing issue"),
confirmed by a real triggered run (PR #1). This predates the desktop app and
blocks: the Windows installer pipeline, Odoo module test runs, and any future
PR gate. **Only a human can fix it, on the GitHub account.** Until then every
"tested" claim in this repo rests on someone's local machine.

### 4.4 🟨 No reachable staging environment

ERP staging is stopped and, per the xcompile script's own note, only listens on
`localhost:8070` on the production host. There is nowhere to test a desktop
build, a bridge addon, or a module upgrade before it touches production data.
This is the quiet one that turns a pilot into an incident.

### 4.5 🟨 The pilot's ERP inherits unfixed S-3/S-4/S-5

Unauthenticated WhatsApp webhook; public, unrate-limited mobile PIN login; a
mobile client that tells users a queued write succeeded. If the pilot includes
the mobile app or WhatsApp, these are in scope.

---

## 5. The plan — phases from here to completion

Phases are sequential where they must be and explicitly parallel where they can
be. Effort estimates assume **one engineer with AI assistance**, and are ranges,
not commitments. "Boring" work is listed as work, not assumed.

### Phase 0 — Truth, secrets, and a working pipeline · ~1 week · **blocking everything**

Nothing else is trustworthy until this is done.

| # | Work | Area | Done |
|---|---|---|---|
| 0.1 | Resolve the GitHub billing lockout; confirm by a green run of both workflows | Infra | ⬜ |
| 0.2 | Rotate the Odoo master password, the Render PostgreSQL password, and demo SSH credentials | Security | ⬜ |
| 0.3 | Remove `odoo.conf` from the repo and the image: template it (`odoo.conf.template` + env substitution in `entrypoint.sh`), `.gitignore` the real file, stop `COPY`ing secrets in `Dockerfile` | Security | ⬜ |
| 0.4 | Purge credentials from `CLAUDE.md`, `AGENTS.md`, `never_deploy.md`, `MOBILE_DEPLOYMENT_GUIDE.md`; replace with "see your password manager / 1Password vault" | Security | ⬜ |
| 0.5 | Scrub git history of the rotated secrets (`git filter-repo`) **or** accept and document that history is compromised and rotation is the only mitigation — decide explicitly | Security | ⬜ |
| 0.6 | Enable GitHub secret scanning + push protection on the repo | Security | ⬜ |
| 0.7 | Resolve §4.1: get Aegis's bridge/T-5/T-6 work pushed to a branch, or declare it unbuilt and reset the cowork board to reality | Process | ⬜ |
| 0.8 | Add `npm test` + `cargo test` to `desktop-build.yml`, and a `packages/ai` lint+test job to `ci.yml`; make both required checks on PRs to `main` | CI | ⬜ |
| 0.9 | Fix stale docs: `CLAUDE.md` Odoo 17 → 19; `desktop/README.md` cross-compile section; `API.md` endpoint coverage; `KNOWN_ISSUES.md` | Docs | ⬜ |
| 0.10 | Delete or fix `fly-deploy.yml` — a workflow that references a missing `fly.toml` is a trap | CI | ⬜ |

**Exit:** CI green on `main`; no secret in the repo or in a built image; the
cowork board matches the filesystem; desktop tests run automatically on PRs.

---

### Phase 1 — Ship the pilot desktop app for real · ~2–3 weeks · parallel with Phase 2 after 1.1

The app is demoable. It is not *installable by a non-engineer on a Windows
machine that isn't yours*. That gap is this phase.

| # | Work | Area | Done |
|---|---|---|---|
| 1.1 | Stand up a reachable **staging Odoo** (public hostname + TLS, or a WireGuard/Tailscale-reachable host) with a sanitised copy of production data — prerequisite for every test below | Infra | ⬜ |
| 1.2 | Windows code signing: obtain an OV/EV certificate or enrol in Azure Trusted Signing (lead time — start on day one) | Release | ⬜ |
| 1.3 | Wire signing into `desktop-build.yml`; produce a signed NSIS + MSI from CI | Release | ⬜ |
| 1.4 | Generate a Tauri updater keypair, publish a static update manifest (same CDN/host as installers), set `pubkey`, flip `updater.active: true`; **test an N → N+1 update on a clean VM** | Release | ⬜ |
| 1.5 | Crash + error telemetry: Sentry (Rust + JS) with PII scrubbing; verify no session cookie, token or employee name reaches it | Observability | ⬜ |
| 1.6 | Structured logging to a rotating local file + a "copy diagnostics" button that produces the bundle a support ticket needs | Observability | ⬜ |
| 1.7 | Re-run the WCAG audit against the current toolbar/app-view; fix focus-ring contrast, chip contrast, and Escape-returns-focus; add an automated axe pass to CI | A11y | ⬜ |
| 1.8 | Complete the manual pre-pilot checklist in `desktop/README.md` on a **clean Windows VM** (install, sign in, relaunch persistence, sign out, offline behaviour, resize to 1024×700, full keyboard nav, uninstall) | QA | ⬜ |
| 1.9 | First-run experience: monitoring notice + acknowledgement (PR-IAM-11 — required before adoption data is collected), and a plain-language "what this app is" screen | Product | ⬜ |
| 1.10 | Session lifecycle honesty: detect Odoo session expiry and surface it (today an expired cookie likely reads as a generic error) | Desktop | ⬜ |
| 1.11 | Installer hygiene: per-user install, clean uninstall, no orphaned data, correct product/publisher metadata, versioning scheme decided (`0.x.y-pilot` → `1.0.0`) | Release | ⬜ |
| 1.12 | Pilot runbook: how to install, how to report a problem, how we push an update, what we do when a machine breaks | Docs | ⬜ |

**Exit:** a named non-engineer installs the signed app on their own Windows
machine unaided, signs in with their Odoo credentials, completes a task in My
Work, and receives a pushed update without reinstalling.

---

### Phase 2 — The bridge addon (P1, for real) · ~3–4 weeks

The seam between DeployGuard and the ERP. Build it even on Track A: it is what
makes the desktop app stop being "a browser pointed at Odoo," and it is the
precondition for extraction later.

| # | Work | Area | Done |
|---|---|---|---|
| 2.1 | Verify or rebuild `security_deployguard_bridge` core: config singleton (Platform URL, tenant id, write-only webhook secret, signing keypair, health fields), `group_deployguard_integration`, dedicated integration user, settings UI restricted to `base.group_system` | ERP | ⬜ |
| 2.2 | Secrets at rest: webhook secret and signing private key encrypted per [16](16-security-architecture.md) §6 — never plaintext in `ir.config_parameter`, logs, or fixtures | Security | ⬜ |
| 2.3 | `security.deployguard.outbox`: event id, type, payload, state, attempts, next attempt; HMAC-SHA256 signing; exponential backoff; 1-minute dispatch cron that logs clearly when no consumer exists | ERP | ⬜ |
| 2.4 | `security.deployguard.api` read facade — `ping`, `get_sites`, `get_employees`, `get_users` — strictly to the field allowlists in [12](12-odoo-integration.md) §3. No "just in case" fields | ERP | ⬜ |
| 2.5 | **Auth endpoints (T-9, security-critical)**: `auth/login` (no persisted web session; mints a short-lived signed JWS assertion), `auth/totp`, `sso/ticket` (single-use, ≤60s, refuses `base.group_system` and anyone without the DeployGuard access flag), `sso/consume`. Rate-limited by account, IP and device | Security | ⬜ |
| 2.6 | `HttpCase` coverage for 2.5: valid login, wrong password, TOTP required, ticket single-use, ticket expiry, admin refusal, replay, clock skew | Test | ⬜ |
| 2.7 | Domain bridge `security_deployguard_attendance` as the template: outbox events on batch create/submit/review/lock + `get_attendance_batches` / `get_attendance_summary` | ERP | ⬜ |
| 2.8 | Integration health: last successful sync, queue depth, failure count, exposed both in Odoo and to the desktop app | Observability | ⬜ |
| 2.9 | Desktop: replace raw `odoo_call_kw` for My Work with facade calls where a facade method exists; keep `call_kw` as the explicit escape hatch it is | Desktop | ⬜ |
| 2.10 | Contract tests against a real Odoo 19 container in CI (signature, replay, skew, throttling, idempotency) | Test | ⬜ |
| 2.11 | Install and validate the bridge on **staging only**; production install is a separate, later decision | Deploy | ⬜ |

**Exit:** the desktop app authenticates through the bridge, not by reading a
cookie; an attendance batch posted in Odoo produces a signed, verifiable outbox
delivery; killing the consumer for an hour self-heals; every endpoint has a
negative test.

---

### Phase 3 — Work management, finished · ~3–4 weeks

`security_work` is a third of P4. This is the rest, and it's the phase that makes
the product *do something no ERP screen already does*.

| # | Work | Area | Done |
|---|---|---|---|
| 3.1 | `security.work.schedule.rule`: recurrence materialisation over a rolling 7-day horizon (calendar, shift-based, site-event based), idempotent, with roster-change reconciliation | ERP | ⬜ |
| 3.2 | Auto-completion rules: subscribe to the bus (`attendance.*`, `incident.*`) and auto-verify or auto-close matching tasks, with the matched fact recorded as evidence | ERP | ⬜ |
| 3.3 | The three MVP templates — `attendance.post`, `site.visit`, `incident.review` — as data, not code | Config | ⬜ |
| 3.4 | Evidence capture: photo/file attachments on checklist responses, size limits, compression, `ir.attachment` storage policy, retention | ERP | ⬜ |
| 3.5 | Verification queue: supervisor view of submitted work, verify/reject with reason, notification to the assignee | ERP + Desktop | ⬜ |
| 3.6 | Overdue sweeps + escalation hooks (feeding Phase 6) | ERP | ⬜ |
| 3.7 | Desktop: evidence capture UI, verify queue screen, task detail polish, all required empty/error/loading/offline states per [05](05-ux-principles.md) §6 | Desktop | ⬜ |
| 3.8 | **Offline foundation**: SQLCipher local store + command outbox in Rust; queued actions are shown as *queued*, never as succeeded (this is S-5's lesson — do not repeat the mobile app's mistake) | Desktop | ⬜ |
| 3.9 | Conflict handling for every row in [20](20-offline-strategy.md) §5; airplane-mode soak test | Desktop + Test | ⬜ |
| 3.10 | Record-rule review: `security_work` currently gives every `base.group_user` read+write on tasks, narrowed by one record rule. Audit that the rule holds for `write` as well as `read`, and add rules to the checklist/response models (which have none) | Security | ⬜ |
| 3.11 | Data retention + purge policy for evidence attachments | Compliance | ⬜ |

**Exit:** a real week of DogForce roster data generates the right tasks; posting
an attendance batch in Odoo auto-completes the expected item within two minutes;
an offline checklist syncs on reconnect and never shows a false success.

---

### Phase 4 — Training core · ~3–4 weeks · needs content from the ops manager (OQ-19)

| # | Work | Area | Done |
|---|---|---|---|
| 4.1 | `security_training` addon: program, course, **course version**, section, lesson, assessment, question bank | ERP | ⬜ |
| 4.2 | Assignment + progress: `training_assignment`, `lesson_progress`, `attempt`, `attempt_answer`, with version pinning (a publish must not change an in-flight assignment) | ERP | ⬜ |
| 4.3 | Competencies + evidence, linked to existing `security.employee.certification` records rather than duplicating them | ERP | ⬜ |
| 4.4 | Authoring workflow: draft → review → publish, with a named approver | ERP | ⬜ |
| 4.5 | Desktop: My Training, lesson player, assessment runner with feedback, practical sign-off | Desktop | ⬜ |
| 4.6 | The DogForce course pack — start with 3 courses, not 8 | Content | ⬜ |
| 4.7 | Tests: version pinning, pass/fail paths, attempt limits, authoring permissions | Test | ⬜ |

**Exit:** three courses authored, approved and assigned; a supervisor completes
one end-to-end; a practical sign-off produces competency evidence linked to a
real record.

---

### Phase 5 — Adoption engine · ~3–4 weeks · **gated on privacy sign-off (OQ-6)**

Do not start 5.2 onwards until the privacy/legal review and the
employment-contract notice exist. Measuring people without that is a legal
problem, not a feature.

| # | Work | Area | Done |
|---|---|---|---|
| 5.1 | Privacy/legal review + employee notice + the in-app monitoring acknowledgement from 1.9 | Compliance | ⬜ |
| 5.2 | Expected Work Model for the 5 MVP workflows; baseline computed from ERP history so we can prove before/after | ERP | ⬜ |
| 5.3 | Nightly scoring per tenant timezone, with score factors stored (never a bare number) | ERP | ⬜ |
| 5.4 | Excusals: leave, absence, roster change, and **platform fault** — with retroactive restoration when a fault is resolved | ERP | ⬜ |
| 5.5 | Confidence gating: no score below 5 items; say "not enough data", never a misleading 0% | ERP | ⬜ |
| 5.6 | Abandonment detection + assistance check-in ("help before blame" framing per [31](31-dogforce-rollout.md) §6) | ERP | ⬜ |
| 5.7 | Desktop: adoption overview, the explanation screen (every score drillable to the events behind it), own-score view | Desktop | ⬜ |
| 5.8 | Fixture-month tests producing exact expected snapshots | Test | ⬜ |

**Exit:** every score on screen explains itself down to individual events and
missing items; a resolved platform fault visibly restores prior scores.

---

### Phase 6 — Exceptions, inbox, notifications · ~3–4 weeks

| # | Work | Area | Done |
|---|---|---|---|
| 6.1 | Exception rule engine: rules, instances, evidence, timeline, dedupe, auto-resolve, pause-on-stale-data | ERP | ⬜ |
| 6.2 | Ingest rather than re-derive: consume `security_notifications`' existing deterministic alerts (roster gaps, missed check-ins, expiries) instead of writing second versions of them | ERP | ⬜ |
| 6.3 | Escalation policies against a working calendar; acknowledging cancels escalation | ERP | ⬜ |
| 6.4 | Manager inbox (Critical / Attention / Watch) with keyboard triage; scoped supervisor inbox | Desktop | ⬜ |
| 6.5 | Notification delivery: in-app, desktop OS notifications (wire `tauri-plugin-notification` at last), email; preferences, quiet hours, digests | Desktop + ERP | ⬜ |
| 6.6 | Email provider decision + deliverability setup — SPF/DKIM/DMARC (OQ-10) | Infra | ⬜ |
| 6.7 | Per-rule positive/negative fixtures; escalation timing tests | Test | ⬜ |

**Exit:** a missing night supervisor raises Critical within two minutes and
escalates on schedule; acknowledging stops it; the inbox is empty when nothing
needs a human.

---

### Phase 7 — Feedback, support, and the owner view · ~2–3 weeks

| # | Work | Area | Done |
|---|---|---|---|
| 7.1 | "Something's wrong" with auto-captured context (route, task, version, recent errors) and redaction | Desktop + ERP | ⬜ |
| 7.2 | Support queue with SLA timers; `platform_fault` resolution propagates to adoption excusal (closes the loop with 5.4) | ERP | ⬜ |
| 7.3 | Knowledge base seeded from `security_help`, targeted by route/workflow; contextual help panel | ERP + Desktop | ⬜ |
| 7.4 | Post-task feedback capture | Desktop | ⬜ |
| 7.5 | Owner overview tiles + weekly deterministic digest, with every number drillable | ERP + Desktop | ⬜ |
| 7.6 | Metric definitions documented and asserted in tests — the digest and the drill-down must agree exactly | Test + Docs | ⬜ |

**Exit:** a blocked supervisor reports a problem in under 20 seconds with full
context; resolving it as a fault restores their coverage figures.

---

### Phase 8 — Pilot hardening and launch · ~2–3 weeks

The boring phase that decides whether the pilot is a success story or an
incident report.

| # | Work | Area | Done |
|---|---|---|---|
| 8.1 | Independent security review of the bridge auth path and the desktop session handling (external if budget allows; at minimum a structured self-review against [16](16-security-architecture.md)) | Security | ⬜ |
| 8.2 | Close S-3 (WhatsApp webhook HMAC + stop publishing the sidecar port) and S-4/S-5 if mobile is in pilot scope | Security | ⬜ |
| 8.3 | Backup + **restore drill**: restore production to a scratch host, time it, record the RTO actually achieved | Ops | ⬜ |
| 8.4 | Fix `promote_staging_to_prod.sh` to roll back on failure — today it doesn't, and two docs claim it does | Ops | ⬜ |
| 8.5 | Monitoring + alerting: Odoo health, container restarts, outbox queue depth, cron failures, disk, certificate expiry — alerting to a channel someone actually reads | Observability | ⬜ |
| 8.6 | Performance gates per [25](25-testing-strategy.md) §4 under realistic data volume | Test | ⬜ |
| 8.7 | Runbooks: incident response, rollback, "Odoo is down", "a pilot user is locked out", "we shipped a bad update" | Docs | ⬜ |
| 8.8 | Per-tenant data export tool (and deletion) — needed for the second client and for any data-subject request | ERP | ⬜ |
| 8.9 | Accessibility audit of the full app, not just the shell | A11y | ⬜ |
| 8.10 | Copy and content review — every error message, every empty state | Product | ⬜ |
| 8.11 | Pilot user training sessions; measure the before/after adoption baseline from 5.2 | Ops | ⬜ |
| 8.12 | Zero open P1 defects | QA | ⬜ |

**Exit:** all NFR gates met, restore drill completed within the stated RTO, no
open P1 defects, rollout Stage 2 can begin.

---

### Phase 9+ — after the pilot

- **P9 AI (V1):** capability configs, runs, insights with citations, budgets,
  eval sets that block merges on regression. `packages/ai` already gives us the
  provider abstraction and output validation — this is the cheapest phase
  relative to its perceived value, *because* we deferred it correctly.
- **Track A/B re-evaluation (§2):** with real pilot data and, hopefully, a second
  client in sight.
- **Multi-tenancy** — whichever way that decision goes.
- **Mobile convergence:** retrofit the design system, fix S-4/S-5 properly, and
  decide whether the Expo app becomes a Platform client or stays an ERP client.

---

## 6. Continuous tracks (not phases — every phase carries them)

1. **Tests are part of the work, not after it.** A phase's acceptance row is its
   definition of done. No phase ships without its tests green in CI.
2. **Every feature emits events and audit from day one** — never retrofitted.
3. **Every screen implements all required states** ([05](05-ux-principles.md) §6)
   before review: loading, empty, error, offline, permission-denied.
4. **Configuration over code.** If a "feature request" is really a new checklist
   or expectation, it ships as data.
5. **No secret in git, ever again.** Push protection on, secret scanning on.
6. **These docs stay current.** A phase that changes a decision updates the ADR
   and this file's checkboxes in the same change set.
7. **No fake data, no fabricated success.** The mobile app's queued-write HTTP
   200 (S-5) is the anti-pattern to keep pointing at.

---

## 7. Critical path, compressed

```
Phase 0 (secrets, CI, truth)          1 wk   ← blocking, start today
   ├── Phase 1 (ship the desktop)     2–3 wk ← needs staging (1.1) + cert lead time (1.2)
   └── Phase 2 (bridge addon)         3–4 wk ← can run parallel to Phase 1 after 1.1
Phase 3 (work mgmt finished)          3–4 wk ← needs Phase 2
Phase 4 (training)                    3–4 wk ← needs content; parallel with 3 if content is ready
Phase 5 (adoption)                    3–4 wk ← needs Phase 3 + privacy sign-off
Phase 6 (exceptions/inbox/notifs)     3–4 wk
Phase 7 (support + owner view)        2–3 wk
Phase 8 (pilot hardening)             2–3 wk
                                     ─────────
                          ≈ 20–28 weeks to pilot-ready on Track A
```

Three things buy time and are outside the code: **the GitHub billing fix**, the
**code-signing certificate** (start the application immediately — lead time is
the hidden critical path), and the **ops manager's course content**.

---

## 8. Change log

| Date | Change |
|---|---|
| 2026-09-17 | Created. Full audit of desktop, ERP, packages, CI and security posture against BUILD-ORDER; Track A/B decision framed; Phases 0–8 defined. |
