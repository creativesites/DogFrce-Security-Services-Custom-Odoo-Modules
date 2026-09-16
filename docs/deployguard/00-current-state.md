# 00 — Current State Assessment

> Status: Baseline · Last verified: 2026-09-15 · Owner: Platform architecture
>
> This is the factual starting point for every other DeployGuard OS planning document. Each statement is tagged:
> **[Verified-prod]** read-only inspection of the production database/containers · **[Verified-code]** read from this repository · **[Reported]** stated in existing docs but not independently verified · **[Assumption]** not verifiable yet — tracked in [32-open-questions.md](32-open-questions.md).

---

## 1. Headline finding

| Metric | Value | Source |
|---|---|---|
| Active employees (`hr.employee`) | **210** | [Verified-prod] |
| Active internal Odoo users (`res.users`, `share = false`) | **4** | [Verified-prod] |

DogForce has a feature-rich Odoo platform, but almost no employees are Odoo users. Most operational work (attendance, reports, handovers, escalations) therefore still happens outside the system — on WhatsApp, paper and spreadsheets — or is keyed in centrally by a handful of people. This is the adoption problem DeployGuard OS exists to solve. Per-user login history could not be sampled (see §9), so *how* those 4 accounts are used is unknown.

---

## 2. Environments

| Environment | Facts | Source |
|---|---|---|
| **Production** | Dedicated VPS (8 vCPU, 11 GiB RAM, 237 GB disk, ~7 % used). Containers `dogforce-prod-odoo` (Odoo **19.0-20260723**, `workers = 4`), `dogforce-prod-db` (PostgreSQL **16.14**), `dogforce-prod-whatsapp-bridge`. Database `dogforce_prod`, single company "DOGFORCE SECURITY SERVICES CC". | [Verified-prod] |
| Production host is shared | The same host runs unrelated stacks (`deployfleet_prod_*`, `netone-*`) and a `caddy` container. The repo only contains nginx config (`deploy/nginx/dogforce.conf`), so which proxy fronts DogForce is unclear. | [Verified-prod] / [Verified-code] |
| **Staging** | Same host, `dogforce-staging-*` containers — **exited ~4 weeks ago**. | [Verified-prod] |
| **Demo** | Separate cloud VM, Zambian localisation only (Sentinel Security demo data). DB name differs between docs and scripts (`dogforce-demo`, `dogforce-demo-two`, `zambia-demo`). | [Reported] / [Verified-code] |
| **Local** | Docker Compose (`deploy/docker-compose.yml`), `odoo:19.0` + `postgres:16` + WhatsApp bridge. | [Verified-code] |
| Fly.io | `fly-deploy.yml` workflow on `main`, but `fly.toml` only exists on branch `flyio-new-files`. Status unknown, likely stale. | [Verified-code] |

**Deployment model:** module rsync/zip upload + container restart; production promotion via `scripts/promote_staging_to_prod.sh` (pre-deploy snapshot, `-u` in a temporary container). The script does **not** restore the snapshot on failure, contrary to what two docs claim. [Verified-code]

---

## 3. Odoo platform ("DeployGuard ERP")

- **Version: Odoo 19.0 Community.** All ~50 manifests use `19.0.x.y.z`; `docs/adr/0003-odoo-19-target-version.md` is Accepted. Statements in `CLAUDE.md` / `AGENTS.md` that the stack is Odoo 17 are **stale**. [Verified-code]
- **Architecture:** modular monolith of `security_*` addons integrated via `_inherit` (ADR-0004, ADR-0013). Single tenant per database; there is no tenant model. [Verified-code]

### 3.1 Modules installed in production (37)

| Domain | Installed modules |
|---|---|
| Core / people | `security_base`, `security_documents`, `security_discipline`, `security_leave`, `security_loans` |
| Operations / rostering | `security_operations`, `security_shift_planner`, `security_compliance_roster`, `security_client_onboarding` |
| Attendance | `security_attendance` |
| Payroll | `security_payroll_core`, `security_discipline_payroll`, `security_equipment_payroll`, `security_l10n_na` |
| Equipment / fleet | `security_equipment`, `security_fleet`, `security_fleet_ops` |
| Finance | `security_billing`, `security_billing_account`, `security_billing_crm`, `security_billing_sale`, `security_accounting_controls`, `security_reconciliation_core`, `security_reconciliation_billing_account`, `security_operations_crm` |
| Reporting | `security_reporting`, `security_client_reports` |
| Experience | **`security_shell`**, `security_theme`, `security_help`, `security_portal` |
| AI / messaging | `security_ai_engine`, `security_ai_whatsapp_bridge`, `security_notifications` |
| Mobile | `security_mobile`, `security_mobile_bridge` |
| Migration | `security_dogforce_migration` |

**Uninstalled in production (by design, code retained):** `security_licensing`, `security_tour`, `security_backup_vault`, `security_suite`, `security_zra_invoice`, `security_l10n_zm`, `security_demo_data`, `security_demo_data_zm`, `security_demo_site`, `security_demo_zambia_site`, `security_dogforce_data`. [Verified-prod]

