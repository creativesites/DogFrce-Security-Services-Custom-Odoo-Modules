# DeployGuard — Production Readiness Audit

**Audit date:** 2026-09-06
**Scope:** `custom_addons/` (50 modules), `whatsapp_service/`, `deploy/`, `mobile/`, repo configuration and documentation.
**Method:** repository-wide static analysis (model/ACL cross-referencing, route and permission enumeration, constraint and exception sweeps) plus targeted deep reads of the payroll, billing, rostering, attendance, authentication and integration paths.
**Not performed:** runtime execution. No live Odoo instance was available to this audit, so no finding below is based on observed runtime behaviour. Findings are marked **Confirmed** (visible directly in code), **Strong suspicion** (code implies it, one unverified assumption remains), or **Needs verification** (requires a running system or production access to settle).

---

## 1. Executive summary

### 1.1 Is DeployGuard production ready today?

**No.** Recommendation: **NO-GO** for operational use handling real payroll, real client billing, or real guard records, until the Phase 0 blockers in §26 are closed.

This is not a verdict on effort or on breadth. The functional surface is genuinely large and much of it is well built — the rostering/attendance core, the reconciliation suite, the new App Shell, and the payslip-generation idempotency are all better than typical for a project this age. The blocking problems are concentrated in **access control, authentication, and financial-record integrity**, not in missing features.

The single most important sentence in this report: **every Security Supervisor can currently read, modify and delete every employee's payslip and loan record, and nothing records that they did.**

### 1.2 What specifically prevents production use

Five issues, all confirmed in code:

1. Payroll and loan data are fully exposed and mutable to all supervisory staff (§7.1).
2. The WhatsApp webhook is completely unauthenticated and can falsify attendance and disclose payroll totals (§7.2).
3. Live database credentials and the Odoo master password are committed to git (§7.3).
4. Mobile PIN authentication is a pass-the-hash design with no rate limiting, over cleartext HTTP (§7.4).
5. A demo module overrides the production login page and publishes account credentials to anonymous visitors (§7.5).

### 1.3 What is already strong

- **Payslip generation is idempotent by design** (`action_generate_payslips` diffs `missing_employees`) — this is the correct pattern and was clearly thought about.
- **Reconciliation suite** is the only subsystem in the repo with complete multi-company record rules (5 of the 8 rules that exist).
- **The App Shell** (`security_shell`) is coherent, documented (`DEPLOYGUARD_DESIGN_SYSTEM.md`), and has a real rollout discipline behind it.
- **`KNOWN_ISSUES.md` is honest.** The team already documents real limitations rather than hiding them. Several findings here corroborate entries already in that file.
- **Frontend timer/listener hygiene is clean** — `setInterval`/`clearInterval` are balanced 2/2, no leaking timers found.
- **Backup Vault** is more thorough than most projects have: nightly full backup with filestore snapshot, offsite R2 sync, *and* a weekly throwaway-DB integrity test — restore is actually exercised, which is rare.

### 1.4 What needs substantial engineering work

Access control and multi-company isolation (essentially absent — 12 of 117 models carry `company_id`, 8 record rules exist repo-wide), payroll state-machine hardening, integration authentication, and test coverage on the operations core.

---

## 2. Repository architecture

Derived from the repository, not assumed.

```
DeployGuard / DogForce Security Services
│
├── Odoo 19 Community  (manifests: 19.0.1.0.0; image odoo:19.0)
│     ⚠ CLAUDE.md still documents "Odoo 17" — stale, see §19
│
├── custom_addons/  — 50 modules, all `security_*`
│   ├── Platform / foundation
│   │   ├── security_base            groups, workforce dashboard, design system CSS
│   │   ├── security_shell           App Shell: rail, nav panel, command palette, Home
│   │   ├── security_theme           white-label theming, login page, app switcher
│   │   ├── security_suite           meta/aggregator
│   │   ├── security_licensing       entitlement enforcement   ⚠ no ACL (§7.8)
│   │   ├── security_notifications   platform notifications
│   │   ├── security_tour            product tours / onboarding
│   │   └── security_help            help centre
│   │
│   ├── Operations core
│   │   ├── security_operations      clients, sites, posts, roster slots, contracts
│   │   ├── security_shift_planner   rostering hub, roster board, AI suggestions
│   │   ├── security_attendance      check-in/out, AWOL, posting console
│   │   ├── security_discipline      incidents, disciplinary cases
│   │   ├── security_compliance_roster
│   │   └── security_armed_response  units, dispatch board, live map, armoury  [NEW]
│   │
│   ├── People
│   │   ├── security_leave, security_documents, security_equipment
│   │   ├── security_loans, security_discipline_payroll, security_equipment_payroll
│   │
│   ├── Finance
│   │   ├── security_payroll_core    periods, payslips, payslip designer
│   │   ├── security_billing (+_account, _crm, _sale)
│   │   ├── security_accounting_controls
│   │   ├── security_reconciliation_core + _billing_account
│   │   └── security_zra_invoice     Zambia Revenue Authority   ⚠ see §10.3
│   │
│   ├── Fleet:      security_fleet, security_fleet_ops
│   ├── Client:     security_client_onboarding, security_client_reports,
│   │               security_portal, security_operations_crm
│   ├── Reporting:  security_reporting
│   ├── Localisation: security_l10n_na (Namibia), security_l10n_zm (Zambia)  ⚠ §10.3
│   ├── Integrations: security_ai_engine, security_ai_whatsapp_bridge,
│   │                 security_telephony [NEW], security_mobile, security_mobile_bridge,
│   │                 security_backup_vault
│   └── Data:       security_dogforce_data (71k LOC), security_demo_data,
│                   security_demo_data_zm, security_demo_site,
│                   security_demo_zambia_site, security_dogforce_migration
│
├── whatsapp_service/   Node + Baileys WhatsApp bridge (separate container)
├── mobile/             Expo SDK 54 / React Native, EAS builds
├── deploy/             docker-compose (prod / staging)
└── docs/               design system, rollout plan, ADRs, this audit
```

