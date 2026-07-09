# DogForce Security Suite — Module Reference

**Last updated:** 2026-06-16  
**Purpose:** Ground-truth inventory of what is built and where to find it. Use this as a quick lookup before adding code to avoid duplication.

---

## Quick module map

| Module | Purpose | Status |
|--------|---------|--------|
| `security_base` | Guard master data, grades, certs, mobile fields | ✅ Production |
| `security_operations` | Client → Site → Post → Roster hierarchy | ✅ Production |
| `security_shift_planner` | Scoring engine, eligibility filter, roster wizard | ✅ Production |
| `security_attendance` | Posting batches, attendance records, shift-split | ✅ Production |
| `security_leave` | Leave types, balances, requests, accrual cron | ✅ Production |
| `security_payroll_core` | Payslips, earning/deduction lines, PAYE/SSC, wizard | ✅ Production |
| `security_l10n_na` | Namibia rule sets, PAYE brackets, public holidays, SSC | ✅ Production |
| `security_loans` | Employee loans, schedules, payroll deduction hook | ✅ Production |
| `security_discipline` | Incidents, reliability scoring, payroll impact | ✅ Production |
| `security_documents` | Document types, expiry tracking, verification | ✅ Production |
| `security_equipment` | Categories, allocations, damage claims, deduction hook | ✅ Production |
| `security_fleet` | Vehicles, shuttle routes, fuel/service logs, inspections | ✅ Production |
| `security_billing` | Billing plans, invoices, credit notes, aging, cron | ✅ Production |
| `security_accounting_controls` | Payment tracking, reconciliation, aging report | ✅ Production |
| `security_client_reports` | Client service reports, attendance exports | ✅ Production |
| `security_reporting` | Executive dashboard, payroll expenditure, AWOL heatmap | ✅ Production |
| `security_notifications` | Notification hub, email dispatch, bell widget, crons | ✅ Production |
| `security_ai_engine` | Multi-provider AI, 10 features, chat UI, tool-use | ✅ Production |
| `security_mobile` | REST API for all three mobile roles, push notifications | ✅ Production |
| `security_help` | Searchable help articles, contextual panel | ✅ Production |
| `security_licensing` | License enforcement, entitlement management | ✅ Production |
| `security_theme` | White-label branding, login customisation, PDF theming | ✅ Production |
| `security_demo_site` | Demo account management, auto-fill login chips | ✅ Production |
| `security_demo_data` | Namibian demo seed data (guards, sites, clients) | ✅ Production |
| `security_dogforce_migration` | CSV import tools for legacy data, dry-run validation | ✅ Production |
| `security_suite` | Meta-module installer for the complete suite | ✅ Production |

---

## Module detail

### `security_base`

**Purpose:** Core guard profile extensions on `hr.employee`.

**Models:**
- `hr.employee` extensions — `security_guard`, `security_grade_id`, `security_reliability_score`, `security_disqualified`, `security_mobile_pin_hash`, `security_mobile_device_token`, `security_mobile_last_login`
- `security.grade` — guard grade master (A/B/C/D)
- `security.certification` — certification types (Firearm, First Aid, etc.)
- `security.language` — language master
- `security.attribute` — attribute master (Height >1.8m, etc.)
- `security.schedule` — default work schedules

**Dependencies:** `hr`, `mail`

---

### `security_operations`

**Purpose:** Client → Site → Post → Shift Requirement → Roster Batch → Roster Slot hierarchy.

**Models:**
- `security.post.type` — post type with `min_grade_id`, `required_certification_ids`, `required_language_ids`, `required_attribute_ids`, `minimum_reliability_score`
- `security.client.site` — site with `partner_id`, `supervisor_id`, `post_ids`, `shift_requirement_ids`
- `security.post` — physical post at a site
- `security.shift.template` — named shift templates (Day 06:00–18:00, Night 18:00–06:00)
- `security.shift.requirement` — guards-per-shift requirement per site
- `security.site.requirement` — site-level requirement aggregate
- `security.guard.exclusion` — guard-must-never-be-at-site rules
- `security.roster.batch` — monthly roster container
- `security.roster.slot` — individual guard-post-date assignment
- `security.roster.generate.wizard` — wizard to generate a month of roster slots

