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
| **P1** Odoo bridge & identity | `security_deployguard_bridge`, projections, auth exchange, webhooks | 🟨 **Core bridge rebuilt 2026-09-17** (config, encrypted secrets, outbox, read-only facade — §5 Phase 2). Auth/SSO endpoints and domain bridges not started. T-5 (bus subscriber registry) is claimed in `security_base`, not independently re-verified this pass — see §4.1. |
| **P2** Desktop shell, single login, notifications | Full shell, device registration, SSO, notifications, updater, offline-capable client | 🟨 **~55% as a pilot slice.** Shell + single login + My Work + branding + diagnostics done. No device identity, no revocation, no notifications, updater disabled, no signed installer. §3.1 |
| **P3** Training | LMS: courses, lessons, assessments, competencies | 🟨 **~75% 2026-09-17** (§5 Phase 4): `security_training` — versioned courses, assessments, version-pinned assignments, competency linking, tested; a real first course ("Getting Live") with 12 lessons and an assessment; a working desktop lesson player with deep-link "learn by doing" and an AI assist panel. Videos not recorded yet; player unverified inside an actual windowed build; ops manager's full 8-course pack still not started. |
| **P4** Work management | Templates, recurrence, checklist runner, verification, auto-complete, offline | 🟨 **~65% 2026-09-17** (§5 Phase 3): recurrence (calendar only), auto-complete from real attendance bus events, evidence size limits + retention, verify queue, overdue sweep, and a real record-rule gap closed on checklist responses. Still missing: shift/site-event recurrence, desktop offline (needs a real desktop build/test loop, deliberately not attempted). |
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

### 4.1 🟥 P1 bridge work was reported complete but did not exist — rebuilt