**Integrations:** WhatsApp (Baileys, self-hosted), Google Maps (Armed Response), ZRA Smart Invoice, Cloudflare R2 (backups), AI engine, mobile REST API, Telephony webhook (no PBX connected yet).

---

## 3. Module inventory (summary)

Full per-module detail is impractical to reproduce here; this is the status classification. "COMPLETE" is assigned on evidence of working end-to-end wiring (model + view + menu/nav + ACL), never on file existence alone.

| Module | UI | Backend | Security | Tests | Status |
|---|---|---|---|---|---|
| security_base | ✅ | ✅ | ✅ groups | ❌ | COMPLETE |
| security_shell | ✅ | ✅ | n/a | ❌ | COMPLETE |
| security_operations | ✅ | ✅ | ✅ +1 rule | ❌ | MOSTLY COMPLETE |
| security_shift_planner | ✅ | ✅ | ✅ | ✅ | MOSTLY COMPLETE |
| security_attendance | ✅ | ✅ | ✅ | ✅ | MOSTLY COMPLETE |
| security_payroll_core | ✅ | ✅ | ⚠ over-broad | ✅ | **FRAGILE** (§9.1) |
| security_loans | ✅ | ✅ | ⚠ over-broad | ❌ | **FRAGILE** (§9.2) |
| security_billing | ✅ | ✅ | ✅ | ✅ | MOSTLY COMPLETE |
| security_reconciliation_core / _billing_account | ✅ | ✅ | ✅ 5 rules | ✅ | COMPLETE |
| security_ai_whatsapp_bridge | ✅ | ✅ | ❌ **unauth webhook** | ❌ | **FRAGILE** (§7.2) |
| security_mobile | n/a | ✅ | ❌ **auth defects** | ✅ | **FRAGILE** (§7.4) |
| security_demo_site | ✅ | ✅ | ❌ **public creds** | ❌ | **PRODUCTION HAZARD** (§7.5) |
| security_licensing | ✅ | ✅ | ❌ **no ACL** | ❌ | **BROKEN** (§7.8) |
| security_armed_response | ✅ | ✅ | ✅ | ❌ | MOSTLY COMPLETE (new) |
| security_telephony | ✅ | ✅ | ✅ token | ❌ | PARTIAL by design (no PBX) |
| security_zra_invoice | ✅ | ✅ | ✅ | ❌ | UNKNOWN — jurisdiction (§10.3) |
| security_dogforce_data | n/a | ✅ | n/a | ❌ | NEEDS VERIFICATION (§22.2) |
| security_equipment / _fleet / _leave / _documents / _discipline | ✅ | ✅ | ✅ | partial | MOSTLY COMPLETE |
| security_portal / _operations_crm / _billing_crm | partial | ✅ | ✅ | ❌ | PARTIAL |
| security_help / _tour / _theme / _notifications | ✅ | ✅ | ✅ | ❌ | COMPLETE |
| security_backup_vault | ✅ | ✅ | ✅ | ❌ | MOSTLY COMPLETE |

---

## 4. The three recently requested modules

The brief states three DogForce-requested modules "have now been added". **Two are added; the third is not.**

| Requested capability | Status | Evidence |
|---|---|---|
| **Armed Response** (units, dispatch board, live map, armoury) | ✅ Built | `security_armed_response/` |
| **Control Room** (call receiving + dispatch) | ⚠ Partial | Dispatch board built. Telephony is the *receiving end only* — `security_telephony/` has no PBX behind it; DogForce has no phone system yet |
| **Fleet / vehicle tracking** | ❌ **Not built** | `nav_catalog.js:211` — `fleet_tracking_map` is still `soon: true` |

ARETE stated all three departments are "fully functional" business units at DogForce today. Fleet tracking has no implementation. This should be corrected in any status reporting to the client.