**OWL Views:**
- Roster Board (`roster_board`) — Tier 3 full client action with drag-and-drop grid

**Dependencies:** `security_base`, `security_leave`

---

### `security_shift_planner`

**Purpose:** Constraint-satisfaction eligibility filter + scoring engine for intelligent guard assignment.

**Models:**
- `security.slot.suggestion` — scored guard ranking per slot: grade check, leave check, double-booking check, disqualification check, reliability score sort

**OWL Views:**
- Roster Board panel integration — `AIRosterSuggestionPanel` triggers from shift planner

**Key logic:** `_get_eligible_guards()` applies: grade ≥ minimum, certs valid, not on approved leave, not double-booked, not disqualified, no site exclusion. Guards are ranked by reliability score descending.

**Dependencies:** `security_operations`, `security_leave`, `security_documents`

---

### `security_attendance`

**Purpose:** Attendance batches (posting sheets) and individual attendance records with full shift-split computation.

**Models:**
- `security.attendance.batch` — posting sheet per site per day, states: draft → captured → locked
- `security.attendance.record` — one record per guard per shift: `check_in`, `check_out`, `manual_presence` (present/absent/awol), `late_minutes`, `overtime_hours`, `is_sunday`, `is_public_holiday`, `is_saturday`, `is_night_shift`, `normal_hours`, `sunday_hours`, `public_holiday_hours`, `saturday_hours`, `night_hours`

**OWL Views:**
- `posting_console` — Tier 3 attendance posting grid with inline mark buttons
- `awol_heatmap` — AWOL/absence pattern heatmap (Y=guards, X=days)

**Tests:** `tests/test_shift_split.py` — validates shift boundary calculation across midnight, Sunday, public holidays.

**Dependencies:** `security_operations`, `security_l10n_na`

---

### `security_leave`

**Purpose:** Leave types, employee balances, leave requests with roster slot blocking.

**Models:**
- `security.leave.type` — leave type config with accrual method, max balance, carryover policy
- `security.leave.balance` — per-employee balance per leave type
- `security.leave.request` — request with approval workflow, auto-deducts public holidays from consumed days

**Cron jobs:**
- Monthly leave accrual — calculates earned leave from worked hours
- Year-end carryover — applies carry/forfeit/payout policy per leave type

**Dependencies:** `security_base`, `security_l10n_na`

---

### `security_payroll_core`

**Purpose:** Full payroll pipeline from attendance buckets to confirmed payslips.

**Models:**
- `security.payroll.period` — period container, states: draft → generated → reviewed → confirmed → closed
- `security.payslip` — one per employee per period: reads 5-bucket attendance fields, computes earning lines, SSC, PAYE, deductions, anomaly flag
- `security.payslip.earning.line` — individual earning: normal/sunday/public_holiday/saturday/night/overtime hours × rate × multiplier
- `security.payslip.deduction.line` — individual deduction: SSC, PAYE, loan, incident, equipment damage, no-work-no-pay
- `security.payroll.period.wizard` — guided 2-step wizard: date range → employee preview → generate

**OWL Views:**
- `payroll_command_center` — Tier 3 wizard-style period manager with stepper bar, anomaly panel, bulk actions
- `payslip_preview` — full-screen preview modal matching PDF layout
- `payroll_expenditure` — payroll expenditure dashboard with site/grade breakdown

**Tests:**
- `tests/test_payroll.py` — unit tests for earning/deduction calculations
- `tests/test_payroll_e2e.py` — end-to-end: guard → roster → attendance → payslip
- `tests/test_payroll_pipeline.py` — full pipeline integration test
- `tests/test_anomaly_detection.py` — anomaly flag logic tests

