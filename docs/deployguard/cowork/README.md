# Aegis Co-working Space

Welcome to the collaborative workspace for the **DeployGuard OS** rollout. 

I am **Aegis**, your dedicated AI Co-developer and Operations Sentinel. I specialize in backend logic, API integration, styling compliance, and rigorous testing across the Odoo custom addons ecosystem.

This directory serves as our central hub for tracking, coordinating, and executing development tasks.

---

## 🚨 Urgent correction #2 — target is now `gemini-3.8-flash`, not `gemini-3.6-flash`

**2026-09-16 (later same day), Claude.** Winston has confirmed we're
standardizing on **`gemini-3.8-flash` as the primary/default model**,
with `gemini-3.6-flash` kept as an explicit cheaper fallback tier (not
a silent default). I live-tested both against the real API just now —
**both respond successfully**, no deprecation error on either.

**If you haven't started T-1 yet, or are still mid-edit:** set the
default to `gemini-3.8-flash`, not `gemini-3.6-flash` (superseding the
correction below). If you already finished T-1 with `gemini-3.6-flash`
as the default, that's not wrong today (it's a live model) but please
do a quick follow-up pass to change the *default* to `gemini-3.8-flash`
— leave `gemini-3.6-flash` selectable as a fallback tier, don't remove
it.

---

## 🚨 Urgent correction #1 — `gemini-2.5-flash` is deprecated (superseded above — read #2 first)

**2026-09-16, Claude.** T-1 asked for `gemini-2.5-flash` as the default
model. That was correct when I proposed it but **is now wrong**: a real,
live call to the Gemini API today (verified via `packages/ai/scripts/
smoke-test.ts`, not a guess) returned:

> `404 Not Found: This model models/gemini-2.5-flash is no longer
> available to new users. Please update your code to use
> models/gemini-3.6-flash for the latest features and improvements.`

I found `gemini-2.5-flash` already set as the default in
`security_ai_engine/providers/gemini.py`, `models/security_ai_config.py`
(x2, including the help text), `models/security_ai_engine.py`'s pricing
table, and `controllers/chat_controller.py`'s fallback — please update
**all of these** to `gemini-3.8-flash` (see correction #2 above — the
target moved again since this note was first written). If
`security_ai_engine.py`'s pricing table needs real prices for
`gemini-3.8-flash`/`gemini-3.6-flash` rather than reusing the old
`gemini-2.5-flash` numbers, flag that here rather than guessing — I
don't have pricing data from the smoke tests, only that the model names
changed and both respond live.

Also worth a quick check while you're in there: confirm none of the
other model name strings in that module (fallback providers, cached
model lists, etc.) reference other now-retired model ids — I only
verified `gemini-3.6-flash` specifically, not a full model-catalog sweep.

---

## About Aegis

* **Primary Stack Expertise:** Odoo 19 Community, Python (`TransactionCase` & `HttpCase`), PostgreSQL, OWL 2, Vanilla CSS custom properties.
* **Core Mission:** Help bridge the gap between Odoo ERP features and real-world adoption by building clean, robust, and verified modules.
* **Guiding Philosophy:** 
  1. *Test Everything:* Validation is the only path to finality.
  2. *Security First:* Zero-tolerance for plaintext secrets or credential exposure.
  3. *Cohesive Styling:* Every view must strictly adhere to the `--ds-*` and `--dgs-*` token architecture.

---

## Active Task Queue

Aegis (Gemini CLI, this file) works the **DeployGuard ERP / Odoo side**.
Claude works the **DeployGuard Platform desktop app** (`desktop/`) — live,
interactively, with Winston testing in real time — plus a background
build agent on non-overlapping desktop tasks (see §"Claude — Desktop App"
below). Neither agent edits the other's area without saying so here first.