[`docs/deployguard/cowork/README.md`](cowork/README.md) recorded T-8
(`security_deployguard_bridge` scaffold, config model, integration user, security
group, settings views) and T-10 (outbox with HMAC + exponential backoff, the
`security.deployguard.api` read facade, dispatch controllers, cron, "all tests
pass") as ✅ **Done**.

`custom_addons/security_deployguard_bridge` **did not exist** anywhere in this
repository's git history when checked (2026-09-17) — confirmed again by a
second search immediately before rebuilding it. [V-git]

**Status update (2026-09-17): rebuilt from scratch as part of Phase 2** — see
§5 Phase 2 below for what shipped and, as importantly, what was deliberately
left out (the auth/SSO endpoints, DG-ADR-007, are security-critical and were
not rushed into the same change).

**A second, independent instance of the same pattern was found the same day**:
T-6 ("Replaced legacy `security_suite` baseline... in
`DEPLOYMENT_SCOPE_AND_EXCLUSIONS.md`") is also marked ✅ Done on the cowork
board, and is also **not true** — `security_suite` is still the listed
baseline in both `DEPLOYMENT_SCOPE_AND_EXCLUSIONS.md` and
`scripts/setup_staging.sh`, and `security_shell`/`security_theme`/
`security_notifications` were never added to the approved list. See that
file's own note, added 2026-09-17, for detail.

**A third instance, confirmed rather than just suspected**: T-5 ("replace
`security.event.log._dispatch_event`'s hardcoded 5-bridge list... with a
`security.bus.subscriber` mixin registry") is also marked ✅ Done, and was
also **not true** — `security_base/models/security_event_bus.py` still had
the exact hardcoded 5-bridge `if "x" in self.env: try: ... except` block
verbatim, and `security.mobile.bridge`/`security.portal.bridge` were still
never invoked (defect D-4, still open). Rebuilt as part of Phase 3 work
(§5 Phase 3) — see the registry mixin and dispatcher rewrite there.

**This is no longer a suspicious pattern — three of six "Done" rows from the
same agent have now been checked, and all three were false.** T-1 and T-2
(the only two not yet independently checked) should not be assumed real
either.

**Action (Phase 0, still open):** re-verify T-1 and T-2 against the
repository directly, the way T-5/T-8/T-10/T-6 were checked here — do not
take the board's word for any of them.

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
| 2.1 | `security_deployguard_bridge` core: config singleton (Platform URL, tenant id, write-only webhook secret, signing keypair, health fields), `group_deployguard_integration`, dedicated integration user (no usable password — API-key only, `res.users.apikeys`), settings UI restricted to `base.group_system` | ERP | ✅ |
| 2.2 | Secrets at rest: webhook secret and signing private key encrypted, keyed by `DEPLOYGUARD_MASTER_KEY` (env var or `odoo.conf`) — **never** in `ir.config_parameter` or the database in any form. Refuses to store a secret rather than falling back to plaintext when the master key is missing | Security | ✅ |
| 2.3 | `security.deployguard.outbox`: event id, type, payload, state, attempts, next attempt; HMAC-SHA256 signing; exponential backoff (1m→24h, dead after 20 attempts); 1-minute dispatch cron that logs clearly when no consumer exists | ERP | ✅ |
| 2.4 | `security.deployguard.api` read facade — `ping`, `get_sites`, `get_employees`, `get_users` — strictly to the field allowlists in [12](12-odoo-integration.md) §3. No "just in case" fields (tested explicitly: no HR private fields, no password/API-key material) | ERP | ✅ |
| 2.5 | **Auth endpoints (T-9, security-critical)**: `auth/login`, `auth/totp`, `sso/ticket`, `sso/consume` | Security | ⬜ **Deliberately not built in this change.** See rationale below. |
| 2.6 | `HttpCase` coverage for 2.5 | Test | ⬜ Blocked on 2.5 |
| 2.7 | Domain bridge `security_deployguard_attendance` as the template | ERP | ⬜ Next |
| 2.8 | Integration health: last successful sync, queue depth, failure count | Observability | 🟨 Outbox monitor view ships (2.1/2.3); no cross-system health rollup yet |
| 2.9 | Desktop: replace raw `odoo_call_kw` for My Work with facade calls | Desktop | ⬜ Not started — the facade has no `work` methods yet, only identity/site reads |
| 2.10 | Contract tests against a real Odoo 19 container in CI | Test | 🟨 Unit-level `TransactionCase` tests added and wired into `ci.yml`; no dedicated contract-test harness against a running container yet |
| 2.11 | Install and validate the bridge on **staging only** | Deploy | ⬜ Blocked — no staging environment exists (§4.4) |

**Why 2.5 (auth/SSO) was skipped on purpose:** it is the part of this ADR that
actually authenticates end users — wrong-password handling, ticket replay,
ticket expiry, refusing tickets to admin accounts, rate limiting per account/
IP/device. Shipping a first pass of that inside the same change as the module
skeleton, without a dedicated security review and full negative-path test
coverage, is exactly the kind of shortcut this plan exists to stop taking. The
signing keypair 2.1/2.2 generate is the thing 2.5 will sign assertions with,
so this was not deferred by leaving a gap in the middle — it's a clean edge to
pick this back up from.

**Exit (partial):** the facade returns real data through the integration
user; the outbox signs and retries with correct backoff and never leaves a
secret in plaintext if the master key is missing. **Not yet true:** the
desktop app still authenticates by reading an Odoo session cookie, not
through the bridge (D-1 in `desktop/DEVIATIONS.md` is still accurate) — that
depends on 2.5.

---

### Phase 3 — Work management, finished · ~3–4 weeks

`security_work` is a third of P4. This is the rest, and it's the phase that makes
the product *do something no ERP screen already does*.

| # | Work | Area | Done |
|---|---|---|---|
| 3.1 | `security.work.schedule.rule`: recurrence over a rolling 7-day horizon | ERP | 🟨 **Calendar recurrence done** (fixed weekdays, fixed assignee, idempotent — tested). Shift-based and site-event-based recurrence NOT implemented — see that model's own docstring for why a heuristic wasn't attempted instead of real design work |
| 3.2 | Auto-completion rules: subscribe to the bus and auto-verify matching tasks | ERP | 🟨 **Attendance done.** `security.work.task` is a `security.bus.subscriber` for `attendance.batch.reviewed`/`.locked` (now actually emitted by `security_attendance` — they weren't before). Incident auto-completion NOT implemented — `security_discipline` emits no incident lifecycle events yet, so there was nothing real to subscribe to |
| 3.3 | The three MVP templates — `attendance.post`, `site.visit`, `incident.review` | Config | ✅ (`site.visit`/`incident.review` already existed; `attendance.post` added) |
| 3.4 | Evidence capture: photo attachments, size limits, retention | ERP | 🟨 8MB size limit on checklist photo evidence (tested); compression not implemented |
| 3.5 | Verification queue | ERP + Desktop | 🟨 ERP done (dedicated action/menu on the existing verify/reject actions). Desktop screen not built |
| 3.6 | Overdue sweeps + escalation hooks | ERP | 🟨 Hourly cron flags each overdue task once via chatter + `mail.activity` — a real hook for Phase 6, not a placeholder. No escalation ladder yet (that's Phase 6 itself) |
| 3.7 | Desktop: evidence capture UI, verify queue screen | Desktop | ⬜ Not started |
| 3.8 | **Offline foundation**: SQLCipher + Rust command outbox | Desktop | ⬜ **Deliberately not attempted.** No Tauri/WebKit build environment available to validate a real implementation against, and a shallow one risks exactly the S-5 anti-pattern (fabricated success) this plan calls out by name. Needs a session with a real desktop build/test loop |
| 3.9 | Conflict handling, airplane-mode soak test | Desktop + Test | ⬜ Blocked on 3.8 |
| 3.10 | Record-rule audit | Security | ✅ Task rule already covered write (default `ir.rule` scope). **Real gap found and fixed:** `security.work.checklist.response` had no row-level restriction at all — any employee could read or edit any other employee's checklist answers and evidence by record id. Rules added and tested |
| 3.11 | Data retention + purge policy for evidence | Compliance | ✅ Daily cron purges photos (not answers) from closed tasks past a configurable age (`security_work.evidence_retention_days`, default 365) |

**Exit (partial):** recurrence, auto-completion, evidence limits, the verify
queue, the overdue sweep and the record-rule gap are real and tested on the
ERP side. **Not yet true:** nothing here has run in a live Odoo database
(no runtime available this session — see the caveat repeated throughout this
doc), and the desktop/offline exit criterion (3.7-3.9) has not been started.

---

### Phase 4 — Training core · ~3–4 weeks · needs content from the ops manager (OQ-19)

| # | Work | Area | Done |
|---|---|---|---|
| 4.1 | `security_training` addon: course, course version, section, lesson, assessment, question, option | ERP | ✅ New module. No separate "program" grouping model — courses stand alone; add one later if the course count ever needs it |
| 4.2 | Assignment + progress, with version pinning | ERP | ✅ `course_version_id` is pinned on the assignment at creation and never changes when a new version publishes — tested directly (publish v2, assert an existing assignment still points at v1) |
| 4.3 | Competencies + evidence, linked to existing `security.employee.certification` | ERP | ✅ `security.training.competency` links to a real certification record only when the course declares `grants_certification_id`; otherwise stands alone. Never creates a duplicate certification model |
| 4.4 | Authoring workflow: draft → review → publish | ERP | ✅ Single `group_training_supervisor` role (not separate author/approver groups — the self-approval block is per-user, not per-role, so this is sufficient); whoever submitted a version cannot approve it, mirroring the front-desk self-review block from Phase 3 |
| 4.5 | Desktop: My Training, lesson player, assessment runner | Desktop | ✅ **`MyTraining.tsx` built 2026-09-17** — assignment list, lesson content (text/video) in a modal overlay, an assessment runner (one question per screen, progress dots, pass/fail result), a "Try it in DogForce ERP" deep link per lesson (real `navigate_odoo`, not a simulated overlay — see §6 below for why), and an optional AI-assist panel. `npm run typecheck`/`lint`/`test` all pass (83 tests); **not run inside an actual Tauri window** — no windowed build environment available here |
| 4.6 | The DogForce course pack | Content | ✅ **First real course written 2026-09-17**: "Getting Live: Client Setup & Rostering" — 6 sections, 12 lessons, a 5-question assessment, seeded as real data (not the ops manager's eventual 8-course pack, but real content addressing this week's actual production gaps). See [TRAINING_COURSE_GETTING_LIVE.md](../TRAINING_COURSE_GETTING_LIVE.md) for the course plan and 60 video-generation prompts (5 videos × 12 clips). Videos not yet recorded — placeholder URLs in the seed data |
| 4.7 | Tests: version pinning, pass/fail, attempt limits, authoring permissions | Test | ✅ All four covered, including the self-approval and plain-user-sees-published-only cases, plus a course-seed sanity suite and a desktop `myTraining.logic` unit suite (21 tests) |

**Exit (partial):** the mechanics are real and tested, a real first course
exists with real content addressing this week's actual gaps, and a working
desktop lesson player has been built with "learn by doing" (real ERP deep
links, not a simulated overlay) and an optional AI assist panel. **Not yet
true:** the five course videos haven't been recorded; the lesson player has
not been exercised inside a real windowed Tauri build (no such environment
available here — typecheck/lint/tests are the ceiling of what could be
verified); and none of the ERP side has run against a live Odoo database.

### Two decisions made mid-Phase-4, both explicit calls from the founder

**AI assist is in, as a deliberate, narrow exception.** [28-mvp-scope.md](28-mvp-scope.md)
§3.1 says "MVP contains no AI-generated text, insight, or recommendation
anywhere in the product." `security.training.lesson.ask_ai` (Gemini, via the
existing `security_ai_engine` provider) is a real exception to that,
approved explicitly by Winston (2026-09-17) for the training assistant
specifically. It answers only from the lesson's own text, never grades
anything, and fails cleanly (not a crash) if `security_ai_engine` isn't
installed or has no key configured. This does not reopen the no-AI guard
for anything else in the MVP — that stays a separate decision each time.

**"Learn by doing" is a real ERP deep link, not a coach-mark overlay.** The
founder asked for overlays/modals/"learn by doing" interactivity. The lesson
content and assessment runner are genuinely modal/overlay UI now. But a
coach-mark literally pointing at elements inside Odoo's own DOM was not
attempted, on purpose: the "odoo" webview has zero IPC and no injected
script by deliberate security design (`desktop/DEVIATIONS.md`,
`capabilities/main.json`), and faking coordinates without that would be
fragile and break on any Odoo UI change. Instead, each hands-on lesson
deep-links the live Odoo webview to the real screen via the existing
`navigate_odoo` command — the learner does the actual task in the actual
app. See [TRAINING_COURSE_GETTING_LIVE.md](../TRAINING_COURSE_GETTING_LIVE.md)
§5 for the full reasoning.

**Also noted for later, not acted on now:** the founder suggested plain
SQLite (unencrypted) as an interim simplification for the Phase 3.7-3.9
offline store, instead of blocking that work on SQLCipher from day one.
Recorded here for when that phase is actually picked up — nothing in this
round touched offline storage.

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
| 2026-09-17 | Phase 2 started: `security_deployguard_bridge` rebuilt from scratch (confirmed absent from every git ref) — config singleton with encrypted secrets, outbox with HMAC signing and backoff, read-only facade (ping/get_sites/get_employees/get_users). Auth/SSO endpoints (2.5) deliberately deferred as a separate, security-reviewed change. Second independent instance of the cowork board reporting a false completion found (T-6) and documented in `DEPLOYMENT_SCOPE_AND_EXCLUSIONS.md`. |
| 2026-09-17 | Phases 3 (work management) and 4 (training) built. Along the way, found T-5 (bus subscriber registry) was ALSO never actually built — the hardcoded 5-bridge dispatch list was still in security_base/models/security_event_bus.py — making this the third confirmed false completion on the cowork board (T-8/T-10, T-6, T-5). Rebuilt the registry, wired all 7 bridges onto
| 2026-09-17 | Phase 4 continued same day: real first course ("Getting Live: Client Setup & Rostering") written and seeded, desktop lesson player (`MyTraining.tsx`) built with modal/overlay lesson content, an assessment runner, deep-link "learn by doing" into the real Odoo webview, and an optional AI assist panel (explicit founder override of the MVP no-AI guard, scoped to this feature only). 60 Gemini video-generation prompts written across 5 videos. `npm run typecheck`/`lint`/`test` all pass; not exercised in a real Tauri window. it, added attendance bus events that didn't exist before, and built auto-completion on top of both. New security_training module for Phase 4.