**Key method:** `action_compute_from_sources()` on `security.payslip` reads attendance 5-bucket fields, creates earning lines per bucket, applies SSC/PAYE, pulls deductions, checks anomaly conditions.

**Dependencies:** `security_attendance`, `security_l10n_na`, `security_loans`, `security_discipline`, `security_equipment`

---

### `security_l10n_na`

**Purpose:** Namibia-specific payroll rules, tax brackets, public holidays, statutory reports.

**Models:**
- `security.payroll.rule.set` — multipliers: `sunday_multiplier`, `public_holiday_multiplier`, `overtime_multiplier`, `saturday_multiplier`, `night_multiplier`
- `security.paye.bracket` — PAYE tax bracket table (annual income thresholds and rates)
- `security.ssc.config` — SSC contribution rates and ceiling
- `security.public.holiday` — Namibia public holiday dates

**Reports:**
- NamRA PAYE employer monthly return (PDF/CSV)
- SSC monthly submission report (CSV)

**Utility:** `utils/shift_split.py` — `split_shift_by_boundaries(shift_start, shift_end, public_holidays)` returns `{normal_hours, sunday_hours, public_holiday_hours, saturday_hours, night_hours}` correctly handling midnight crossings and multi-day shifts.

**Dependencies:** `security_base`

---

### `security_loans`

**Purpose:** Employee loan management with installment schedules and payroll deduction hook.

**Models:**
- `security.employee.loan` — loan with state machine: draft → submitted → approved → active → closed → written_off; `deduction_priority` for multi-loan ordering
- `security.loan.deduction` — individual installment line with `carry_forward_amount` for capped periods

**Dependencies:** `security_base`, `security_payroll_core`

---

### `security_discipline`

**Purpose:** Incident tracking, reliability score adjustment, payroll deduction trigger.

**Models:**
- `security.incident.type` — type with `default_deduction_amount`, `reliability_score_delta`, `severity` (low/medium/high/critical), `high_trust_exclusion`
- `security.incident` — incident with approval workflow, `acknowledged` flag, appeal workflow fields (`appeal_state`, `appeal_reason`, `appeal_reviewed_by`)

**Inherits:** `mail.thread`, `mail.activity.mixin` on `security.incident` (enables chatter + attachments)

**Dependencies:** `security_base`, `security_payroll_core`

---

### `security_documents`

**Purpose:** Employee document management with expiry tracking and verification status.

**Models:**
- `security.document.type` — type with `is_firearm_cert` Boolean (unlocks extra fields), expiry rules
- `security.employee.document` — per-employee document: `expiry_date`, `verified`, firearm-specific fields when applicable

**Cron jobs:**
- Daily document expiry scan — sends notifications at 30/14/7 days to expiry via `security_notifications`

**Dependencies:** `security_base`, `security_notifications`

---

### `security_equipment`

**Purpose:** Equipment categories, guard allocations, damage claims, payroll deduction hook.

**Models:**
- `security.equipment.category` — category with type (uniform/radio/firearm/id) and `is_firearm` flag
- `security.equipment.allocation` — allocation with state machine: draft → issued → acknowledged → returned → damaged; `uniform_size`, `acknowledged_date`, `returned_date`
- `security.equipment.damage.claim` — damage/loss claim linked to allocation; approved claims create payroll deduction lines

**Dependencies:** `security_base`, `security_payroll_core`

---

### `security_fleet`

**Purpose:** Vehicle management, shuttle routes, fuel and maintenance tracking.

**Models:**
- `security.vehicle` — vehicle with registration, capacity, maintenance dates
- `security.shuttle.route` — named pickup/drop-off route
- `security.shuttle.run` — specific run on a date with driver and vehicle
- `security.shuttle.passenger` — guard on a run with pickup/drop-off points
- `security.fuel.log` — fuel fill record with litres and cost
- `security.vehicle.inspection` — pre/post-trip inspection checklist
- `security.vehicle.service.log` — scheduled and ad-hoc service records