> **Policy:** DeployGuard is a multi-client product. Module *code* is never removed because one client doesn't use it; only the per-database install state changes. Namibian production must keep Zambia-only modules uninstalled.

> **`security_suite` is outdated** and must not be treated as the install baseline, although `scripts/setup_staging.sh` and older docs still reference it. **`security_shell` is critical**, but it is missing from the approved list in `DEPLOYMENT_SCOPE_AND_EXCLUSIONS.md`. [Verified-code]

### 3.2 Security role model in Odoo

Groups in `security_base/security/security_groups.xml`: Security Guard → Supervisor → Manager → Owner (each implies the previous), plus HR/Payroll Officer and System Auditor. [Verified-code]

- Model access mostly goes to generic groups (`hr.group_hr_user` 78 ACL rows, `base.group_user` 28). The Guard, Owner, Auditor and Payroll Officer roles have **no** ACL rows of their own; role checks happen mainly in controllers (`require_group`).
- Only 8 record rules exist, and there are no own-record rules (e.g. a guard seeing only their own slots).
- 221 `sudo()` calls across addons.

---

## 4. Existing capabilities that overlap DeployGuard OS

| Capability | What exists | Location | Relevance |
|---|---|---|---|
| Event bus | `security.event.log` "Intelligence Bus": `register_event()` → synchronous `_dispatch_event()` to a **hardcoded list of 5 bridges**. Events in use: `attendance.missed`, `compliance.bypass`, `compliance.expiring_documents`, `equipment.low_stock`, `fleet.breakdown`, `fleet.shuttle_delayed`, `portal.feedback_received`. | `security_base/models/security_event_bus.py` | Natural source for the Odoo→Platform bridge; the dispatch list must become a registry. |
| Integration jobs | `security_reconciliation_core`: rules, links with fingerprints, jobs (JSON payload, `correlation_id`, retries), conflicts, logs; 5-minute dispatch cron. | `security_reconciliation_core/` | Proven outbox/retry pattern to reuse in the bridge addon. |
| Alerts / exceptions | `security.notification` (types: document/cert expiry, overdue invoice, AWOL, roster gap, override audit; severity info/warning/critical). Crons: roster gaps + missing check-ins every 10 min, daily doc/cert/invoice scans. | `security_notifications/` | Deterministic signals the Platform should ingest rather than re-derive. |
| Help | `security.help.category`, `security.help.article` (country-aware) + OWL help portal. | `security_help/` | Seed content for the Platform knowledge base. |
| Guided tours | `security.tour.definition` with supervisor/manager/owner tours, `res.users.tour_*_done` flags. **Not installed in prod.** | `security_tour/` | Precedent for in-app walkthroughs. |
| Certifications | `security.certification`, `security.employee.certification` (expiry, firearm flag), `security.document.type` category `training`, roster eligibility gate. | `security_base/`, `security_documents/`, `security_compliance_roster/` | Legal/eligibility records stay in Odoo; Platform competencies link to them. |
| Reliability | `hr.employee.security_reliability_score`, `security.reliability.adjustment`. | `security_base/` | Operational performance ≠ system adoption; must not be conflated. |
| AI | `security_ai_engine` v19.0.4: providers Claude/OpenAI/Gemini, 10 `action_ai_*` features, chat panel with tool loop and confirm-before-write, `security.ai.log`, cache, `security.smart.recommendation`. | `security_ai_engine/` | See defect D-1 (default provider). |
| Home "attention" | `security.shell.data.get_home_payload()` → `_get_attention`, `_get_coverage`, `_get_metrics`. | `security_shell/models/` | Precursor of the Manager Inbox concept; the UX reference. |
| Mobile | `security_mobile` REST API (role-scoped owner/manager/supervisor/guard routes) + Expo app with offline queue, PIN lock, Expo push. | `custom_addons/security_mobile/`, `mobile/` | Guard channel; future Platform API consumer. |
| WhatsApp | Baileys-based Node sidecar ↔ `security_ai_whatsapp_bridge` (keyword intents + AI fallback, sender whitelist). | `whatsapp_service/`, `security_ai_whatsapp_bridge/` | Future notification channel. |

**Absent** [Verified-code]: training/LMS (courses, lessons, quizzes); competencies as models; generic tasks, checklists and workflow instances; shift handover and patrol models (patrols are stored as `security.incident` notes); adoption/usage analytics; a tenant model; API tokens/OAuth; any TypeScript web or desktop code besides `mobile/` and the JavaScript `whatsapp_service/`.

---

## 5. Design system and shell