**Remaining `soon: true` nav gaps** (`nav_catalog.js`): applicant pipeline (145), vacancies (146), document register (154), fleet tracking map (211), client portal (233).

---

## 5. Core workflow audit — CLIENT → … → REPORTING

| Link | State | Note |
|---|---|---|
| Client → Site → Post | ✅ Complete | `security_operations`; sites carry `gps_lat/lng` + geofence |
| Post → Shift requirement → Roster | ✅ Complete | Auto-generation cron exists |
| Roster → Shift → Check-in | ✅ Complete | Gap-detection cron every 10 min |
| Attendance → AWOL/Incident | ✅ Complete | Incident model real (`security.incident`) |
| **Attendance → Payroll** | ⚠ **Fragile** | Payslip pulls *all* attendance in period with **no approval gate** — `attendance_record_ids = [(6,0,...)]` (`security_payroll_core.py:485-509`). `billing_approved` / `overtime_approved` flags exist on attendance (`security_attendance.py:371,386`) but the payslip computation does not filter on them. Unapproved and falsified attendance flows straight into pay. |
| **Payroll → Payslip** | ⚠ **Fragile** | Recompute has no state guard (§9.1) |
| Payslip → Billing | ⚠ Partial | Billing generates from roster *or* attendance *or* approved attendance — three parallel paths (`security_billing.py:443,458,478`), no single source of truth |
| Billing → Invoice → Payment | ✅ Mostly | |
| Payment → Reconciliation | ✅ Strong | Best-engineered subsystem in the repo |
| → Reporting | ✅ | |

**The weakest link is Attendance → Payroll.** It has no approval gate, and it is downstream of the unauthenticated WhatsApp webhook (§7.2). That is the cross-module chain that matters most:

```
unauthenticated WhatsApp webhook  →  attendance falsified
      →  payslip (no approval gate, no state guard)
      →  payroll paid  →  billing generated from same attendance
      →  invoice to client  →  reconciliation  →  reporting
```

A single anonymous HTTP request can therefore influence what a guard is paid **and** what a client is invoiced, with no audit trail on the resulting payslip.

---

## 6. Data model audit

| Metric | Count | Assessment |
|---|---|---|
| Concrete + transient models | 117 | |
| AbstractModels | 18 | |
| `@api.constrains` | 41 | Thin for the domain |
| SQL / `models.Constraint` | 8 | **Very thin** |
| UNIQUE constraints | 8 | **Very thin** |
| `ondelete=` on M2O | 64 | Reasonable |
| `index=True` | 59 | Reasonable |
| Models with `company_id` | **12 / 117** | **Multi-company unsafe** (§8) |
| `ir.rule` records repo-wide | **8** | **Row-level security effectively absent** |

### 6.1 Impossible states the system can currently represent

| Impossible state | Prevented? | Evidence |
|---|---|---|
| Payslip recomputed after being paid | ❌ No | `action_compute_from_sources` has no state filter (`security_payroll_core.py:485`) |
| Loan deduction applied twice | ❌ No | `action_confirm` has no state guard; `action_apply_carry_forward` does `+=` (`security_loans.py:173`) |
| Two payslips for same (period, employee) under concurrency | ❌ No DB constraint | Application-level diff only; no UNIQUE on `(period_id, employee_id)` |
| Closed payroll period reopened and regenerated | ❌ No | `action_reset_to_draft` unguarded (`security_payroll_core.py:144`) |
| Paid payslip reset to draft | ❌ No | `action_reset_to_draft` unguarded (`:436`) |
| Payslip marked paid without confirmation | ❌ No | `action_mark_paid` does not check state (`:432`) |
| Attendance counted for pay without approval | ❌ No | §5 |
| Cross-company data visible | ❌ No | Only 4 modules have any rule |

---

## 7. Security audit

### 7.1 P0 — Payroll and loan records fully exposed and mutable to all supervisors
**Confirmed.**