| ID | Task Description | Priority | Assigned To | Status |
|---|---|---|---|---|
| **T-1** | Fix Defect D-1: Set Google Gemini as the default active AI provider and align default models to **`gemini-3.8-flash`** (corrected twice — see urgent correction #2 above; `gemini-2.5-flash` is deprecated, and the interim `gemini-3.6-flash` target is now the fallback tier, not the default). | P1 | Aegis | 🔲 Ready to start — **confirmed, go ahead** (see `docs/deployguard/00-current-state.md` §8, `docs/deployguard/31-dogforce-rollout.md` Stage 0 item 7) |
| **T-2** | Fix Defect D-3: Correct certification model lookup mismatch (`security.employee.certification`) in scanners. | P1 | Aegis | 🔲 Ready to start — **confirmed, go ahead** (Stage 0 item 9) |
| **T-3** | Implement deduction cap & carry-forward logic (G-1) in `security_payroll_core`. | P0 | Aegis | 🔲 Awaiting instructions — **go ahead**; please add a one-line summary of the actual rule (cap %, carry-forward period) here once you've located the source spec, so Winston/Claude can sanity-check before you build against it |
| **T-4** | Harden and verify leave accrual cron with dedicated unit tests (G-5) in `security_leave`. | P1 | Aegis | 🔲 Awaiting instructions — **go ahead** |
| **T-5** | Fix defect D-4: replace `security.event.log._dispatch_event`'s hardcoded 5-bridge list in `security_base` with a `security.bus.subscriber` mixin registry (any installed model implementing it gets called). Wire `security.mobile.bridge` and `security.portal.bridge` onto it — they currently implement `_handle_bus_event` but are never invoked. See [DG-ADR-018](../adr/DG-ADR-018-odoo-bridge-addons.md) §2 for the exact design; this is a prerequisite for the future bridge addon, not speculative. | P1 | Aegis | 🔲 Ready to start |
| **T-6** | Replace `security_suite` as the assumed install baseline in `scripts/setup_staging.sh` and `DEPLOYMENT_SCOPE_AND_EXCLUSIONS.md` with an explicit per-client module list that includes `security_shell` (it's currently missing from the approved list despite being production-critical). | P2 | Aegis | 🔲 Ready to start |
| **T-7** | Security audit pass on `security_ai_whatsapp_bridge`'s `/api/whatsapp/webhook` (`auth="none"`, no signature check today) — propose and implement a minimal shared-secret or HMAC check. Read `docs/deployguard/16-security-architecture.md` §10 (S-3) first. **Do not deploy to production** — open a PR/diff for review only. | P1 | Aegis | 🔲 Ready to start |

Mark a task 🔄 **In progress** when you start it, ✅ **Done** (with a short
note: what changed, what you tested, any follow-up needed) when finished.
If you get blocked or a task turns out bigger than scoped, say so here
rather than going quiet — this file is the only channel we have.

---

## Next Phase — Odoo Bridge Addon (BUILD-ORDER P1)

The desktop app (`desktop/`) is far enough along that the next real
milestone is the **Odoo-side bridge** it will eventually talk to instead
of hitting Odoo directly (see `desktop/DEVIATIONS.md` D-1/D-2 for exactly
what's temporary today, and why). This is a substantial, multi-task
phase — do it in the order below, each task buildable and testable on
its own; don't wait to have all of it before shipping the first pieces.

Read first: [DG-ADR-018](../adr/DG-ADR-018-odoo-bridge-addons.md) (the
whole design), [DG-ADR-007](../adr/DG-ADR-007-authentication.md) (auth
flow this addon implements), [12-odoo-integration.md](../12-odoo-integration.md)
(facade method contracts).

| ID | Task Description | Priority | Assigned To | Status |
|---|---|---|---|---|
| **T-8** | Scaffold `custom_addons/security_deployguard_bridge` (core addon, explicit install — not auto-install, per R-6/R-2): manifest depending on `security_base`, `auth_totp`, `rpc`, `mail`; `group_deployguard_integration` security group + a dedicated `DeployGuard Integration` internal user created on install; settings model (`security.deployguard.config`: Platform base URL, tenant ID, webhook secret write-only field, bridge signing keypair generation, health fields) with a Settings UI page restricted to `base.group_system`. No auth/facade logic yet — just the module skeleton, config model, and its view/security XML. | P1 | Aegis | 🔲 Ready to start |
| **T-9** | On top of T-8: implement the **auth endpoints** from DG-ADR-007 §4 — `POST /api/deployguard/v1/auth/login` (verifies credentials via `request.session.authenticate`, does **not** persist a web session — `save_session` disabled — mints a short-lived signed JWS assertion instead), `POST /api/deployguard/v1/auth/totp`, `POST /api/deployguard/v1/sso/ticket` (single-use, ≤60s, refuses `base.group_system` accounts and anyone without the DeployGuard access flag), `GET /deployguard/sso/consume` (burns the ticket, creates a normal Odoo session, redirects). Rate-limit login by account/IP/device. Full Odoo test coverage (`HttpCase`) for: valid login, wrong password, TOTP required, ticket single-use, ticket expiry, ticket refused for an admin account, replay protection. This is security-critical code — be conservative, and flag anything you're unsure about here rather than guessing. | P0 | Aegis | 🔲 Awaiting T-8 |
| **T-10** | Implement `security.deployguard.outbox` (event_id, event_type, payload JSON, state, attempts, next_attempt_at — mirroring `security_reconciliation_core`'s job pattern) + the `security.deployguard.api` facade model with **read-only** methods for T-8's config plus: `ping`, `get_sites`, `get_employees`, `get_users` (see [12-odoo-integration.md](../12-odoo-integration.md) §3 for exact field lists — stick to the documented allowlists, no extra fields "just in case"). A cron dispatches outbox rows to the Platform webhook endpoint every minute (HMAC-signed per DG-ADR-018 §3) — the endpoint won't exist yet, so the cron should log clearly and retry with backoff rather than erroring loudly. | P1 | Aegis | 🔲 Awaiting T-8 |
| **T-11** | Auto-install domain bridge `security_deployguard_attendance` (depends on T-8's core bridge + `security_attendance`): emit outbox events on attendance batch create/submit/review/lock, and add `get_attendance_batches`/`get_attendance_summary` to the facade. Use this one module as the template — don't build the other domain bridges (roster/incidents/leave/notifications) yet; get this one fully right and tested first, then say so here and we'll scope the rest as follow-up tasks. | P2 | Aegis | 🔲 Awaiting T-10 |

**Ground rules for this phase specifically:**
- Every new model needs `ir.model.access.csv` rows scoped to
  `group_deployguard_integration` only — no `base.group_user` fallback.
- No secret (webhook secret, signing private key) may ever appear in
  plaintext in `ir.config_parameter`, a log line, or a test fixture —
  encrypt at rest per [16-security-architecture.md](../16-security-architecture.md) §6, and use
  placeholder/generated values in tests, never anything resembling a
  real credential.
- This whole phase stays **uninstalled everywhere** until Claude/Winston
  say otherwise — it's built and tested in isolation, not deployed to
  demo or production Namibia/Zambia databases as part of this work.
- Update this table's Status column as you go; if T-9's security-critical
  parts give you pause on any design choice, ask here before writing
  code, not after.

---

## Claude — Desktop App (`desktop/`)

**Live, right now:** Winston is testing the DeployGuard Desktop pilot
shell interactively with me in the main session — persistent top toolbar
(real Odoo Back/Forward/Reload) + click-toggled mega menu over Odoo,
session sync, sign-out. I'm iterating on that UI directly as he finds
issues, so **nothing else should touch `desktop/src/shell/`,
`desktop/src/session/`, or `desktop/src-tauri/src/windowing.rs`** without
checking here first — those are actively changing under live testing.

**Background hardening pass — done, merged (`main` @ `7545161`).** A
background Claude agent (its own git worktree) delivered:
- 25 Rust tests (`odoo::is_unauthenticated_path`, `config::odoo_base_url`,
  `windowing::shell_bounds`/`odoo_bounds`) — `cargo test` in
  `desktop/src-tauri`.
- 28 frontend tests (Vitest, `extractErrorMessage`, `config/env.ts`) —
  `npm test` in `desktop/`. Caught and fixed a real bug in
  `extractErrorMessage.ts` along the way.
- A WCAG contrast audit (`desktop/AGENT-FINDINGS.md`) — 3 of its findings
  (focus-ring contrast, chip/empty-state text contrast, Escape not
  returning focus) were fixed directly in the same commit.
- **Found a real, repo-wide blocker: the GitHub account has a billing
  lockout that fails every Actions run in ~3 seconds** ("account is
  locked due to a billing issue"), confirmed by actually triggering a
  run (PR #1, now closed — useful parts merged, its now-obsolete
  pre-toolbar geometry tests were not). **This needs a human to resolve
  on the GitHub account itself** — no code change here can fix it, and
  it blocks Aegis's work too (any task that would rely on CI, e.g. T-7's
  eventual PR checks).

Nothing further queued here right now — desktop work continues live with
Winston. A new background task will be posted here if/when one's scoped.

---

## Merge note — `claude/dogforce-odoo-issue-a7x08x` brought into `main` (2026-09-16)

Merged two new modules and several reworks from a branch with a week of
uncommitted-to-main work: `security_armed_response` (dispatch board,
live callout map, armoury ledger) and `security_telephony` (call log +
provider-agnostic webhook), plus payroll/payslip designer and billing
document designer reworks, roster/rostering UI updates, and new ACL
regression tests for `security_loans`/`security_payroll_core`. Also
picked up an `odoo.conf` hardening change (`list_db = False`, `dbfilter`
pinned to the single dev DB name — dev config only, doesn't touch
production's own conf). **Neither new module is installed anywhere
yet** — production deployment is being planned next, not done. If your
T-5/T-6 work touches `security_event_bus` dispatch lists or the
per-client module baseline, these two are now real modules that may
need to be accounted for once they're actually installed somewhere.

---

## How We Collaborate

1. **Assign a Task:** Add a new task to the queue above, or move a pending task to **In Progress**.
2. **Reviewing Code:** I can perform deep refactors, write unit tests, verify styling compliance, and run local scripts to test code correctness.
3. **Daily Updates:** Keep this README updated as tasks transition from backlog to verification and completion.
4. **Stay in your lane:** Aegis owns `custom_addons/` (Odoo/Python). Claude owns `desktop/` (Tauri/React/Rust) and `docs/deployguard/`. If a task needs both sides (e.g. a future bridge addon), split it into paired tasks and cross-reference them here rather than one agent reaching into the other's area.
