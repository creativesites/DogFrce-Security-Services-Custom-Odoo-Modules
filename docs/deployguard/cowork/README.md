# Aegis Co-working Space

Welcome to the collaborative workspace for the **DeployGuard OS** rollout. 

I am **Aegis**, your dedicated AI Co-developer and Operations Sentinel. I specialize in backend logic, API integration, styling compliance, and rigorous testing across the Odoo custom addons ecosystem.

This directory serves as our central hub for tracking, coordinating, and executing development tasks.

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
| **T-1** | Fix Defect D-1: Set Google Gemini as the default active AI provider and align default models to `gemini-2.5-flash`. | P1 | Aegis | 🔲 Ready to start — **confirmed, go ahead** (see `docs/deployguard/00-current-state.md` §8, `docs/deployguard/31-dogforce-rollout.md` Stage 0 item 7) |
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

## Claude — Desktop App (`desktop/`)

**Live, right now:** Winston is testing the DeployGuard Desktop pilot
shell interactively with me in the main session — single-window overlay
over Odoo, corner handle, session sync, sign-out. I'm iterating on that
UI directly as he finds issues, so **nothing else should touch
`desktop/src/shell/`, `desktop/src/session/`, or
`desktop/src-tauri/src/windowing.rs`** without checking here first — those
are actively changing under live testing.

I've also spawned a background Claude agent, isolated in its own git
worktree, on tasks that **don't** touch those live files:

| Area | Task |
|---|---|
| CI | Get `.github/workflows/desktop-build.yml` actually producing a working, installable Windows artifact — push a test build, fix whatever GitHub Actions turns up that `cargo build` on macOS can't catch (MSVC-specific errors, bundler issues, icon format quirks on Windows). |
| Tests | Add the Rust unit tests and Playwright/WebDriver smoke tests described in `desktop/README.md` "Testing checklist" and `docs/deployguard/25-testing-strategy.md` — sign-in failure path, connectivity-loss handling, session restore. |
| Accessibility | Run the `docs/deployguard/05-ux-principles.md` §9 checklist against the current panel (contrast, keyboard nav, focus order, `aria-label`s) and fix what it finds. |
| Docs | Keep `desktop/DEVIATIONS.md` and `desktop/README.md` accurate as the live UI changes land — will need a final sync pass once the interactive session settles. |

Its work lands in a separate branch for review/merge once it's done —
it will not appear in Winston's currently-running dev instance until
merged.

---

## How We Collaborate

1. **Assign a Task:** Add a new task to the queue above, or move a pending task to **In Progress**.
2. **Reviewing Code:** I can perform deep refactors, write unit tests, verify styling compliance, and run local scripts to test code correctness.
3. **Daily Updates:** Keep this README updated as tasks transition from backlog to verification and completion.
4. **Stay in your lane:** Aegis owns `custom_addons/` (Odoo/Python). Claude owns `desktop/` (Tauri/React/Rust) and `docs/deployguard/`. If a task needs both sides (e.g. a future bridge addon), split it into paired tasks and cross-reference them here rather than one agent reaching into the other's area.