**Evidence:**
- `security_payroll_core/security/ir.model.access.csv` — `access_security_payslip_user,…,model_security_payslip,hr.group_hr_user,1,1,1,1` (read/write/create/**unlink**)
- Same pattern for `security.payslip.earning.line`, `security.payslip.deduction.line`
- `security_loans/security/ir.model.access.csv` — `security.employee.loan`, `security.loan.deduction` → `hr.group_hr_user,1,1,1,1`
- `security_base/security/security_groups.xml:20` — `group_security_supervisor` → `implied_ids = [group_security_guard, hr.group_hr_user]`
- No `ir.rule` exists in `security_payroll_core` or `security_loans` (verified: no rule files in either module)
- `security.payslip` does **not** inherit `mail.thread` (only `_inherit` in that file is `hr.employee` at `:805`)

**Impact:** Every Security Supervisor — and by implication every Manager and Owner — can read every employee's salary, allowances, deductions and loans, including management's; can alter those figures; and can **delete** payslips outright. Because the model has no chatter, none of this is recorded. This is simultaneously a confidentiality breach, a financial-integrity risk, and an audit failure. In a payroll system this is the most serious class of defect.

**Recommendation:** Restrict payslip/loan ACLs to a dedicated payroll group; add `ir.rule` limiting non-payroll users to `employee_id.user_id == user`; remove `unlink` from all non-admin groups; add `mail.thread` + `tracking=True` on monetary and state fields.

### 7.2 P0 — WhatsApp webhook is completely unauthenticated
**Confirmed.**

**Evidence:** `security_ai_whatsapp_bridge/controllers/whatsapp_webhook.py:11`
```python
@http.route("/api/whatsapp/webhook", type="json", auth="none", methods=["POST"], csrf=False)
```
Targeted search for `token|secret|signature|hmac|verify|allowlist` in that file returns **nothing**. The handler reads `From` and `Body` straight from the request body and passes them to `process_incoming_message`. The only gate is `_check_sender_authorized`, which compares the **attacker-supplied** `From` value against a configured number list — trivially spoofed.

**Impact:** Any anonymous party who can reach port 8069 can:
- `OWNER STATS` → the HTTP response returns gross payroll, allowances, statutory deductions, net payable, monthly recurring billing and active site count (`whatsapp_bridge.py:661-679`) — financial exfiltration with no login
- `[Site] all present` → mark an entire site's guards present (feeds payroll **and** billing)
- `AWOL [Guard]` → falsely flag a guard, triggering discipline and payroll deduction
- Create incident records

**Recommendation:** Shared-secret or HMAC signature validation on the route (the pattern already used in `security_telephony/controllers/telephony_event.py` and `security_armed_response/controllers/gps_ping.py` is the correct in-repo precedent); bind the endpoint to the internal Docker network; never return financial aggregates to an unauthenticated caller.

### 7.3 P0 — Live credentials committed to version control
**Confirmed.**

**Evidence:** `odoo.conf` is git-tracked (`git ls-files` confirms) and contains `admin_passwd`, `db_password`, and a live managed-Postgres FQDN (`dpg-…singapore-postgres.render.com`). `.gitignore` covers `.env` only. Credentials also appear in `CLAUDE.md`, `AGENTS.md`, `INSTALL.md`, `MOBILE_DEPLOYMENT_GUIDE.md`, `deploy/docker-compose*.yml`, `.github/workflows/fly-deploy.yml`.

**Impact:** Anyone with repository access — including anyone who ever cloned it — holds the database password for an internet-reachable Postgres instance and the Odoo master password (which permits database drop/restore). Rotation alone is insufficient; the values persist in git history.

**Recommendation:** Rotate every exposed credential; move config to environment variables / Docker secrets; add `odoo.conf` to `.gitignore` with a committed `odoo.conf.example`; purge history or treat all historical values as permanently compromised.

### 7.4 P0 — Mobile PIN authentication defects
**Confirmed.**

**Evidence:** `security_mobile/controllers/main.py:164-225`
```python
@http.route("/api/security/mobile/auth/pin", auth="public", methods=["POST","OPTIONS"],
            type="http", csrf=False, cors="*")
…
env = request.env(su=True)
employee = env["hr.employee"].browse(int(employee_id))
…
verified = crypt_context.verify(pin_hash, stored_hash)
```
Repo-wide search for `rate.?limit|attempt|throttle|lockout` in `security_mobile/` returns **nothing**.

Four distinct defects:
1. **Pass-the-hash** — the client-supplied `pin_hash` *is* the credential. Anyone who captures it (device storage, logs, or the wire) can replay it indefinitely.
2. **No rate limiting** — with a short numeric PIN and a known client-side hash scheme, the entire PIN space can be enumerated against this endpoint.
3. **Employee enumeration** — attacker-controlled `employee_id` with distinct error messages ("Employee not found" 404 / "PIN not configured" 401 / "No Odoo user linked" 401 / "Invalid PIN" 401) is an oracle over the whole employee table, executed under `su=True`.
4. **Cleartext transport** — `CLAUDE.md` documents `EXPO_PUBLIC_ODOO_BASE_URL=http://…` and `usesCleartextTraffic: true`, so credentials cross the network unencrypted.

`cors="*"` on an auth endpoint compounds 1–3.

**Recommendation:** Server-side PIN verification against a per-device salt; strict rate limiting and lockout keyed on employee + IP; uniform error responses; drop `su=True` before authentication; TLS before any production mobile rollout.

### 7.5 P0 (conditional) — Demo module publishes credentials on the login page
**Confirmed in code; installation on production = Strong suspicion.**

**Evidence:** `security_demo_site/controllers/main.py:8` overrides the global `/web/login` route (`auth='none'`) and renders `demo_accounts` — `login` + `password_hint` — for all anonymous visitors. `:67` exposes the same via public JSON (`/security/demo/accounts`, `auth='public'`). `password_hint` is declared `string='Password (display)'` (`security_demo_config.py:12`). `demo_accounts.xml` seeds **4 `res.users`** with `password`, `password_hint` and `group_ids`. The panel defaults to **enabled** (`security.demo.panel_enabled` defaults `'True'` — opt-out, not opt-in).

**Why production installation is suspected:** the password-reset defect fixed earlier this week (demo_accounts.xml `noupdate="0"` overwriting passwords on every upgrade) was observed *on the production database*. That data file belongs to this module, so the module is installed there.

**Impact:** If installed on production, the public login page of a system holding 872 real client sites advertises working credentials and their access levels.

**Recommendation:** Confirm install state on production immediately (`ir_module_module` where `name='security_demo_site'`); uninstall from production; change the default to opt-**in**; never ship a `/web/login` override in a module that can reach production.

### 7.6 P1 — Unauthenticated attack surface summary

| Route | Auth | Protected? | Verdict |
|---|---|---|---|
| `/api/whatsapp/webhook` | `none` | ❌ nothing | §7.2 |
| `/web/login` (override) | `none` | n/a | §7.5 |
| `/security/demo/accounts` | `public` | ❌ | §7.5 |
| `/api/security/mobile/auth/login` | `public` | password | Legitimate |
| `/api/security/mobile/auth/pin` | `public` | ❌ weak | §7.4 |
| `/api/telephony/event` | `none` | ✅ shared token | Acceptable |
| `/api/armed_response/units/<id>/ping` | `none` | ✅ per-unit token | Acceptable |

`csrf=False` appears 43 times — acceptable on JSON/API routes, but each `type='http'` + `auth='user'` occurrence needs review (**Needs verification**).

### 7.7 P1 — `sudo()` concentration
225 `.sudo()` calls repo-wide; 98 in `security_mobile`, 47 in `security_ai_whatsapp_bridge`, 28 in `security_ai_engine`. The mobile and WhatsApp concentrations are the concern: both accept external input and then operate with elevated rights. `security_mobile/controllers/main.py:186` uses `request.env(su=True)` on an attacker-supplied `employee_id` **before** authentication. Individual review required (**Needs verification** per call site; the pre-auth `su=True` is **Confirmed**).

### 7.8 P1 — `security_licensing` ships no ACL
**Confirmed.** Its three models (`security.license`, `security.license.log`, `license.key.wizard`) have no `ir.model.access` row anywhere; the manifest `data` list contains no `.csv`. The module is wired into the Owner nav (`nav_catalog.js:261`) and has menu items. Non-superusers will hit `AccessError`. Either the licensing/entitlement feature is unreachable in practice, or it only ever worked while logged in as `admin`.

---

## 8. Multi-company audit

**Confirmed — the platform is not multi-company safe.**

- 12 of 117 models declare `company_id`
- 9 use `_check_company_auto`
- **8 `ir.rule` records exist in the entire repository**, in only 4 modules (`security_reconciliation_core` ×5, `security_notifications`, `security_help`, `security_operations`)

Payroll, loans, attendance, discipline, equipment, fleet, documents and billing have **no company scoping and no record rules**. ARETE has indicated DogForce operates branches; the competitor platform models an Organisation/branch hierarchy. The moment a second company or branch entity is added, every un-scoped model leaks across it.

This is architectural and cannot be retrofitted cheaply — it should be decided deliberately before, not after, a second entity exists.

---

## 9. Business logic audit

### 9.1 P1 — Payslip recompute has no state guard
**Confirmed.** `security_payroll_core.py:87-119` (`action_generate_payslips`) selects **all** payslips for the period and calls `all_payslips.action_compute_from_sources()`. That method (`:485`) iterates `for payslip in self:` with no state filter. `action_recompute_payslips` (`:123`) simply re-calls it.

Creation is correctly idempotent (`missing_employees` diff — a genuine strength). **Recomputation is not gated**: re-running on a period whose payslips are `confirmed` or `paid` silently rewrites paid financial records. There is no audit trail (§7.1).

### 9.2 P1 — Loan carry-forward double-application
**Confirmed.** `security_payroll_core.py:422` `action_confirm()` sets `state = "confirmed"` without checking current state, and calls `active_loans.action_apply_carry_forward(payslip)`. `security_loans.py:173` performs `next_line.amount += carry` — **not idempotent**.

Reproduction: confirm → `action_reset_to_draft()` (unguarded, `:436`) → confirm again ⇒ the employee's next loan deduction is inflated by the carry-forward amount, repeatable indefinitely.

### 9.3 P1 — Unguarded state transitions throughout payroll
`action_mark_paid` (`:432`), `action_reset_to_draft` (`:436`, `:144`), `action_close` (`:140`) perform bare assignments with no validation. A paid payslip can be reset to draft; a closed period can be reopened; a draft payslip can be marked paid without ever being confirmed.

### 9.4 P2 — Three parallel billing generation paths
`action_generate_from_roster` (`:443`), `action_generate_from_attendance` (`:458`), `action_generate_from_approved_attendance` (`:478`), plus `action_auto_invoice_all` (`:43`) driven by the *"Security: Auto-generate Monthly Invoices"* cron. Duplicate-invoice protection across these paths is **Needs verification** — but a monthly cron that generates invoices is exactly the case where a non-idempotent retry double-bills a client.

### 9.5 P2 — Attendance has approval flags that payroll ignores
`security_attendance.py:371,386` define `overtime_approved` and `billing_approved` with approver and timestamp fields. The payslip computation (`security_payroll_core.py:485-509`) filters attendance only by employee and date — never by approval. The approval workflow exists but does not gate anything.

---

## 10. Integration audit

| Integration | Auth | Retry | Idempotent | Logging | Production ready |
|---|---|---|---|---|---|
| WhatsApp inbound webhook | ❌ **none** | n/a | ❌ | partial | **No** (§7.2) |
| WhatsApp bridge (Baileys) | session/QR | ✅ backoff | n/a | ✅ | Conditional (§10.1) |
| Mobile REST API | ⚠ defective | n/a | n/a | partial | **No** (§7.4) |
| Google Maps (Armed Response) | API key | n/a | n/a | ✅ | Yes, key not yet set |
| Telephony webhook | ✅ token | n/a | ✅ by `pbx_call_id` | ✅ | Yes — but no PBX exists |
| ZRA Smart Invoice | — | ✅ retry cron | ? | ? | **Jurisdiction risk** (§10.3) |
| Backup Vault / R2 | — | ✅ | ✅ | ✅ | Yes (§14) |
| AI engine | — | ? | n/a | ✅ has log model | Needs verification |

### 10.1 WhatsApp bridge resilience
`whatsapp_service/index.js` handles reconnect with exponential backoff, session persistence via `useMultiFileAuthState`, and QR rotation. It survives restart and network loss. Two gaps: pairing-code linking was scaffolded but never completed (state variables exist, no `requestPairingCode` call path); and inbound message processing has **no duplicate-event guard** — Baileys can redeliver, and a redelivered `[Site] all present` re-marks attendance.

### 10.2 Human-delay simulation on replies
`whatsapp_service/index.js` delays every reply 15–30 s and shows a typing indicator. For an operations channel that may carry AWOL and incident traffic, an intentional 15–30 s delay on **every** message is a questionable default (**Needs verification** — may be deliberate for demo realism, but it is not appropriate for emergency operational messaging).

### 10.3 P1 — Jurisdiction mismatch: Zambia vs Namibia
**Confirmed.** DogForce is Namibian (`+264`, `admin@dogforce.com.na`, `security_l10n_na`, 1,367 `NAD`/`N$` references). The repository also carries a full Zambian stack: `security_zra_invoice` (Zambia Revenue Authority Smart Invoice), `security_l10n_zm`, `security_demo_data_zm`, `security_demo_zambia_site`, 119 `ZMW` references, 87 `NAPSA`/`NHIMA` references.

Worse, this leaks into user-facing financial output:
```
security_ai_whatsapp_bridge/models/whatsapp_bridge.py:666-673
  "• 💵 Est. Monthly Recurring Billing: `ZMW {monthly_revenue:,.2f}`"
  "• ➖ Statutory Deductions (NAPSA/NHIMA/PAYE): `ZMW {statutory_deductions:,.2f}`"
```
A Namibian owner requesting stats receives their real payroll figures labelled in Zambian Kwacha with Zambian statutory deduction names. `security_billing.py:1088` also defaults to `"ZMW"` when a company currency symbol is absent.

**Recommendation:** Decide explicitly whether this is one product for two markets or a Namibian deployment carrying Zambian residue. Then either make currency/statutory labels company-driven throughout, or remove the Zambian modules from the Namibian deployment. Do not ship financial output with a hardcoded foreign currency.

---

## 11. Frontend / OWL audit

**Largely clean** — this area is in better shape than the backend.

- `setInterval` 2 / `clearInterval` 2 — balanced, no leaking timers
- `addEventListener` 18 / `removeEventListener` 12 — a gap of 6 (**Needs verification**; some are on elements destroyed with the component, which is legitimate)
- The old `deployguard_command_center` component was properly *retired*, not left dead, when `security_shell` superseded it
- The `.rmm-overlay` full-viewport bug was found and fixed during the shell rollout — good discipline

**Outstanding:** the Phase 2 decision in `DESIGN_SYSTEM_ROLLOUT_PLAN.md` (retire vs keep the five mega-menus) is still open. Several retrofitted CSS files (e.g. `roster_board.css:13-23`) use hardcoded hex values that *happen to match* the design tokens rather than `var(--ds-*)` references — cosmetically correct today, but white-label theme changes will not propagate. P3.

---

## 12. Error handling and observability

- **108** `except Exception` blocks; **0** bare `except:`; **14** exception handlers whose body is `pass`
- The 14 silent-swallow sites are the concern — a swallowed exception in a payroll or billing path produces a wrong number rather than an error (**Needs verification** per site)
- `security_notifications/models/security_notifications.py:72` hardcodes `http://localhost:8069` — notification links will be broken in production (P2, Confirmed)
- Logging exists and is reasonably structured in the integration modules; there is no correlation ID across the WhatsApp → Odoo → payroll chain

---

## 13. Testing audit

| Metric | Value |
|---|---|
| Modules with a `tests/` directory | **12 of 50 (24%)** |
| Test files | 17 |
| Test LOC | 2,670 |

**Tested:** payroll_core, billing, attendance, shift_planner, equipment, fleet, leave, mobile, accounting_controls, reconciliation ×2, l10n_zm.

**Untested — and significant:**
`security_operations` (the operations core — clients, sites, posts, roster slots), `security_discipline`, `security_loans` (the module with the confirmed double-deduction bug), `security_ai_whatsapp_bridge`, `security_base` (the group/permission definitions), `security_shell`, `security_licensing`, `security_documents`, `security_zra_invoice`, `security_armed_response`, `security_telephony`.

**No test anywhere exercises access control.** Given §7.1, a single test asserting "a supervisor cannot read another employee's payslip" would have caught the most serious finding in this report.

---

## 14. Deployment, backup and recovery

**Backup is a strength.** `security_backup_vault` runs a nightly full backup with filestore snapshot, hourly disk-space monitoring, R2 offsite sync, and — notably — a **weekly throwaway-DB integrity test**. Restore is actually exercised, which most projects never do. `KNOWN_ISSUES.md` correctly notes there is no restore *script*; restore is manual.

**Deployment concerns:**
- `KNOWN_ISSUES.md` records that **production runs Odoo Enterprise separately while this repo targets Community, with an undefined cutover path**. That is a material unknown for a production readiness assessment.
- The repo `odoo.conf` correctly sets `list_db = False` and `dbfilter` (hardening applied), but points at `dogforce_dev`. Whether production's config carries the same hardening is **Needs verification**.
- Production infrastructure (observed earlier this week): three unrelated application stacks share one 11.68 GB host; Postgres ran on stock defaults with a 64 MB `/dev/shm` until it was raised to 512 MB and CPU/memory limits were applied to the DogForce containers. Resource isolation is now in place for DogForce but not for the neighbours.

---

## 15. Migration and upgrade safety

- `security_dogforce_data` is 71,419 lines of Python loading "real DogForce company data from XLSX exports via post-init hook". Its interaction with an existing production database on upgrade is **Needs verification** — a post-init hook that loads company data is exactly the kind of thing that duplicates records if it runs again.
- Demo modules (`security_demo_data`, `security_demo_data_zm`, `security_demo_site`, `security_demo_zambia_site`) can seed users and data into any database they are installed on. The `noupdate="0"` password-overwrite defect already demonstrated this reaching production.
- 17 cron jobs; the financially significant ones (*Auto-generate Monthly Invoices*, *Monthly Leave Accrual*, *Year-End Leave Carryover*, *Auto-generate Next Month Roster Batches*) all need explicit idempotency review (**Needs verification**) — a monthly job that double-runs after a failure is how clients get double-billed.

---

## 16. Documentation audit

Documentation volume is high (17 top-level `.md` files plus `docs/`), and `KNOWN_ISSUES.md` is genuinely honest. Problems:

- **`CLAUDE.md` states "Odoo 17 Community"; the codebase is Odoo 19** (all manifests `19.0.1.0.0`, image `odoo:19.0`). The single most-read onboarding document is wrong about the platform version.
- `CLAUDE.md` documents a demo server and database (`dogforce-demo` @ 47.84.205.81) that is not the production system worked on this week (`dogforce_prod` @ server1). A new engineer following it would deploy to the wrong place.
- Credentials in documentation (§7.3).
- No documented restore procedure (corroborated by `KNOWN_ISSUES.md`).

---

## 17. Production readiness scorecard

| Area | Score | Status | Major concern |
|---|---:|---|---|
| Core workflows | 7/10 | Good | Attendance→payroll approval gate missing |
| Data integrity | 3/10 | **Weak** | Unguarded payroll states; 8 unique constraints across 117 models |
| Security | 2/10 | **Critical** | Payroll ACL; unauthenticated webhook; committed credentials |
| Permissions | 2/10 | **Critical** | 8 record rules repo-wide; supervisor ⇒ `hr.group_hr_user` |
| Multi-company | 2/10 | **Weak** | 12/117 models scoped |
| Payroll | 4/10 | **Weak** | Recompute-after-paid; loan double-application; no audit trail |
| Rostering | 8/10 | Strong | Well covered, automated, tested |
| Attendance | 7/10 | Good | Approval flags unused downstream |
| Billing | 6/10 | Adequate | Three generation paths; cron idempotency unverified |
| Integrations | 4/10 | Weak | WhatsApp unauthenticated; jurisdiction mismatch |
| Frontend / Shell | 8/10 | Strong | Clean lifecycle, documented system |
| Performance | 6/10 | Adequate | Not load-tested; prod already had a resource incident |
| Testing | 3/10 | **Weak** | 24% of modules; zero permission tests |
| Deployment | 5/10 | Mixed | Backup strong; Community/Enterprise cutover undefined |
| Documentation | 5/10 | Mixed | Honest but stale on platform version; credentials embedded |

### **Overall production readiness: 4/10 — NO-GO**

The score is deliberately not lifted by the polished shell. The UI is genuinely good; the permission model underneath it is not.

---

## 18. Risk register — top 10

| # | Severity | Category | Risk | Confidence |
|---|---|---|---|---|
| 1 | P0 | Security / Data integrity | All supervisors can read, edit and delete all payslips and loans, untracked | Confirmed |
| 2 | P0 | Security | Unauthenticated WhatsApp webhook → attendance falsification + payroll disclosure | Confirmed |
| 3 | P0 | Security | Live DB password + Odoo master password in git | Confirmed |
| 4 | P0 | Security | Mobile PIN: pass-the-hash, no rate limit, enumeration, cleartext | Confirmed |
| 5 | P0 | Security | Demo login override publishes credentials publicly | Confirmed in code; prod install suspected |
| 6 | P1 | Data integrity | Paid payslips silently recomputed | Confirmed |
| 7 | P1 | Data integrity | Loan carry-forward applied twice | Confirmed |
| 8 | P1 | Correctness | Namibian company shown ZMW / NAPSA labels on real figures | Confirmed |
| 9 | P1 | Architecture | No multi-company isolation | Confirmed |
| 10 | P1 | Data integrity | Unapproved attendance flows into pay and invoices | Confirmed |

---

## 19. Remediation roadmap

### Phase 0 — Production blockers (must precede any operational use)

| # | Item | Modules | Size | Risk |
|---|---|---|---|---|
| 0.1 | Rewrite payroll/loan ACLs; add record rules; remove `unlink`; add `mail.thread` + field tracking | payroll_core, loans, base | **L** | Med — may break existing user access; needs a permission test suite alongside |
| 0.2 | Authenticate the WhatsApp webhook (shared secret/HMAC, internal-network binding) | ai_whatsapp_bridge, whatsapp_service | **M** | Low — in-repo precedent exists |
| 0.3 | Rotate all exposed credentials; move to env/secrets; untrack `odoo.conf` | repo-wide, deploy | **M** | Med — coordinated rotation across prod/staging/CI |
| 0.4 | Fix mobile PIN auth; add rate limiting; uniform errors; enable TLS | mobile, security_mobile | **L** | Med — forces a mobile app rebuild |
| 0.5 | Confirm and remove `security_demo_site` from production; flip panel to opt-in | demo_site | **S** | Low |

### Phase 1 — Reliability and financial integrity

| # | Item | Size |
|---|---|---|
| 1.1 | State guards on all payroll transitions; block recompute of confirmed/paid payslips | M |
| 1.2 | Make loan carry-forward idempotent (ledger entry keyed to payslip, not `+=`) | M |
| 1.3 | UNIQUE constraint on `(period_id, employee_id)` and equivalents | S |
| 1.4 | Gate payroll and billing on attendance approval flags | M |
| 1.5 | Audit the 14 silent `except: pass` sites in financial paths | S |
| 1.6 | Idempotency review of the 4 financially significant crons | M |

### Phase 2 — Core workflow completion
Fleet & tracking map (the missing third requested module); consolidate the three billing generation paths; document register; client portal; recruitment.

### Phase 3 — Security hardening
Multi-company record rules across all business models; `sudo()` review in mobile/WhatsApp; `csrf=False` review on `type='http'` routes; `security_licensing` ACL.

### Phase 4 — Performance
Load-test rostering and payroll at realistic volume; index review; N+1 sweep in dashboards.

### Phase 5 — UX polish
Close the Phase 2 mega-menu decision; convert hardcoded hex to token references.

### Phase 6 — Testing
Permission test suite **first** (it would have caught risk #1); then payroll, billing, roster regression tests; integration tests for the WhatsApp and mobile endpoints.

### Phase 7 — Deployment
Restore script + tested restore runbook; resolve the Community/Enterprise cutover question; production config parity check; monitoring.

### Phase 8 — Post-launch
Jurisdiction consolidation; documentation refresh; remaining `soon:true` features.

---

## 20. Recommended next action

**Write a permission test suite before changing any permission code.**

Specifically: a test asserting that a user in `group_security_supervisor` cannot read a payslip belonging to another employee. It will fail today. That single failing test converts the most serious finding in this report from an assertion into a regression gate, and it makes Phase 0.1 safe to attempt — because the risk in rewriting ACLs on a live system is breaking legitimate access, and only a test suite tells you when you have.

---

*Findings marked Confirmed are visible directly in the code at the cited locations. Findings marked Needs verification require a running system or production access and should not be treated as established until checked.*