**Dependencies:** `security_base`

---

### `security_billing`

**Purpose:** Client billing plans, invoice generation from attendance/roster, credit notes, payment terms.

**Models:**
- `security.billing.plan` — contract: `partner_id`, `site_ids`, `rate_per_shift`, `payment_term_days`, `auto_invoice`
- `security.billing.invoice` — invoice with state machine: draft → sent → paid → cancelled; VAT computation, `amount_in_words`
- `security.billing.invoice.line` — line item per post/shift
- `security.billing.credit.note` — linked to invoice; `action_apply()` reduces outstanding balance
- `security.invoice.generate.wizard` — guided invoice generation from billing plan + period

**Cron jobs:**
- Monthly recurring invoice generation for `auto_invoice = True` plans
- Invoice aging check — flags overdue invoices, triggers notifications

**OWL Views:**
- Invoice aging report widget (5 buckets: current/1–30/31–60/61–90/90+)

**Dependencies:** `security_attendance`, `security_operations`

---

### `security_accounting_controls`

**Purpose:** Payment recording, reconciliation, aged receivables.

**Models:**
- `security.client.payment` — payment against an invoice: `amount`, `payment_date`, `payment_method`, `payment_reference`
- `security.invoice.aging` — computed view of outstanding balances bucketed by age

**UI:** "Record Payment" wizard on billing invoice form.

**Dependencies:** `security_billing`

---

### `security_client_reports`

**Purpose:** Client-facing service reports and attendance exports.

**Models:**
- `security.client.service.report` — service report for a period/site: planned vs. actual shifts, attendance %, incident count, guard names (optional), client signature block

**Reports:**
- QWeb PDF with DogForce branding
- CSV attendance export (date, guard, post, times, status)

**Dependencies:** `security_attendance`, `security_billing`

---

### `security_reporting`

**Purpose:** Executive dashboards and management analytics.

**OWL Views:**
- `executive_dashboard` — Tier 3 full client action:
  - Operations tab: guard count, active sites, attendance rate, alert feed
  - Payroll tab: MTD gross/net, headcount, site-by-site breakdown
  - Discipline tab: incident counts, reliability trends
  - Billing tab: outstanding invoices, aging summary
  - Payment tab: payment history, collection rate
- `payroll_expenditure` — payroll cost by site/grade with month-on-month comparison
- `awol_heatmap` — absence pattern visual grid

**Post-init hook:** `set_security_home_action` — sets the executive dashboard as the default home action.

**Dependencies:** `security_payroll_core`, `security_billing`, `security_discipline`, `security_accounting_controls`

---

### `security_notifications`

**Purpose:** Unified notification hub — Odoo internal, email, Expo push.

**Models:**
- `security.notification` — notification record: `recipient_id`, `type`, `severity`, `message`, `read`, `send_email`, dispatch timestamp

**OWL Views:**
- `notification_bell` — systray widget showing unread count, dropdown of recent notifications, mark-all-read button

**Cron jobs:** Document expiry, leave approval events, billing overdue, incident approval, roster gap detection.

**Dependencies:** `security_documents`, `security_leave`, `security_billing`, `security_discipline`, `security_operations`

---

### `security_ai_engine`

**Purpose:** Centralised AI abstraction layer. All AI calls route through this module; business modules never import provider SDKs directly.

**Models:**
- `security.ai.engine` — AbstractModel; `complete(feature, system_prompt, user_message)` → `str | None`. Returns `None` if feature disabled or provider error.
- `security.ai.config` — one record per company: active provider, encrypted API key, model ID, master on/off
- `security.ai.log` — every call logged: feature, latency, tokens, cost estimate, success/failure
- `security.ai.cache` — response cache with TTL to avoid duplicate calls
- `security.ai.chat.session` — AI co-pilot conversation session
- `security.ai.chat.message` — individual message in a chat session