- **Base design system:** `security_base/static/src/css/design_system.css` defines the `--ds-*` tokens ("Clean Corporate Light").
- **Shell layer:** `security_shell/static/src/css/shell_tokens.css` defines the `--dgs-*` tokens: rail `#101724`, canvas `#F5F6F9`, radii 22/20/16/13/22, IBM Plex Mono numerals, one metric ramp.
- **Specification:** [`docs/DEPLOYGUARD_DESIGN_SYSTEM.md`](../DEPLOYGUARD_DESIGN_SYSTEM.md).
- **Shell components** (`security_shell/static/src/js/`): `shell_frame`, `shell_rail`, `shell_rail_flyout`, `shell_nav_panel`, `nav_catalog` (curated tree; leaf flags `soon`, `owner`, `countKey`), `shell_command_palette` (⌘K), `home_dashboard`, `shell_profile_card`, `shell_loading_bar`, `shell_service` (reactive state, persisted to `localStorage` under `dgs.nav.v1`).
- **Technology:** OWL 2 and plain CSS custom properties, no SCSS.
- **Mobile app theme** (`mobile/src/theme/index.ts`, primary `#4F46E5`) and the push notification colour (`#1A56DB`) do **not** follow the design system. [Verified-code]

---

## 6. Integration and API surface

| Surface | Auth | Notes |
|---|---|---|
| `/api/security/mobile/*` (`type="http"`, `cors="*"`) | Odoo session cookie / `X-Openerp-Session-Id` | Envelope `{success, data\|error}`. `/auth/login` defaults to DB `dogforce_dev` in code. |
| `/api/security/mobile/auth/pin` | **Public**, sets session manually | No rate limiting; trusts the client-supplied `employee_id`. |
| `/web/ai-chat/*` (`jsonrpc`) | User session | AI chat panel. |
| `/api/whatsapp/webhook` | **`auth="none"`, no signature** | Protected only by a sender whitelist. |
| WhatsApp sidecar `/send`, `/qr`, `/restart` | **None** | Port 3000 is published on the host in prod compose. |
| Odoo external API | Odoo 19 provides JSON-2 (`/json/2/<model>/<method>`, bearer API key). `/xmlrpc` and `/jsonrpc` are deprecated. | Not used by any DogForce component today. |

---

## 7. Security findings (prerequisites, not fixed by this planning work)

| ID | Finding | Severity |
|---|---|---|
| S-1 | Plaintext production and demo credentials in repository docs (`CLAUDE.md`, `AGENTS.md`, `never_deploy.md`, `MOBILE_DEPLOYMENT_GUIDE.md`) and in root `odoo.conf`, which the `Dockerfile` copies into the image. | Critical |
| S-2 | GitHub OAuth token embedded in the local git remote URL. | High |
| S-3 | WhatsApp webhook unauthenticated; sidecar `/send` unauthenticated and host-exposed. | High |
| S-4 | Mobile PIN login public, not rate-limited; raw PIN kept in device SecureStore. | High |
| S-5 | Mobile offline queue returns a fabricated HTTP 200 for queued writes (user believes the action succeeded). | Medium |
| S-6 | Heavy `sudo()` use; thin record-rule coverage; roles enforced in controllers rather than the ORM. | Medium |

## 8. Known defects relevant to DeployGuard OS

| ID | Defect | Location |
|---|---|---|
| D-1 | `security.ai.config.active_provider` defaults to `claude`; **Gemini must be the default.** Provider files hardcode `claude-sonnet-4-6` and `gemini-1.5-pro`, which disagree with the config default `gemini-2.5-flash`. **Update (2026-09-16, verified against the live API):** `gemini-2.5-flash` is itself now deprecated — a real call returns `404 … use models/gemini-3.6-flash`. The correct target model is **`gemini-3.6-flash`**, not `gemini-2.5-flash`. | `security_ai_engine/models/security_ai_config.py`, `providers/*.py` |
| D-2 | `openai` provider silently falls through to the Claude agent path. | `security_ai_engine/controllers/chat_controller.py` |
| D-3 | `action_scan_certification_expiry` looks up non-existent `security.guard.certification` (real model `security.employee.certification`), so the scan does nothing. | `security_notifications/models/security_notifications.py` |
| D-4 | `security.mobile.bridge` and `security.portal.bridge` implement `_handle_bus_event` but are never dispatched, so Expo push from bus events is dead code. | `security_base/models/security_event_bus.py` |
| D-5 | Stale documentation: Odoo 17 claims, `API.md` (8 of ~40 endpoints), `KNOWN_ISSUES.md` (offline/PIN "missing"), ADR-0008 (PIN "planned"), ADR-0007 superseded in practice by the Aug-2026 accounting decision. | root docs, `docs/adr/` |

---

## 9. Unknowns

- Per-user login frequency and which workflows the 4 internal users perform. A second production query was refused because SSH authentication began failing mid-session.
- Number of office staff, supervisors and managers who would become desktop users; whether they have Windows machines.
- Which reverse proxy (nginx vs Caddy) currently serves the DogForce domain.
- Whether the Fly.io and Render environments still exist.
- Whether DogForce staff have individual email addresses.

All of these are tracked in [32-open-questions.md](32-open-questions.md).