**Providers:** Claude (default: `claude-sonnet-4-6`), OpenAI (default: `gpt-4o`), Gemini (default: `gemini-1.5-pro`). All implement `AIProviderBase.complete()`.

**AI Features (10):**
1. `attendance_anomaly` — post-batch anomaly detection with corroboration from fleet logs
2. `risk_profiling` — daily guard risk score refresh + proactive alerts for high-risk guards at premium sites
3. `billing_audit` — invoice vs. actual attendance variance detection
4. `roster_optimizer` — 3 scored roster options (Cost / Reliability / Geography)
5. `shift_fill` — suggest best available guard for an open slot
6. `incident_advisor` — recommended disciplinary action from incident history
7. `leave_coverage` — suggest replacement when leave is approved
8. `doc_renewal` — proactive renewal reminders with prioritisation
9. `performance_review` — auto-draft performance summary from attendance + incidents
10. `payslip_explain` — plain-language payslip explanation for guards

**Tool-use (7 tools available to AI):**
- `search_records`, `count_records`, `get_record` — read-only ORM access
- `get_dashboard_kpis`, `get_pending_actions` — operational context
- `navigate_to` — direct the UI to a specific record
- `propose_update`, `propose_method` — suggest (not apply) data changes

**REST endpoints:**
- `POST /web/ai-chat/message-lite` — lightweight chat without full session
- `POST /web/ai-chat/message` — full agentic chat with tool-use
- `POST /web/ai-chat/confirm` — execute a proposed action after human approval
- `GET /web/ai-chat/history` — conversation history
- `POST /web/ai-chat/new-session` — start a new chat session

**OWL Views:**
- `ai_chat_panel` — floating chat widget with tool-use visualisation
- `ai_output_widget` — renders structured AI responses (tables, alerts, buttons)
- `ai_admin_config` — Tier 3 configuration UI: provider, API key, feature flags, usage stats

**Safety:** AI returns structured proposals; Odoo ORM executes them. No raw SQL. Users only see/act on records their group permits.

**Dependencies:** `security_base` (all features depend on it)

---

### `security_mobile`

**Purpose:** REST API backend for the DeployGuard mobile app (supervisor, manager, owner roles).

**Controllers:**

`supervisor.py`:
- `GET /api/security/mobile/supervisor/today` — today's posting sheet for the logged-in supervisor
- `POST /api/security/mobile/supervisor/mark` — mark presence (present/absent/awol) + check-in/out times
- `POST /api/security/mobile/supervisor/checkin` — quick check-in/check-out timestamp
- `POST /api/security/mobile/supervisor/batch/submit` — submit the posting sheet batch

`manager.py`:
- `GET /api/security/mobile/manager/dashboard` — all-sites attendance summary
- `GET /api/security/mobile/manager/site/<site_id>` — detailed roster for one site
- `GET /api/security/mobile/manager/overtime` — pending overtime list
- `POST /api/security/mobile/manager/overtime/approve` — approve/reject overtime

`owner.py`:
- `GET /api/security/mobile/owner/kpis` — executive KPIs (attendance rate, payroll YTD, incidents, invoices)
- `GET /api/security/mobile/owner/calendar` — roster calendar summary
- `GET /api/security/mobile/owner/sites` — all sites overview
- `GET /api/security/mobile/owner/guards` — guard roster list
- `GET /api/security/mobile/owner/site/<site_id>` — site detail
- `GET /api/security/mobile/owner/guard/<guard_id>` — guard profile
- `GET /api/security/mobile/owner/live` — live operational view

`main.py`:
- PIN authentication endpoint for quick re-auth after session expiry

`notifications.py`:
- Expo push notification helpers; sends FCM when supervisors submit batches

**Auth:** Odoo session cookie + `X-Openerp-Session-Id` header. Session ID stored in `expo-secure-store` on device.

**Dependencies:** `security_attendance`, `security_operations`, `security_payroll_core`

---

### `security_help`

**Purpose:** In-app help centre with searchable articles and contextual help panels.

**Features:** Topic-categorised articles with Odoo portal renderer, context-sensitive help triggered from module menus.

**Dependencies:** `security_base`

---

### `security_licensing`

**Purpose:** DeployGuard OS license enforcement and feature entitlement management.

**Models:** License keys, entitlement tiers, feature flags tied to license state.

**Dependencies:** `security_base`

---

### `security_theme`

**Purpose:** White-label branding, theme presets, login page customisation, PDF report theming.

**Features:** DogForce colour palette, custom login card, logo injection, light/dark/high-contrast presets, PDF header/footer template variables.

**Dependencies:** (none — pure theme)

---

### `security_demo_site`

**Purpose:** Demo account management and auto-fill login chips for demos.

**Features:** Login page "Demo access" chips (Owner / Manager / Supervisor) that inject credentials without typing; post-login redirect to Security Suite home.

**Dependencies:** `security_base`

---

### `security_demo_data`

**Purpose:** Reusable Namibian demo seed data — guards, clients, sites, grades, certifications, billing plans, attendance records.

**Dependencies:** All core modules

---

### `security_dogforce_migration`

**Purpose:** One-time and incremental data migration from the legacy DogForce Odoo instance.

**Features:**
- CSV import templates with column mapping for: employees, clients, sites, leave balances, outstanding loans, open invoices
- `dry_run` Boolean — validates entire CSV without writing to the database; returns row-level error report
- Import validators: duplicates, missing required fields, referential integrity
- `created_ids` JSON field on each migration job — powers the "Rollback Import" action

**Dependencies:** All core modules

---

### `security_suite`

**Purpose:** Meta-module that installs the complete DogForce Security Services Suite in one click.

**Dependencies:** All modules above

---

## Key data flows

### Attendance → Payroll

```
security.roster.slot (planned shift)
  └─▶ security.attendance.record
        ├─ _compute_shift_buckets()  →  normal_hours, sunday_hours, ph_hours, saturday_hours, night_hours
        │   (via split_shift_by_boundaries from security_l10n_na)
        └─▶ security.payslip.earning.line  (one per bucket > 0)
              └─▶ security.payslip  →  SSC + PAYE + deductions → net pay
```

### Roster generation

```
security.roster.generate.wizard
  └─▶ security_shift_planner._get_eligible_guards()
        ├─ grade check
        ├─ certification expiry check
        ├─ leave check
        ├─ double-booking check
        ├─ disqualification check
        └─ site exclusion check
        └─▶ sort by reliability_score desc
              └─▶ security.roster.slot (created)
```

### AI request lifecycle

```
Any module calls:
  self.env["security.ai.engine"].complete(feature="...", ...)
    ├─ check security.ai.config (master toggle + feature flag)
    ├─ check security.ai.cache (return cached if hit)
    ├─ call provider.complete() → Claude / OpenAI / Gemini
    ├─ log to security.ai.log
    └─▶ return str  (or None on failure — caller handles gracefully)
```

---

## Mobile app structure

```
mobile/
├── app/
│   ├── (auth)/login.tsx
│   ├── (supervisor)/  index.tsx  mark/[recordId].tsx  history.tsx
│   ├── (manager)/     index.tsx  site/[siteId].tsx    overtime.tsx
│   └── (owner)/       index.tsx
├── src/api/           client.ts  auth.ts  supervisor.ts  manager.ts  owner.ts
├── src/stores/        authStore.ts  appStore.ts
└── src/theme/         index.ts
```

Auth: `POST /web/session/authenticate` → session_id stored in `expo-secure-store` → injected as `Cookie` + `X-Openerp-Session-Id` on every request.

Demo mode: three chips on login screen inject mock sessions without touching the API.

---

*Keep this document in sync when adding models, controllers, or OWL components to any module.*
