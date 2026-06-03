# DogForce Security Suite — Platform Master Plan

**Version:** 1.0  
**Date:** 2026-05-31  
**Author:** Winston Zulu  
**Status:** Active — Use this as the single source of truth for all build decisions.

---

## Table of Contents

1. [Vision & Principles](#1-vision--principles)
2. [Gap Analysis — Missing Features Per Module](#2-gap-analysis--missing-features-per-module)
3. [Missing Modules to Add](#3-missing-modules-to-add)
4. [Automation Strategy](#4-automation-strategy)
5. [Custom Views Architecture — OWL Tier System](#5-custom-views-architecture--owl-tier-system)
6. [Module-by-Module View Redesigns](#6-module-by-module-view-redesigns)
7. [Payroll, Payslip & Attendance Deep Improvements](#7-payroll-payslip--attendance-deep-improvements)
8. [AI Integration Layer — Multi-Provider Strategy](#8-ai-integration-layer--multi-provider-strategy)
9. [AI Feature Specifications](#9-ai-feature-specifications)
10. [Intent-Based Interaction Model](#10-intent-based-interaction-model)
11. [Implementation Sequence](#11-implementation-sequence)

---

## 1. Vision & Principles

### 1.1 Platform Vision

This is not an ERP configuration project. It is an **intelligent operational platform** for private security companies. The system does the work; the human approves, adjusts, or overrides. The human is never the data-entry clerk.

The target experience: a field supervisor opens their phone, sees today's posting sheet pre-filled from the roster, taps Present/Absent for each guard, and submits in under 2 minutes. An AI flags the one anomaly. The manager approves it. Payroll for that shift is already accounted for.

### 1.2 Design Principles

| Principle | What It Means in Practice |
|-----------|--------------------------|
| **Intent over CRUD** | Users declare what they want ("Plan June roster"). The system handles the how. |
| **Beginner-friendly, expert-powerful** | A new supervisor can complete their daily workflow in under 5 minutes without training. A payroll officer can drill into any computation. |
| **Automate the predictable** | If a task runs the same way every time (monthly accrual, invoice generation, document expiry alerts), a cron does it. Humans only touch exceptions. |
| **AI is optional, not required** | Every AI feature has an on/off flag. The system works fully without AI. AI makes it faster and smarter, not fragile. |
| **Auditability is a product feature** | Every override, approval, AI suggestion acceptance, and payroll computation is logged with user + reason + timestamp. |
| **Country-neutral core** | Namibia rules live in `security_l10n_na`. The operational core works for any country. Zambia deployment adds `security_l10n_zm`, nothing else changes. |
| **Test-driven payroll** | Every statutory calculation has an automated test. Payroll is too high-stakes for manual verification alone. |

---

## 2. Gap Analysis — Missing Features Per Module

### `security_base`

**Currently built:** Guard profile extensions on `hr.employee`, grades, certifications, languages, attributes, reliability score, disqualification, mobile pin/device token fields.

**Missing features:**

- **Certification expiry date per guard** — currently `expiry_required` Boolean exists only on the certification *type*, not on the guard's assignment. Need `security.employee.certification` join model with `expiry_date`, `document_id`, and `verified` fields.
- **Emergency contact fields** — name, relationship, phone number. Critical for operational safety, legally required in some jurisdictions.
- **Home location as geo coordinates** — currently stored as freetext `Char`. Needs `home_latitude` and `home_longitude` float fields for AI roster distance scoring.
- **Guard availability calendar** — "Guard X is unavailable Mondays" distinct from leave. A `security.guard.availability` model with day-of-week patterns.
- **`on_notice` status flag** — guard is serving a notice period: still assignable but flagged. Includes `notice_effective_date` and `notice_end_date`.
- **Language proficiency level** — currently a flat many2many tag. Needs a join model with proficiency level (Basic / Conversational / Fluent) per language per guard.
- **Medical fitness expiry** — currently freetext `security_medical_fitness_grade`. Needs `medical_fitness_expiry_date` and link to document record.
- **Performance review model** — `security.performance.review` with reviewer, score, notes, and reliability score impact.
- **Payslip history tab** — last 12 payslips visible directly on the guard's employee form (computed One2many via period).
- **Guard headcount report** — active guards by grade, broken down by site assignment.

---

### `security_operations`

**Currently built:** Client → Site → Post → Shift Requirement → Roster Batch → Roster Slot hierarchy. Grade/cert/leave/disqualification validation. Supervisor override with reason.

**Missing features:**

- **Monthly roster generation wizard** — the single most critical gap. A guided wizard: select month + site(s) → system generates slots from eligible guards using constraint-satisfaction logic → supervisor reviews and confirms. ADR-012 deferred this; it must be built now as `security_shift_planner`.
- **Site-specific guard exclusion rules** — `security.site.guard.exclusion` model: "Guard X must never be assigned to Client Y's Site Z." Checked during roster generation and manual assignment.
- **Fairness score warnings** — system warns when one guard is accumulating disproportionate Sunday/holiday/night shifts relative to peers with similar eligibility.
- **Bulk roster copy** — duplicate last month's roster as a draft starting template for the next month. Saves the most common case (same guards, same posts).
- **Roster approval workflow** — draft → submitted → approved state machine. Operations Manager approves a complete monthly roster before it becomes the source of truth for attendance generation.
- **Roster calendar view** — see all slots as a visual week/month calendar (not just a list). Built as the Roster Board OWL component (see Section 6).
- **Understaffing notification wired** — the model field `understaffing_alert` exists but no scheduled action or notification sends it to anyone. Wire to `security_notifications`.
- **Supervisor-per-site tracking** — which supervisor is responsible for which site on which shift/day. Needed for notification routing and mobile access scoping.
- **Guard preferred pool per site** — a "preferred guards" list on `security.client.site` that the auto-roster fills first before drawing from the general pool.
- **`min_guards` vs `required_guards`** on shift requirements — minimum acceptable staffing vs. full contract requirement, so understaffing alerts can distinguish critical shortfall from minor shortfall.

---

### `security_attendance`

**Currently built:** Batch/posting sheet model, attendance records with scheduled vs. actual metrics, late/early/AWOL/overtime calculations, Sunday and public holiday calendar flags.

**Missing features:**

- **Bulk inline batch entry UI** — supervisors currently open each record individually. Need a spreadsheet-style inline grid where the entire posting sheet is one screen: one row per guard, status + times editable in-place. This is the Attendance Posting Console (Section 6).
- **Supervisor dashboard** — a single screen showing all of the logged-in supervisor's sites' status for today: how many marked, how many missing, how many AWOL, any overtime pending approval.
- **Night shift flag** — `is_night_shift` Boolean on `security.attendance.record` for shifts with `scheduled_start` between 18:00 and 06:00. Required for night premium payroll calculation.
- **Saturday flag** — `is_saturday` Boolean, similar to `is_sunday`. Required for Saturday premium.
- **Shift split fields** — `normal_hours`, `sunday_hours`, `public_holiday_hours`, `saturday_hours`, `night_hours` stored directly on the attendance record (computed by the split utility). The current `premium_category` single-value field is insufficient for shifts crossing boundaries.
- **Attendance correction request workflow** — guard or supervisor disputes a record → second supervisor/manager reviews → reason logged. Currently corrections are made directly with no approval layer.
- **Absence reason categorisation** — beyond `awol` vs. `no_show`, need: sick (with/without medical certificate), family emergency, transport failure, disciplinary suspension, authorised absence. Each has different payroll treatment.
- **Late pattern detection** — computed flag: "This guard has been late more than 3 times in 14 days." Surfaces in the AI risk profiling and supervisor dashboard.
- **Cross-batch weekly summary** — attendance percentage per guard per site per week, visible from the batch list view without needing to run a separate report.
- **GPS timestamp storage hook** — `check_in_gps_lat`, `check_in_gps_lng` float fields, nullable. No GPS device required in Phase 1 but the schema is ready for Phase 2.

---

### `security_leave`

**Currently built:** Leave types, employee balances, leave requests, approval workflow, roster slot blocking for approved leave.

**Missing features:**

- **Leave accrual cron** — currently no automated monthly accrual. Need a scheduled action that calculates earned leave from worked hours in the period and writes to balance records.
- **Leave balance dashboard widget** — per-employee view of all leave types: earned, used, remaining, projected to year-end. OWL widget on the employee form and on the employee's self-service view.
- **Multi-type balance table** — Annual / Sick / Maternity / Compassionate all visible in one table, not separate records to navigate.
- **Leave calendar** — visual month view of approved leave across all guards, colour-coded by leave type. Managers can spot coverage gaps immediately.
- **Leave carryover rules** — configurable: carry over up to N days / forfeit / pay out at year-end. Currently no year-end logic.
- **Leave encashment** — convert unused annual leave balance to a cash earning line at period close. Relevant for guards resigning or at contract end.
- **Specific leave types with rules** — Maternity (84 days, Namibia Labour Act), Sick (30 days/year cap), Compassionate (3 days per event), Compensatory (overtime converted to leave).
- **Public holiday auto-detection in leave** — if a public holiday falls within an approved leave period, that day must not consume a leave day. Currently not handled.
- **Leave substitution** — when approving leave, system suggests available replacements for the guard's roster slots during the leave period.
- **Negative balance cap enforcement** — the architecture mentions this but no constraint validation exists on the balance model.

---

### `security_payroll_core`

**Currently built:** Payroll periods, payslips, earning and deduction line models, SSC/PAYE calculations, normal/Sunday/holiday/overtime hours, loan deduction hook, incident deduction hook.

**Missing features:**

- **Night shift premium earning line** — `is_night_shift` hours at configurable multiplier. Currently the entire shift gets classified as normal unless it's a Sunday/holiday.
- **Saturday premium earning line** — separate Saturday multiplier. Currently treated as normal.
- **Shift split integration** — `action_compute_from_sources()` reads `premium_category` (one field) from attendance. Needs to read the 5-bucket fields (`normal_hours`, `sunday_hours`, `ph_hours`, `saturday_hours`, `night_hours`) after the split utility runs.
- **Payslip preview screen** — before confirming, the HR officer sees a screen that matches the PDF layout exactly, with: totals, comparison to previous period, anomaly flags (>20% net pay change, missing SSC number, missing bank details).
- **Batch payslip email delivery** — `action_print_payslips()` prints. Also need `action_email_payslips()` that sends each payslip PDF to the guard's work email or the supervisor's email for distribution.
- **Management payroll summary report** — a one-page A4 report: headcount, total normal hours, Sunday hours, holiday hours, total gross, total deductions broken by category (SSC, PAYE, loans, incidents, equipment), total net. By site and company total.
- **Excel export of payroll register** — all employees × all earning/deduction lines in one flat table. Finance reconciliation requirement.
- **Payroll period wizard** — guided UI: select dates → confirm rule set → preview eligible employees → generate in one click.
- **Payslip history on employee form** — last 12 payslips with net pay + one-line earning summary, accessible from the guard profile.
- **Equipment damage deduction integration** — `security_equipment` extends `security.payslip` via `_inherit`, but this hook needs to be verified and tested end-to-end.
- **Deduction cap logic** — if loan + incident + equipment deductions would take net pay below zero (or below a configurable minimum), cap the deduction and carry the excess to the next period.
- **Anomaly detection flag** — `anomaly_flag` Boolean + `anomaly_reason` Char on `security.payslip`. Set by `action_compute_from_sources()` when net pay changes >20% vs. previous period, attendance hours are zero, or statutory numbers are missing.

---

### `security_l10n_na`

**Currently built:** Rule sets with Sunday/holiday/overtime multipliers, PAYE bracket model, SSC rate/cap configuration, public holiday model.

**Missing features:**

- **Confirmed 2025/2026 Namibian public holiday data** — the model exists but the actual holiday dates must be loaded as XML/CSV data records. Verify against the Namibia Public Holidays Act.
- **Saturday premium multiplier field** on `security.payroll.rule.set` — currently no field for Saturday rate.
- **Night shift premium multiplier field** on rule set — currently no field for night rate.
- **`split_shift_by_boundaries()` utility** — the single most critical missing computation. A Python function that takes `(shift_start: datetime, shift_end: datetime, public_holidays: list[date])` and returns `{normal_hours, sunday_hours, ph_hours, saturday_hours, night_hours}`. Handles midnight crossings and shifts spanning multiple calendar days.
- **NamRA PAYE employer monthly return report** — formatted PDF/CSV matching the NamRA submission format.
- **SSC monthly submission report** — formatted CSV/PDF matching the Social Security Commission submission format.
- **Namibia invoice legal footer** — the required legal text for Namibian VAT invoices stored as a configurable data record, not hardcoded.
- **NAD number-to-words utility** — proper Namibian format including cents (e.g., "Two Thousand Six Hundred Seventy Namibia Dollars and 34 Cents"). Currently `amount_in_words` on invoices is a rough approximation.

---

### `security_loans`

**Currently built:** (Per architecture) Employee loan schedules, payroll deduction hooks, balance tracking.

**Missing features:**

- **Loan application workflow** — guard/HR submits loan application → Operations Manager approves → HR activates → payroll deducts automatically. Currently no request state machine.
- **Loan statement PDF** — guard-facing document showing: loan amount, disbursement date, all installments paid to date, remaining balance, projected payoff date.
- **Early settlement** — compute and apply a lump-sum payoff in the current period, close the loan, notify HR.
- **Multiple concurrent loans with deduction priority** — if a guard has 2 active loans, define which is deducted first. Priority field on loan record.
- **Loan limit by grade policy** — configurable: Grade A max N$10,000, Grade C max N$3,000. Enforced at application.
- **Deduction cap** — if total loan installments would reduce net pay below a configured minimum floor (e.g., 30% of gross), cap the deduction for this period and carry the difference forward.
- **Loan write-off approval** — manager/accountant approves writing off an uncollectable balance. Full audit trail.

---

### `security_discipline`

**Currently built:** Incident types with deduction/reliability delta, incident records with approval workflow, reliability score update on approval, payslip link.

**Missing features:**

- **Evidence attachments** — the incident record needs `ir.attachment` integration so supervisors can attach photos, written statements, or CCTV screenshots to the incident record.
- **Employee notification and acknowledgment** — after incident approval, the guard (or their supervisor on their behalf) must receive a formal notice and acknowledge receipt. Logged on the incident.
- **Appeal workflow** — guard challenges the incident → second-level manager reviews → outcome (upheld / overturned) logged. If overturned: reliability score reversed, payroll deduction reversed.
- **Progressive discipline tracking** — `SecurityIncidentType` needs a `severity` field. Three offences of severity "Medium" within 90 days auto-triggers a "Suspension Recommended" flag on the guard profile.
- **`high_trust_exclusion` check in roster validation** — the flag exists on `security.incident` but `security.roster.slot` assignment validation does not currently check whether the guard has an active `high_trust_exclusion` incident. Must be wired.
- **Deduction amount override at record level** — the incident type sets a default deduction; the specific incident record should allow the approver to set a different amount with a reason (e.g., partial deduction for mitigating circumstances).
- **Reliability score history graph** — OWL widget on the guard profile showing the 12-month trend of the reliability score, not just the current integer.

---

### `security_billing`

**Currently built:** Billing plans with line items, invoice model with generation from roster/attendance, VAT computation, amount-in-words, state machine (draft/sent/paid/cancelled).

**Missing features:**

- **Monthly invoice generation wizard** — a guided UI wizard: select billing plan + period month → preview generated lines from roster or attendance → confirm and create invoice. One screen, one click.
- **Recurring invoice cron** — scheduled action that generates invoices for all active billing plans marked `auto_invoice = True` at the start of each billing period. Creates them in draft for review before sending.
- **Invoice email template** — send the PDF invoice to the client's billing contact with a configurable covering letter template. Button on the invoice form.
- **Credit notes** — `security.billing.credit.note` model linked to the original invoice. Adjusts a sent invoice for partial credit (e.g., understaffing dispute reconciliation).
- **Billing vs. actuals reconciliation alert** — compare invoice guard count × days against actual attendance records for the same period/site. Flag overbilling or underbilling variance in NAD. Surfaced in the AI Billing Auditor (Section 9).
- **Invoice aging report** — 30/60/90+ days outstanding table, exportable to PDF/Excel.
- **Named payment terms** — `security.payment.term` model (Net 7 / Net 14 / Net 30 / EOM) linked to billing plans. Currently only a raw integer field.
- **Proper Namibian invoice sequence** — format `INV/YYYY/NNNN` (e.g., `INV/2026/0047`). Currently uses `ir.sequence` but the format may need tightening.
- **Partial invoice support** — invoice a subset of posts/sites within a billing plan for a period (e.g., mid-month contract start).

---

### `security_accounting_controls`

**Currently built:** (Per architecture) Client payment tracking, invoice aging, reconciliation status on billing invoices.

**Missing features:**

- **Bank statement import** — CSV/OFX import of bank statement lines with field mapping configuration. Needed for matching payments to outstanding invoices.
- **Payment reconciliation UI** — match an imported bank statement line to one or more outstanding invoices. Record partial payments and overpayments.
- **Write-off approval workflow** — small differences (< configurable threshold) auto-approve; above threshold requires Accounting Manager sign-off. Full audit trail per write-off.
- **Bank account detail change approval** — any change to client or company bank details requires dual approval (two different users). The change is logged with before/after values, both approvers, and timestamp.
- **Report export audit log** — when any user exports a financial report (PDF/Excel), log: user, timestamp, report type, filter parameters applied.
- **Aged receivables PDF export** — formatted report matching Namibian professional presentation standard.
- **Daily cash position report** — summary of payments received vs. outstanding per day.

---

### `security_client_reports`

**Currently built:** (Per architecture) Client attendance and service report models.

**Missing features:**

- **Client service report PDF** with DogForce branding — shows: period, site, posts, guard names (optional), planned vs. actual shifts, attendance percentage, incidents if any. Designed for professional client delivery.
- **Excel attendance export** — flat table of all attendance records for the period/site, formatted for client's own analysis.
- **Client portal access** — clients log into Odoo portal, see their own sites, download invoices and service reports. No raw data exposed.
- **Report scheduling** — configurable auto-send: monthly service report emailed to client billing contact on period close.
- **Shift-level drill-down** — client can see per-shift detail (post, time, guard name or ID, status) on the portal, not just aggregates.

---

### `security_reporting`

**Currently built:** Pivot and graph views on existing models.

**Missing features:**

- **Executive KPI Dashboard** — full OWL client action (see Section 6). Replaces the need to navigate separate menu items to get a management overview.
- **Payroll expenditure dashboard** — gross pay by site, by grade, by premium category, with month-on-month comparison.
- **AWOL/absence heatmap** — visual grid: guards on Y axis, days on X axis, colour by attendance status. Immediately shows patterns.
- **Guard reliability leaderboard** — top 20 and bottom 20 guards by reliability score with 90-day trend arrows.
- **Overtime cost analysis** — total approved overtime hours and cost by site, by guard, trending over 12 months.
- **Loan deduction totals by period** — for finance reconciliation.
- **Incident deduction totals by type and period** — for discipline reporting.
- **Headcount trend** — active guards over the last 12 months (hires vs. departures).

---

### `security_documents`

**Currently built:** Document types, expiry tracking, verification status, attachments.

**Missing features:**

- **Firearm certificate as first-class document type** — with additional fields: weapon type, calibre, licence number, issuing authority, next inspection date. Linked to roster eligibility check.
- **Document type → post type requirement mapping** — `security.post.type` should list required document types. Roster assignment checks: "Does this guard have all required documents for this post type, and are they current?"
- **Document expiry cron** — daily scheduled action: find documents expiring in 30 / 14 / 7 days → send notification to HR and site supervisor via `security_notifications`.
- **Compliance dashboard** — list of all guards with documents expiring in the next 30 days, grouped by document type and site.
- **Missing document block on roster assignment** — if a guard is missing a required document for the target post, assignment is blocked (with override option + reason logging).
- **Mobile document upload** — supervisor can photograph a document on-site and attach it to the guard's record via the mobile app.
- **Bulk document verification** — HR can mark multiple documents as Verified in one batch action, not one-by-one.

---

### `security_equipment`

**Currently built:** Equipment categories, allocations to guards, damage claims, payroll deduction hook.

**Missing features:**

- **Equipment issuance workflow** — state machine: draft → issued → acknowledged. Guard (or supervisor on their behalf) must confirm receipt before equipment is considered issued. Confirmation logged with date and user.
- **Return/handback workflow** — state machine: return requested → inspected → condition assessed (Good / Damaged / Lost) → closed. If damaged/lost, auto-trigger damage claim.
- **Damage claim approval before payroll deduction** — currently unclear whether deduction requires explicit approval. Needs a clear: damage claim → manager approves → payroll deduction activated.
- **Equipment inventory count per category per site** — how many radios/uniforms/firearms are allocated to Site A right now.
- **Uniform sizing** — `uniform_size` field on employee (S/M/L/XL/XXL) and on equipment allocation. Prevents issuing wrong size.
- **Firearm as special category** — serial number, licence number, last inspection date, next inspection due. Separate model with stricter audit logging.
- **Bulk issuance** — issue standard new-guard kit (uniform + radio + ID) to multiple guards in a single batch action.

---

### `security_fleet`

**Currently built:** Vehicles, shuttle routes/runs/passengers, fuel logs, inspections, service logs, fleet incident link.

**Missing features:**

- **Driver licence tracking per guard** — separate from firearm cert. `driver_licence_number`, `driver_licence_expiry`, `driver_licence_class` fields on `hr.employee` (via fleet module extension).
- **Vehicle availability calendar** — is this vehicle already assigned to a run at the requested time? Conflict detection.
- **Shuttle passenger manifest PDF** — printable document for the driver showing all scheduled passengers, pickup points, and drop-off points for a run.
- **Fuel cost analysis** — cost per km per vehicle, by month, by route. Needed for fleet expense reporting.
- **Vehicle maintenance schedule** — service due at N km or N months, whichever first. Alert when due date approaches.
- **Fleet cost report by vehicle** — fuel + maintenance + incident repair costs over a period.
- **GPS tracking hook** — `last_known_latitude`, `last_known_longitude`, `last_gps_update` fields on `security.vehicle`. Not wired in Phase 1 but schema ready for Phase 2 hardware.

---

### `security_mobile`

**Currently built:** REST API for supervisor posting sheet, manager multi-site dashboard, owner KPI endpoints. Session authentication, role-group access control.

**Missing features:**

- **Push notifications via FCM** — `security_mobile_device_token` field exists on `hr.employee` but no code sends push messages. Must be wired to `security_notifications` module.
- **Offline posting sheet** — mark attendance when there is no network; sync when reconnected. Requires local SQLite cache in Expo and a sync endpoint with conflict resolution.
- **Guard self-service screens** — a guard can view their own payslip PDF, check their leave balance, see their upcoming roster schedule.
- **Leave application from mobile** — guard submits a leave request from the app → supervisor receives push notification → approves/rejects from mobile.
- **Equipment handover confirmation** — guard taps "I confirm receipt of equipment" from mobile; this writes the acknowledgment to the allocation record.
- **Incident reporting from mobile** — supervisor files an incident report on-site, attaches a photo.
- **AI Co-pilot mobile endpoint** — `POST /security/mobile/copilot` accepts a natural language query string, returns a structured response payload that the mobile app renders as a widget.
- **Overtime approval from mobile** — manager receives push for pending overtime → approves or rejects with one tap + optional note.
- **Manager roster view** — manager can see the current month's roster for any of their sites on mobile.

---

## 3. Missing Modules to Add

### `security_ai_engine` *(New — highest strategic value)*

**Purpose:** Centralised AI abstraction. All AI calls route through this module. Business modules never import Anthropic/OpenAI/Gemini SDKs directly. The company admin can switch providers or disable AI entirely without touching business logic.

**Models:**
- `security.ai.config` — one record per company: active provider, encrypted API key, model ID, master on/off toggle
- `security.ai.feature.flag` — per-feature on/off (roster optimizer, risk profiling, anomaly detection, billing auditor, co-pilot)
- `security.ai.request.log` — every AI call logged: feature key, input length, output length, latency ms, success/failure, estimated cost
- `security.ai.feedback` — thumbs up/down on any AI suggestion, with free-text reason. This is the training signal for prompt improvement.

**Provider abstraction:**
```python
class AIProviderBase:
    def complete(self, system_prompt: str, user_message: str,
                 max_tokens: int = 1000, temperature: float = 0.3) -> str: ...

class ClaudeProvider(AIProviderBase):   # uses anthropic SDK
class OpenAIProvider(AIProviderBase):   # uses openai SDK
class GeminiProvider(AIProviderBase):   # uses google-generativeai SDK
```

**Abstract model callable from any module:**
```python
result = self.env["security.ai.engine"].complete(
    feature="roster_optimizer",
    system_prompt="...",
    user_message="...",
)
# Returns None if feature disabled or AI not configured.
# Business logic handles None gracefully.
```

---

### `security_notifications` *(New)*

**Purpose:** Unified notification dispatch — in-app Odoo chatter, email, FCM push, and a future SMS gateway hook. All other modules call this module; none implement notification logic themselves.

**Models:**
- `security.notification.template` — named templates (e.g., "Document Expiry Warning", "Understaffing Alert", "Payroll Ready for Review") with subject, body (QWeb), and enabled channels
- `security.notification.log` — every dispatched notification logged with recipient, channel, template, timestamp, and delivery status

**Triggered by:** Scheduled crons, workflow state changes (incident approved, roster published, payroll period closed), AI anomaly detections.

---

### `security_portal` *(New)*

**Purpose:** Client self-service portal. Clients log into Odoo's standard portal and see only their own data.

**Features:**
- View and download their invoices (PDF)
- View their site attendance/service reports for any period
- Download monthly service summary
- Submit queries or billing disputes (creates a helpdesk ticket or chatter message)

**Implementation:** Extends `website`/Odoo portal controllers. All data access is scoped to the client's `res.partner` record via record rules. No guard personal data visible to clients unless explicitly included in the service report template.

---

### `security_shift_planner` *(New — extracts roster intelligence from `security_operations`)*

**Purpose:** The scheduling engine, separated from `security_operations` so the optimization logic can evolve independently (add AI, add constraint solvers) without modifying the core operational module.

**Features:**
- **Constraint-satisfaction filter** — pure Python, no AI. Produces a candidate list for each slot: guards who are eligible (grade ✓, certs ✓, not on leave ✓, not disqualified ✓, rest rules ✓, site exclusion ✓)
- **Scoring engine** — ranks candidates by: reliability score (weight 40%), distance to site (weight 20%), fairness rotation index (weight 20%), grade-to-post fit (weight 20%)
- **AI optimizer hook** — optionally calls `security_ai_engine` to post-process the scored candidates and return 3 named options (Lowest Cost / Highest Reliability / Best Geographic Match)
- **Conflict detector** — runs on a complete draft roster and produces a list of all violations with severity (blocking vs. warning)
- **Monthly generation wizard** — the UI entry point (OWL wizard component) that invokes the planner for a month/site selection

---

### `security_analytics` *(New)*

**Purpose:** Advanced analytics and exportable management packs. Extends `security_reporting` without replacing it.

**Features:**
- **Monthly management pack** — one-click PDF generation with all key metrics for a period: attendance rate, payroll summary, top incidents, billing summary, outstanding invoices
- **12-month payroll trend chart** — OWL chart component, rendered server-side data
- **Guard reliability trend** — per-guard 12-month reliability score sparkline
- **Client billing vs. actuals variance analysis** — detailed comparison table per site per period
- **Full Excel export** — payroll register, attendance register, incident register — one call, three sheets

---

### `security_dogforce_migration` *(Planned — build now)*

**Purpose:** One-time and incremental data migration from the existing DogForce Odoo instance. Completely isolated so it does not contaminate reusable modules.

**Features:**
- CSV import templates (with column mapping documentation) for: employees, clients, sites, leave balances, outstanding loans, open invoices
- Import validators that check for duplicates, missing required fields, and referential integrity before writing any records
- Migration run log — every record created/updated/skipped during an import, with reason
- Rollback flag — mark all records created in a migration run so they can be bulk-deleted if the migration is bad and needs to be retried

---

### `security_l10n_zm` *(Future — scaffold now)*

**Purpose:** Zambia localization pack. Scaffold the module with empty rule sets now to validate the architecture decision: Zambia deployment should require zero changes to core modules.

**Structure mirrors `security_l10n_na`:** rule set record, empty PAYE bracket table, empty SSC equivalent, empty public holiday list, empty VAT rate.

---

## 4. Automation Strategy

The goal is to eliminate every manual batch trigger that can be safely automated. Users touch exceptions; crons handle the routine.

### 4.1 Scheduled Actions (Odoo `ir.cron`)

| Job Name | Schedule | Logic |
|----------|----------|-------|
| **Document Expiry Warnings** | Daily 07:00 | Find all `security.employee.certification` records with `expiry_date` in next 30/14/7 days → notify HR and site supervisor via `security_notifications` |
| **Daily Understaffing Alert** | Daily 06:00 | For each site with shifts today, compare rostered slot count vs. `required_guards` on shift requirement → notify Operations Manager for any shortfall |
| **Missing Checkout Alert** | Daily 22:00 | Find all `security.attendance.record` with `check_in` set, `check_out` null, `shift_date = today` → notify supervisor |
| **AWOL Detection** | Daily 10:00 | Find guards scheduled today, not yet marked, whose shift started > 2 hours ago → flag as `potential_awol`, notify supervisor |
| **AI Risk Score Refresh** | Daily 03:00 | If AI enabled: recompute `ai_risk_score` for all active guards from attendance + incident patterns → update field; generate proactive alerts for high-risk guards on upcoming high-value sites |
| **Leave Accrual** | 1st of month | For each active guard: sum worked hours in previous month → compute accrual per leave type rules → write balance increment |
| **Payroll Period Auto-Open** | 1st of month | Create a new `security.payroll.period` in Draft state with the correct date range and Namibia rule set → notify HR/Payroll Officer |
| **Recurring Invoice Generation** | Configurable per billing plan | For all `security.billing.plan` records with `auto_invoice = True` and active: generate a draft invoice for the completed period → notify accountant |
| **Monthly Client Service Reports** | On payroll period close | Generate `security.client.service.report` PDF for each active client → email to client billing contact and account manager |
| **Management Pack Generation** | On payroll period close | Generate monthly management analytics pack PDF → email to Operations Manager and Owner |
| **Equipment Return Reminder** | Weekly | Find equipment allocations past their expected return date with no return recorded → notify supervisor |

### 4.2 Workflow Automations (Event-Driven)

These fire when a record transitions to a specific state.

| Trigger | Automated Actions |
|---------|------------------|
| Roster batch → `approved` | Auto-generate `security.attendance.record` shells for all slots in the batch. Sets each to `scheduled` status. Supervisor only needs to update them on the day. |
| Attendance batch → `locked` | Auto-flag records with anomalies (`payable_hours = 0` and not `absent`, missing check-out older than 1 day, late > 60 min). Payroll officer sees anomaly list, not raw records. |
| Payroll period → `processed` | Auto-set all payslips without anomaly flags to `confirmed`. HR only reviews the flagged ones. |
| Payroll period → `closed` | Auto-trigger invoice generation for billing plans with `auto_invoice = True`. |
| Loan balance reaches zero | Auto-close loan (`state = closed`), notify employee's supervisor and HR. |
| Certification expiry date reached | Auto-set `security.employee.certification.expired = True`. Roster validation now blocks new assignments for that post type. |
| Incident → `approved` | Auto-update guard reliability score. Auto-create payroll deduction flag for next period. Auto-notify supervisor via `security_notifications`. |
| Guard → `disqualified` | Auto-cancel all future `security.roster.slot` records for this guard (with reason "Guard disqualified"). Notify Operations Manager. |
| Equipment allocation → `issued` (no acknowledgment after 48h) | Auto-send reminder to supervisor to get guard acknowledgment. |

### 4.3 Smart Defaults (Reduce Clicks Without Automation)

- **Attendance batch creation**: defaults date = today, site = user's assigned site (from their employee record)
- **New payroll period**: defaults date_from = first day of next month, date_to = last day of next month, rule_set = company's active Namibia rule set
- **Roster slot grade**: auto-populated from the post type's `minimum_grade` when a post is selected
- **Billing invoice due date**: auto-set from `invoice_date + billing_plan.payment_term_days` on invoice creation
- **New guard profile**: defaults reliability score to 100, security_guard = True, grade = company default entry grade

---

## 5. Custom Views Architecture — OWL Tier System

### 5.1 The Three Tiers

```
TIER 1 — Standard XML + Lightweight OWL Widgets
────────────────────────────────────────────────
Used for: Master data and configuration CRUD screens
Examples: Guard profiles, grades, certifications, leave types,
          equipment categories, incident types, billing plans
OWL additions: Status badges, reliability gauge field widget,
               certification badge list widget

TIER 2 — OWL-Augmented Form and List Views
────────────────────────────────────────────────
Used for: Transactional records that benefit from contextual panels
Examples: Payslip form, billing invoice form, incident form,
          equipment allocation form
OWL additions: Payslip preview panel, AI suggestion toast,
               inline earnings/deductions chart, anomaly banner

TIER 3 — Full Custom Client Action Canvases
────────────────────────────────────────────────
Used for: Complex operational workflows that need spatial UI
Examples: Roster Board, Attendance Posting Console,
          Payroll Command Center, Executive Dashboard,
          AI Settings Panel
OWL: Entire screen is a mounted OWL component (ir.actions.client)
     Standard Odoo form/list layouts are not used here at all
```

### 5.2 Directory Structure (Per Module)

```
custom_addons/security_operations/
└── static/src/
    ├── components/                       # Reusable UI atoms
    │   ├── guard_card/
    │   │   ├── guard_card.js             # OWL Component definition
    │   │   └── guard_card.xml            # QWeb template
    │   ├── reliability_gauge/
    │   │   ├── reliability_gauge.js      # Custom field widget
    │   │   └── reliability_gauge.xml
    │   └── conflict_warning_badge/
    │       ├── conflict_warning_badge.js
    │       └── conflict_warning_badge.xml
    ├── views/                            # Client Action root components
    │   └── roster_board/
    │       ├── roster_board.js           # Root OWL component
    │       └── roster_board.xml
    ├── actions/
    │   └── roster_board_action.xml       # ir.actions.client XML record
    └── index.js                          # Registry entry point
```

### 5.3 Asset Manifest Pattern

```python
# __manifest__.py
'assets': {
    'web.assets_backend': [
        'security_operations/static/src/index.js',
        'security_operations/static/src/components/**/*.js',
        'security_operations/static/src/components/**/*.xml',
        'security_operations/static/src/views/**/*.js',
        'security_operations/static/src/views/**/*.xml',
    ],
},
```

### 5.4 OWL Component Registry Pattern

```javascript
// static/src/index.js
import { registry } from "@web/core/registry";
import { RosterBoard } from "./views/roster_board/roster_board";
import { ReliabilityGauge } from "./components/reliability_gauge/reliability_gauge";
import { CertificationBadgeList } from "./components/certification_badge_list/certification_badge_list";

// Register Tier 3 full-screen actions
registry.category("actions").add("security_roster_board", RosterBoard);

// Register Tier 1/2 field widgets
registry.category("fields").add("reliability_gauge", ReliabilityGauge);
registry.category("fields").add("certification_badge_list", CertificationBadgeList);
```

### 5.5 Client Action Record Pattern

```xml
<!-- static/src/actions/roster_board_action.xml -->
<record id="action_roster_board" model="ir.actions.client">
    <field name="name">Roster Board</field>
    <field name="tag">security_roster_board</field>
    <field name="target">main</field>
</record>

<menuitem
    id="menu_roster_board"
    name="Roster Board"
    action="action_roster_board"
    parent="security_operations.menu_operations_root"
    sequence="5"
/>
```

### 5.6 OWL Component Base Pattern

```javascript
// Any Tier 3 component
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class RosterBoard extends Component {
    static template = "security_operations.RosterBoard";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            slots: [],
            guards: [],
            selectedMonth: new Date(),
            loading: true,
            aiSuggestions: null,
        });
        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        // Fetch via ORM service — no raw JSON-RPC
        this.state.slots = await this.orm.searchRead(
            "security.roster.slot",
            [["shift_date", ">=", this.monthStart], ["shift_date", "<=", this.monthEnd]],
            ["id", "employee_id", "post_id", "shift_date", "shift_template_id", "state"]
        );
        this.state.loading = false;
    }
}
```

---

## 6. Module-by-Module View Redesigns

### `security_base` — Guard Profile (Tier 1 + Custom Widgets)

**Problem:** Standard Odoo employee form with security fields appended at the bottom. Feels generic. Key information buried.

**Redesigned form layout:**

```
┌──────────────────────────────────────────────────────────────────────┐
│  [PHOTO]   A. Smith                          [Grade B]  [● Active]  │
│            Employee #DFS-0042                                        │
│            Site A — Post 1                   [★★★★☆ Reliability: 87]│
├──────────────────────────────────────────────────────────────────────┤
│  TABS: Profile | Certifications | Roster History | Payslips          │
│         Incidents | Documents | Equipment | Leave                    │
├──────────────────────────────────────────────────────────────────────┤
│  PROFILE TAB                                                         │
│  ┌──────────────────────┬───────────────────────────────────────┐   │
│  │ [ReliabilityGauge]   │ Grade: B           Hourly Rate: N$25  │   │
│  │   OWL circular gauge │ Home Location: [map link icon]        │   │
│  │   0–100, colour coded│ Medical Fitness: Grade 1  Exp: Mar 27 │   │
│  └──────────────────────┴───────────────────────────────────────┘   │
│  Languages: [EN Fluent] [AF Conversational]                         │
│  Attributes: [Height >1.8m] [First Aid]                             │
├──────────────────────────────────────────────────────────────────────┤
│  CERTIFICATIONS TAB                                                  │
│  [✓ Firearm Lic  Exp: 2027-03]  [✓ Grade B  Exp: 2026-11]         │
│  [⚠ First Aid  Exp: 2026-06 — expiring in 14 days]                 │
│  [✗ CCTV  Not held]                                                 │
├──────────────────────────────────────────────────────────────────────┤
│  PAYSLIPS TAB                                                        │
│  [PayslipHistoryMini widget — 12-month table + sparkline]           │
└──────────────────────────────────────────────────────────────────────┘
```

**New OWL field widgets:**
- `ReliabilityGauge` — circular progress gauge (0–100). Green ≥ 80, Amber 50–79, Red < 50. Click navigates to reliability adjustment history.
- `CertificationBadgeList` — horizontal chip list. Green = valid, Amber = expiring < 30 days, Red = expired, Grey = not held.
- `PayslipHistoryMini` — compact 12-row table with net pay + a tiny SVG sparkline of net pay trend.
- `ReliabilityScoreHistory` — 12-month line chart of reliability score changes with event annotations (incident, adjustment).

---

### `security_operations` — Roster Board (Tier 3 Full Client Action)

**Problem:** Roster is managed via a flat list of `security.roster.slot` records. No spatial awareness, error-prone, not beginner-friendly.

**Redesigned Roster Board:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│  [◀ Apr]  MAY 2026  [Jun ▶]   [Site: All Sites ▼]   [Suggest AI ✦]   │
│  Status: 186/210 slots filled  |  8 open  |  3 conflicts  [Approve All]│
├──────────────┬────────────────────────────────────────────────────────┤
│              │  Thu 1  │  Fri 2  │  Sat 3  │  Sun 4  │  Mon 5  │ ... │
│  SITE A      │         │         │         │         │         │     │
│  Post 1 Day  │[A.Smith]│[A.Smith]│[B.Jones]│  OPEN ⚠ │[A.Smith]│     │
│  Post 1 Ngt  │[T.Nkosi]│[T.Nkosi]│[T.Nkosi]│[T.Nkosi]│  OPEN  │     │
│  Post 2 Day  │[C.David]│[C.David]│  OPEN  │[C.David]│[C.David]│     │
├──────────────┼─────────────────────────────────────────────────────────┤
│  SITE B      │ ...                                                    │
└──────────────┴─────────────────────────────────────────────────────────┘
│  ╔═══════════════════════════════════════════════════════╗            │
│  ║  GUARD POOL SIDEBAR          [▼ Available] [▼ Grade]  ║            │
│  ║  A. Smith     ████████ 87   Grade B  ✓ Firearm  ✓   ║            │
│  ║  M. Nakale    ███████  83   Grade B  ✓ Firearm  ✓   ║            │
│  ║  B. Jones     ██████   71   Grade C                  ║            │
│  ║  C. David     ████     45   ⚠ 3 incidents            ║            │
│  ╚═══════════════════════════════════════════════════════╝            │
└─────────────────────────────────────────────────────────────────────────┘
```

**Sub-components:**

| Component | Purpose |
|-----------|---------|
| `RosterTimeline` | The main grid. Rows = sites/posts, columns = calendar days |
| `RosterSlotCell` | One cell. States: filled (green), open (amber), conflict (red border), leave-blocked (grey). Click opens mini-form. Drag-and-drop target. |
| `GuardPoolSidebar` | Filterable drawer. Drag source. Shows: name, reliability gauge bar, grade, cert status, risk flag. |
| `ConflictWarningBadge` | Inline overlay on a slot cell. Shows the specific broken rule (e.g., "< 12h rest"). |
| `AIRosterSuggestionPanel` | Modal after "Suggest AI" click. Shows 3 scored options side-by-side. Each shows: coverage %, avg reliability, cost estimate. |
| `RosterApprovalBar` | Sticky footer: X filled / Y open / Z conflicts. "Submit for Approval" button. |
| `RosterMiniForm` | Popover when clicking a slot cell. Change guard assignment inline without leaving the board. |

---

### `security_attendance` — Attendance Posting Console (Tier 3)

**Problem:** Supervisors mark attendance by opening each of 20+ records individually in a list view. Daily task takes 15–20 minutes. Should take 2 minutes.

**Redesigned Posting Console:**

```
┌───────────────────────────────────────────────────────────────────────┐
│  Posting Sheet: [Site Alpha ▼]  [01 May 2026 ▼]  [Generate from Roster]│
│  ● 18 marked  ⚠ 1 AWOL  ○ 3 unmarked  ↑ 2 overtime pending          │
├────────────────┬───────────┬──────────┬────────┬───────┬─────────────┤
│  Guard         │ Post      │ Status   │ In     │ Out   │ Action      │
├────────────────┼───────────┼──────────┼────────┼───────┼─────────────┤
│  A. Smith      │ Post 1 Day│ ✓ Present│ 05:58  │ 18:02 │             │
│  B. Jones      │ Post 1 Ngt│ ⚠ Late   │ 18:47  │ —     │ [OT ✓]     │
│  C. David      │ Post 2 Day│ ✗ AWOL   │ —      │ —     │ [Dispute]  │
│  D. Williams   │ Post 2 Ngt│ ? Mark   │ —      │ —     │[✓][✗][⚠]  │
├────────────────┴───────────┴──────────┴────────┴───────┴─────────────┤
│  ╔══════════════════════════════════════════════════════╗             │
│  ║  AI ANOMALY PANEL (if AI enabled)                    ║             │
│  ║  ⚠ B. Jones late 47min. Traffic incident on B1       ║             │
│  ║    confirmed by fleet log. Suggest: approve           ║             │
│  ║    normal shift pay.                [✓ Approve][✗]   ║             │
│  ╚══════════════════════════════════════════════════════╝             │
│  [Lock Batch]   [Export PDF]   [Submit for Payroll]                  │
└───────────────────────────────────────────────────────────────────────┘
```

**Sub-components:**

| Component | Purpose |
|-----------|---------|
| `AttendancePostingGrid` | The main table. Each row is one guard/shift. Status column uses a button group (Present / Absent / AWOL). Time fields inline editable. Keyboard-navigable for fast entry. |
| `PostingSheetStatusBar` | Sticky top bar. Live counts of marked / unmarked / AWOL / overtime pending. |
| `AIAnomalyAlert` | Bottom panel. Shows AI-suggested auto-approvals for anomalous records. Thumbs up = applies override reason. Thumbs down = logs rejection. |
| `OvertimeApprovalQueue` | Side drawer listing pending overtime approvals across all sites for the manager. Approve/reject inline. |
| `AttendanceSmartCard` | Expanded card view for one record (click row to expand). Shows all computed fields: payable hours, shift bucket breakdown, late minutes, premium category. |

---

### `security_payroll_core` — Payroll Command Center (Tier 3)

**Problem:** Payroll period management and payslip review are separate list views with no guided workflow and no anomaly surfacing.

**Redesigned Payroll Command Center:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│  PAYROLL — May 2026                                                    │
│  [① Draft] ──▶ [② Generated] ──▶ [③ Reviewed] ──▶ [④ Confirmed] ──▶ [⑤ Closed]│
│  Current: ③ Reviewed                          [Next: Confirm All ▶]   │
├───────────────────────────┬─────────────────────────────────────────────┤
│  PERIOD SUMMARY           │  FLAGS REQUIRING REVIEW                    │
│  Headcount:        47     │  ⚠ 3 payslips: net pay >20% change        │
│  Total Gross: N$234,500   │  ⚠ 2 guards: no attendance records         │
│  Total Deductions: N$18,200│ ⚠ 1 guard: SSC number missing             │
│  Total Net:   N$216,300   │  ✓ 41 payslips: ready, no flags            │
│  vs. Apr: ▲ +2.1%         │  [Review Flags →]                          │
├───────────────────────────┴─────────────────────────────────────────────┤
│  [Search guard...] [Site ▼] [Show: All ▼]                              │
│  Guard          Site    Normal  OT  Sun  Gross      Net       State     │
│  A. Smith       Site A  96h     4h  8h   N$4,800   N$4,320   ✓ Ready  │
│  B. Jones       Site B  88h     0h  0h   N$4,400   N$3,960   ⚠ Flag   │
│  C. David       Site A  72h     0h  0h   N$3,600   N$3,010   ✓ Ready  │
├─────────────────────────────────────────────────────────────────────────┤
│  [Print All Payslips]  [Email Payslips]  [Export Excel]  [Confirm All] │
└─────────────────────────────────────────────────────────────────────────┘
```

**Sub-components:**

| Component | Purpose |
|-----------|---------|
| `PayrollStepperBar` | Visual wizard: 5 steps with current step highlighted. Click a completed step to review it. |
| `PayrollSummaryCard` | 4-up metric cards with vs-last-period comparison arrows and percentage. |
| `AnomalyFlagPanel` | Collapsible panel listing all payslips with flags. Each row shows the specific anomaly. Click navigates to that payslip. |
| `PayslipPreviewModal` | Full-screen modal showing exact PDF layout before print/confirm. Real-time computed data. Shows previous-period comparison column. |
| `PayrollBulkActionBar` | Sticky footer with primary actions: Print All / Email All / Export Excel / Confirm All. Confirms only non-flagged payslips unless overridden. |
| `EarningsDeductionsChart` | Mini doughnut chart on the period summary showing gross composition (normal / Sunday / holiday / night / overtime). |

---

### `security_reporting` — Executive Dashboard (Tier 3)

**Problem:** Managers must navigate to separate menu items to see each metric. No single overview.

**Redesigned Executive Dashboard:**

```
┌──────────────────────────────────────────────────────────────────────────┐
│  DOGFORCE OPERATIONS                    May 2026    [PDF] [Refresh]      │
├───────────┬───────────┬────────────────┬────────────────────────────────┤
│ Guards    │ Sites     │ Attendance     │ Payroll MTD                    │
│ 47 Active │ 12 Active │ 93.4% ▲+0.8%  │ N$234,500 ▲+2.1%              │
│ 3 On Leave│ 2 Alerts  │ 4 AWOL        │ 47 Guards Processed            │
├───────────┴───────────┴────────────────┴────────────────────────────────┤
│  ATTENDANCE BY SITE — Last 30 Days [Heatmap]                           │
│  ████████████████░░████████ Site Alpha     96.2% ✓                     │
│  ██████░░████░░████████████ Site Bravo     87.4% ⚠                     │
│  ████████████████████████░░ Site Charlie   98.1% ✓                     │
├────────────────────────────┬───────────────────────────────────────────┤
│  OUTSTANDING INVOICES      │  ALERT FEED                               │
│  INV/2026/047  N$28,400    │  ● 09:15  Guard C.David AWOL - Site B    │
│  12 days overdue ⚠         │  ● 08:30  Roster gap: Site A Post 2 Sun  │
│  INV/2026/044  N$15,200    │  ● 07:00  Doc expiry: B.Jones First Aid  │
│  3 days overdue            │  ● 2026-05-30  Billing variance: Site B  │
│  [View All Invoices →]     │  [View All Alerts →]                     │
├────────────────────────────┴───────────────────────────────────────────┤
│  [AI CO-PILOT]  Ask anything: "Who is available Saturday night?" [▶]  │
└──────────────────────────────────────────────────────────────────────────┘
```

**Sub-components:**

| Component | Purpose |
|-----------|---------|
| `MetricCard` | Statistic + vs-last-period trend arrow + 7-day sparkline. Clicking navigates to the source report. |
| `AttendanceHeatmap` | CSS grid. Sites on Y axis, days on X axis. Cell colour by attendance rate (green/amber/red). |
| `AlertFeed` | Reverse-chronological feed of all system alerts. Colour-coded by severity. Click to navigate to the source record. |
| `InvoiceAgeingWidget` | Mini table of top 5 outstanding invoices sorted by days overdue. |
| `CopilotWidget` | Text input + send button at the bottom. Sends to the AI co-pilot endpoint. Response appears as a formatted card below. |
| `MapWidget` | Optional OpenStreetMap canvas (no API key required) showing active site locations with attendance status pins. Enabled only if site geo-coordinates are configured. |

---

## 7. Payroll, Payslip & Attendance Deep Improvements

### 7.1 The Shift Split Utility — Critical Missing Logic

A shift from 18:00 Friday to 06:00 Saturday crosses midnight. If Friday is a normal day and Saturday is a public holiday, the first 6 hours are normal rate and the last 6 hours are public holiday rate. The current model assigns one `premium_category` to the whole shift, which is wrong.

**Location:** `security_l10n_na/utils/shift_split.py`

```python
from datetime import datetime, timedelta, date, time

NIGHT_START_HOUR = 18  # 18:00
NIGHT_END_HOUR = 6     # 06:00

def split_shift_by_boundaries(
    shift_start: datetime,
    shift_end: datetime,
    public_holidays: list[date],
) -> dict:
    """
    Returns hours in each pay category for a shift spanning any time range.
    Handles midnight crossings and shifts spanning multiple calendar days.

    Returns:
        {
            'normal_hours': float,
            'sunday_hours': float,
            'public_holiday_hours': float,
            'saturday_hours': float,
            'night_hours': float,  # Hours between 18:00 and 06:00
        }
    """
    buckets = dict(
        normal_hours=0.0, sunday_hours=0.0,
        public_holiday_hours=0.0, saturday_hours=0.0, night_hours=0.0
    )

    # Walk in 1-minute increments between shift_start and shift_end
    # For performance, identify boundary times and walk in segments instead
    current = shift_start
    segment_start = current

    def get_category(dt: datetime) -> str:
        d = dt.date()
        if d in public_holidays:
            return 'public_holiday'
        weekday = d.weekday()  # 0=Mon, 6=Sun
        if weekday == 6:
            return 'sunday'
        if weekday == 5:
            return 'saturday'
        return 'normal'

    def is_night(dt: datetime) -> bool:
        h = dt.hour
        return h >= NIGHT_START_HOUR or h < NIGHT_END_HOUR

    # Build boundary list: every midnight and every 18:00 and 06:00
    boundaries = []
    d = shift_start.date()
    while d <= shift_end.date():
        for boundary_hour in [0, 6, 18]:
            b = datetime.combine(d, time(boundary_hour, 0))
            if shift_start < b < shift_end:
                boundaries.append(b)
        d += timedelta(days=1)
    boundaries.sort()

    segments = [shift_start] + boundaries + [shift_end]
    for i in range(len(segments) - 1):
        seg_start = segments[i]
        seg_end = segments[i + 1]
        hours = (seg_end - seg_start).total_seconds() / 3600.0
        if hours <= 0:
            continue
        category = get_category(seg_start)
        buckets[category + '_hours'] += hours
        if is_night(seg_start):
            buckets['night_hours'] += hours

    return buckets
```

**Integration into `security.attendance.record`:**

Add 5 stored computed fields: `normal_hours`, `sunday_hours`, `public_holiday_hours`, `saturday_hours`, `night_hours`. Computed by `_compute_shift_buckets()` which calls `split_shift_by_boundaries()` when `check_in` and `check_out` are set.

**Integration into `security_payroll_core`:**

`action_compute_from_sources()` reads these 5 bucket fields instead of `premium_category`. Creates one earning line per bucket that has hours > 0. Applies the corresponding multiplier from the rule set.

---

### 7.2 The Improved Payroll Pipeline

```
security.roster.slot (planned shift)
        │
        ▼ action_generate_from_roster() OR mobile check-in OR manual
security.attendance.record
        │
        ├── _compute_scheduled_datetimes()   → scheduled_start, scheduled_end
        ├── _compute_calendar_flags()        → is_sunday, is_public_holiday, is_saturday, is_night_shift
        ├── _compute_attendance_metrics()    → worked_hours, late_minutes, valid_hours, overtime_hours
        └── _compute_shift_buckets()         → normal_hours, sunday_hours, ph_hours, saturday_hours, night_hours
                                               (calls split_shift_by_boundaries from security_l10n_na)
        │
        ▼ action_compute_from_sources()
security.payslip
        │
        ├── Pull attendance records in period, read 5-bucket fields
        ├── Create earning lines:
        │     NORMAL        = normal_hours × base_rate
        │     SUNDAY        = sunday_hours × base_rate × sunday_multiplier
        │     PUBLIC_HOLIDAY = ph_hours × base_rate × ph_multiplier
        │     SATURDAY      = saturday_hours × base_rate × saturday_multiplier
        │     NIGHT         = night_hours × base_rate × night_multiplier
        │     OVERTIME      = overtime_hours × base_rate × overtime_multiplier
        ├── Calculate SSC on (NORMAL + SUNDAY + PH + SATURDAY) ← not on OT
        ├── Calculate PAYE on (gross − SSC), annualised
        ├── Pull loan deductions (with cap logic)
        ├── Pull incident deductions (approved only, with amount override)
        ├── Pull equipment damage deductions (approved only)
        ├── Apply no-work-no-pay deduction (unpaid_hours × base_rate)
        ├── Check anomaly: net pay change > 20% vs. last period → set anomaly_flag
        └── Check anomaly: attendance hours = 0 → set anomaly_flag
        │
        ▼
security.payslip (confirmed) → PDF via QWeb → Email or Print
```

---

### 7.3 Payslip PDF Template Requirements

The QWeb template (`security_payroll_core/reports/security_payslip_report.xml`) must be redesigned to include:

```
┌─────────────────────────────────────────────────────────────────────┐
│  [COMPANY LOGO]          PAYSLIP — CONFIDENTIAL                    │
│  Company:  DogForce Security Services                              │
│  Guard:    A. Smith                 Employee #: DFS-0042           │
│  Period:   01 May – 31 May 2026     Pay Date:  16 June 2026        │
│  Grade:    B                         SSC #:    NA123456            │
│  Bank:     FNB Namibia               Account:  62001234567         │
├──────────────────────────────────────────┬──────────────────────────┤
│  EARNINGS               Hrs    Rate     Amount  │  PREV PERIOD     │
│  Normal Hours           96.0   N$25.00  N$2,400 │  N$2,200         │
│  Sunday Hours            8.0   N$37.50    N$300 │    N$150         │
│  Public Holiday Hours    4.0   N$37.50    N$150 │      N$0         │
│  Night Shift Hours      12.0   N$28.75    N$345 │    N$345         │
│  Approved Overtime       4.0   N$25.00    N$100 │      N$0         │
│                               GROSS:   N$3,295  │  N$2,695         │
├──────────────────────────────────────────┬──────────────────────────┤
│  DEDUCTIONS                         Amount      │                  │
│  No Work No Pay (4h × N$25)       (N$100.00)    │                  │
│  Social Security (SSC)             (N$29.66)    │                  │
│  Pay As You Earn (PAYE)           (N$245.00)    │                  │
│  Loan — Uniform Loan              (N$200.00)    │                  │
│  Incident — Damage to Radio        (N$50.00)    │                  │
│                        TOTAL DED: (N$624.66)    │                  │
├─────────────────────────────────────────────────┴──────────────────┤
│              NET PAY:  N$2,670.34                                  │
│  TWO THOUSAND SIX HUNDRED SEVENTY NAMIBIA DOLLARS AND 34 CENTS    │
├─────────────────────────────────────────────────────────────────────┤
│  Supervisor: _________________ Date: _________                     │
│  This payslip is confidential. For addressee only.                 │
└─────────────────────────────────────────────────────────────────────┘
```

**Specific improvements needed in the template:**
1. DogForce logo and address block
2. Employee bank details (for EFT verification before payment)
3. Previous period comparison column
4. Proper NAD number-to-words including cents
5. Supervisor signature line
6. Confidentiality footer
7. Page numbering for batch prints

---

## 8. AI Integration Layer — Multi-Provider Strategy

### 8.1 Architecture Principle

Business modules **never** import Anthropic, OpenAI, or Google GenerativeAI SDKs directly. All AI calls route through `security.ai.engine`. If the company disables AI or the API key is invalid, every `engine.complete()` call returns `None` and business logic handles `None` gracefully — the UI shows the manual workflow instead.

### 8.2 Provider Implementations

```python
# security_ai_engine/providers/base.py
class AIProviderBase:
    def complete(self, system_prompt: str, user_message: str,
                 max_tokens: int = 1000, temperature: float = 0.3) -> str: ...

# security_ai_engine/providers/claude.py
# Model default: claude-sonnet-4-6 (as of 2026-05-31)
class ClaudeProvider(AIProviderBase):
    def complete(self, system_prompt, user_message, max_tokens=1000, temperature=0.3):
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )
        return response.content[0].text

# security_ai_engine/providers/openai_provider.py
# Model default: gpt-4o
class OpenAIProvider(AIProviderBase):
    def complete(self, system_prompt, user_message, max_tokens=1000, temperature=0.3):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=max_tokens, temperature=temperature
        )
        return response.choices[0].message.content

# security_ai_engine/providers/gemini.py
# Model default: gemini-1.5-pro
class GeminiProvider(AIProviderBase):
    def complete(self, system_prompt, user_message, max_tokens=1000, temperature=0.3):
        response = self.model.generate_content(f"{system_prompt}\n\n{user_message}")
        return response.text
```

### 8.3 Engine Service Model

```python
# security_ai_engine/models/ai_engine.py
class SecurityAIEngine(models.AbstractModel):
    _name = "security.ai.engine"

    def complete(self, feature: str, system_prompt: str,
                 user_message: str, **kwargs) -> str | None:
        """
        Call this from any module. Returns None if:
        - AI is disabled company-wide
        - Feature flag is off
        - API key is invalid
        - Provider raises an exception
        Business logic must handle None.
        """
        if not self._is_feature_enabled(feature):
            return None
        provider = self._get_provider()
        if not provider:
            return None
        try:
            result = provider.complete(system_prompt, user_message, **kwargs)
            self._log_request(feature, user_message, result, success=True)
            return result
        except Exception as e:
            self._log_request(feature, user_message, str(e), success=False)
            return None
```

### 8.4 Admin Configuration UI (Tier 3 OWL)

```
┌──────────────────────────────────────────────────────────────────────┐
│  AI CONFIGURATION                                                    │
├──────────────────────────────────────────────────────────────────────┤
│  Provider:   ○ Claude (Anthropic)   ○ OpenAI   ○ Gemini             │
│  API Key:    [••••••••••••••••]                [Test Connection ▶]   │
│  Model:      [claude-sonnet-4-6 ▼]                                  │
├──────────────────────────────────────────────────────────────────────┤
│  FEATURE FLAGS                                                       │
│  ☑ Roster Optimizer            Monthly roster AI suggestions        │
│  ☑ Guard Risk Profiling        Daily risk score + proactive alerts  │
│  ☑ Attendance Anomaly          Auto-suggest anomaly resolutions     │
│  ☑ Billing Auditor             Under/overbilling detection          │
│  ☑ Operations Co-pilot         Natural language queries             │
│  ☐ Auto-apply AI suggestions   (off by default — require approval)  │
├──────────────────────────────────────────────────────────────────────┤
│  USAGE THIS MONTH                                                   │
│  Requests: 247   Est. Cost: $1.24   Avg Latency: 1.2s              │
│  [View Request Log →]                                               │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 9. AI Feature Specifications

### Feature 1 — Intelligent Roster Optimizer

**Trigger:** "Suggest AI" button on the Roster Board.

**Input payload:**
```json
{
  "site": "Site Alpha, Windhoek CBD",
  "period": "June 2026",
  "requirements": [
    {"post": "Post 1 Day", "grade_min": "C",
     "certifications": ["Firearm"], "shifts_in_period": 26}
  ],
  "eligible_guards": [
    {"id": 12, "name": "A. Smith", "grade": "B", "reliability": 87,
     "certs": ["Firearm"], "home_lat": -22.56, "home_lng": 17.07,
     "leave_days": [1, 2], "high_trust_excluded": false,
     "incidents_30d": 0, "consecutive_days_available": 6}
  ],
  "labor_rules": {
    "max_consecutive_days": 6, "min_rest_hours_between_shifts": 12,
    "max_hours_per_day": 12
  }
}
```

**System prompt:** `"You are an expert security operations scheduler. Generate 3 roster options: (1) Lowest Cost, (2) Highest Reliability, (3) Best Geographic Proximity. Return valid JSON only with schema: {option_name, score, rationale, assignments: [{slot_id, guard_id}]}."`

**Output:** `AIRosterSuggestionPanel` shows 3 options side by side. Each displays: option name, score, rationale, coverage percentage, estimated cost. Manager clicks "Apply" to write the slot assignments. Feedback buttons (thumbs up/down) stored in `security.ai.feedback`.

---

### Feature 2 — Guard Risk Profiling

**Trigger:** Nightly cron (03:00) + on-demand from guard profile.

**Input:** Last 90 days of attendance records + incident records for the guard.

**Computation (rule-based, no AI needed for the score):**
```python
late_rate = late_occurrences / total_scheduled_shifts
awol_rate = awol_occurrences / total_scheduled_shifts
incident_weight = sum(incident.reliability_score_delta for incident in recent_incidents)
risk_score = max(0, min(100,
    100
    - (late_rate * 40)
    - (awol_rate * 60)
    + incident_weight  # negative values reduce score
))
```

**AI escalation:** If `risk_score < 40` and guard is on the roster in the next 7 days at a site with `site.risk_classification = 'high'`, call the AI with guard history and site context to generate a natural-language proactive alert for the Operations Manager.

**Alert example:**
> "Guard C. David has a 31% late rate over the past 90 days and 2 approved incidents. He is assigned to Site Alpha (Premium Client) on Thursday night. Consider swapping with Guard M. Nakale (Risk Score: 83, available Thursday). [Swap Now →] [Dismiss]"

---

### Feature 3 — Attendance Anomaly Detection

**Trigger:** After an attendance batch is locked.

**Logic per anomalous record (late > 30 min or AWOL):**
1. Read the supervisor's `override_reason` or `note` field.
2. Check: is there a fleet shuttle breakdown on this route on this date? (Query `security.fleet.incident` or `security.vehicle.run`.)
3. If the reason mentions transport and a fleet incident is found → suggest "Auto-approve normal shift pay" with the rationale.
4. If no corroboration and the guard has a high late rate → flag for mandatory supervisor review.

**Output:** `AIAnomalyAlert` panel on the Posting Console. Each suggestion shows the guard name, the anomaly, the AI's rationale, and ✓/✗ buttons. Approved: sets `override_reason = "AI-assisted: [rationale]"`. Rejected: logs the rejection to `security.ai.feedback`.

---

### Feature 4 — Smart Billing Auditor

**Trigger:** "Audit Invoice" button on the billing invoice form.

**Logic:**
1. Fetch attendance records for the same `partner_id`, `site_id`, and service date range as the invoice.
2. Compare: `actual_guard_shifts` (from attendance, status = present/late/early_leave) vs. `invoiced_guard_shifts` (from invoice lines).
3. Compute variance per post per day.
4. If variance > 0 (overbilled) or < 0 (underbilled): call AI to generate a natural-language variance summary.

**Output alert example:**
> "Site Bravo — May 2026: Invoiced 4 guards per shift (N$12,800 total). Attendance records show 3 guards for 6 of 26 shifts. Potential overbilling: N$2,400. [Create Credit Line for N$2,400] [Mark as Reviewed] [Dismiss]"

---

### Feature 5 — Operations Co-pilot

**Where it lives:** Floating widget on the Executive Dashboard (web). Dedicated screen in mobile app (manager role). REST endpoint: `POST /security/mobile/copilot`.

**Architecture:**

```
Manager input: "Who is the most reliable guard available for a night shift
                in Windhoek this Saturday?"
                │
                ▼
AI System prompt: "You are an assistant for a Namibian security company.
Translate the user's question into a structured query specification.
Return JSON only:
{
  'model': 'hr.employee',
  'filters': [['security_guard', '=', true], ...],
  'sort_by': 'security_reliability_score desc',
  'limit': 5,
  'fields': ['name', 'security_grade_id', 'security_reliability_score']
}"
                │
                ▼
Odoo ORM executes the structured query (NOT raw SQL — no injection risk)
                │
                ▼
Result formatted as a clean widget:
"Top 3 available guards for Saturday night in Windhoek:
 1. A. Smith     Grade B   Reliability: 87   ✓ Available
 2. M. Nakale    Grade B   Reliability: 83   ✓ Available
 3. T. Amupala   Grade C   Reliability: 79   ✓ Available
 [Assign A. Smith to Saturday →]"
```

**Safety:** The AI returns a query specification. Odoo's ORM executes it with full access control. Users can only see records they have permission to see. No raw SQL, ever.

---

## 10. Intent-Based Interaction Model

### 10.1 The Philosophical Shift

| Old CRUD | New Intent-Based |
|----------|-----------------|
| Navigate → Roster Slots → New → Fill 20 fields × 200 slots | Click "Plan May Roster" → AI suggests → Manager approves in one click |
| Open each attendance record → mark present/absent (20+ records/day) | Open Posting Console → grid view → mark all guards in one screen in 2 min |
| Navigate → Payroll → Generate → Open each payslip → Compute → Review | Click "Run May Payroll" in wizard → System generates + flags 3 anomalies → HR reviews only the 3 |
| Navigate → Billing → Create Invoice → Add lines manually | Click "Bill May Services" → System generates from attendance → Accountant reviews + sends |
| Navigate to 6 different reports to get a management overview | Open Dashboard → everything visible immediately |
| Search through guard list to answer "who's available Saturday?" | Type into Co-pilot: "Who's available Saturday night Windhoek?" |

### 10.2 Smart Onboarding Wizard

For new deployments, a setup wizard guides the admin through:

1. Company profile: name, logo, address, currency (NAD pre-selected for Namibia)
2. AI provider configuration (optional — fully skippable)
3. Grades and certifications: system suggests standard security company setup; admin accepts or edits
4. First client and site
5. First guard profiles (CSV import option)
6. First roster: "Let me suggest a roster for this week" or "I'll do it manually"

This replaces the blank Odoo interface with a guided 20-minute setup.

### 10.3 Feedback Loops

Every AI suggestion has a binary feedback button (thumbs up / down) and an optional free-text reason on rejection. This data is stored in `security.ai.feedback` and used to:

1. Improve system prompt specificity over time
2. Identify AI features with low acceptance rates (may indicate poor prompt design or wrong feature)
3. Track per-user preferences (some managers prefer manual control even when AI is available)

The principle: **AI suggests, human decides, system learns.**

---

## 11. Implementation Sequence

### Sprint A — Foundation Gaps (Weeks 1–2)

These gaps block correct payroll and billing. Fix these first.

| Task | Module | Priority |
|------|--------|----------|
| Add `split_shift_by_boundaries()` utility | `security_l10n_na` | P0 |
| Add `is_night_shift`, `is_saturday` fields to attendance record | `security_attendance` | P0 |
| Add `_compute_shift_buckets()` using the split utility | `security_attendance` | P0 |
| Add night + Saturday earning lines in payroll compute | `security_payroll_core` | P0 |
| Add Saturday + night multiplier fields to rule set | `security_l10n_na` | P0 |
| Add certification expiry date per employee join model | `security_base` | P1 |
| Document expiry cron job | `security_documents` | P1 |
| Leave accrual cron job | `security_leave` | P1 |
| Confirmed 2025/2026 Namibia public holiday data | `security_l10n_na` | P1 |

---

### Sprint B — Critical UX (Weeks 3–5)

These are the highest-frequency daily-use screens. Build the backend models first, then the OWL views.

| Task | Module | Priority |
|------|--------|----------|
| Attendance Posting Console — backend bulk mark endpoint | `security_attendance` | P0 |
| Attendance Posting Console — Tier 3 OWL component | `security_attendance` | P0 |
| `AttendancePostingGrid` + `PostingSheetStatusBar` OWL | `security_attendance` | P0 |
| Guard Profile form redesign — tab layout | `security_base` | P1 |
| `ReliabilityGauge` field widget OWL | `security_base` | P1 |
| `CertificationBadgeList` field widget OWL | `security_base` | P1 |
| Payslip preview modal — `PayslipPreviewModal` OWL | `security_payroll_core` | P1 |
| Improved QWeb payslip PDF template (with all fields) | `security_payroll_core` | P1 |
| Anomaly flag logic in `action_compute_from_sources()` | `security_payroll_core` | P1 |

---

### Sprint C — Scheduling Intelligence (Weeks 6–8)

| Task | Module | Priority |
|------|--------|----------|
| `security_shift_planner` module scaffold | `security_shift_planner` | P1 |
| Constraint-satisfaction eligible guard filter | `security_shift_planner` | P1 |
| Scoring engine (reliability + distance + fairness) | `security_shift_planner` | P1 |
| Monthly roster generation wizard — backend | `security_shift_planner` | P1 |
| Site-guard exclusion model + roster validation hook | `security_operations` | P1 |
| `high_trust_exclusion` check in roster assignment validation | `security_operations` | P1 |
| Roster Board — Tier 3 OWL root component | `security_operations` | P1 |
| `RosterTimeline` + `RosterSlotCell` + `GuardPoolSidebar` OWL | `security_operations` | P1 |
| `ConflictWarningBadge` OWL widget | `security_operations` | P2 |
| Roster approval state machine | `security_operations` | P2 |

---

### Sprint D — AI Engine + Smart Features (Weeks 9–11)

| Task | Module | Priority |
|------|--------|----------|
| `security_ai_engine` scaffold — models, admin config | `security_ai_engine` | P1 |
| Provider abstraction — Claude, OpenAI, Gemini | `security_ai_engine` | P1 |
| AI admin configuration UI — Tier 3 OWL | `security_ai_engine` | P1 |
| Billing Auditor feature (AI Feature 4) | `security_ai_engine` + `security_billing` | P1 |
| Attendance Anomaly Detection (AI Feature 3) | `security_ai_engine` + `security_attendance` | P1 |
| `AIAnomalyAlert` OWL component | `security_attendance` | P2 |
| Guard Risk Profiling — rule-based score | `security_base` | P2 |
| Guard Risk Profiling — AI escalation alerts | `security_ai_engine` | P2 |
| Roster Optimizer AI hook | `security_shift_planner` + `security_ai_engine` | P2 |
| `AIRosterSuggestionPanel` OWL | `security_operations` | P2 |

---

### Sprint E — Reporting, Billing Automation, Portal (Weeks 12–14)

| Task | Module | Priority |
|------|--------|----------|
| Executive Dashboard — Tier 3 OWL | `security_reporting` | P1 |
| `MetricCard`, `AttendanceHeatmap`, `AlertFeed` OWL | `security_reporting` | P1 |
| Payroll Command Center — Tier 3 OWL | `security_payroll_core` | P1 |
| Management payroll summary PDF (QWeb) | `security_payroll_core` | P1 |
| Payroll batch email delivery | `security_payroll_core` | P2 |
| Recurring invoice cron + monthly invoice wizard | `security_billing` | P1 |
| Client service report PDF (QWeb) | `security_client_reports` | P2 |
| `security_portal` module | `security_portal` | P2 |
| Operations Co-pilot — web widget + mobile endpoint | `security_ai_engine` | P2 |
| `security_notifications` module | `security_notifications` | P2 |
| FCM push notifications wired | `security_mobile` | P2 |

---

### Sprint F — Migration, Hardening, Go-Live (Weeks 15–16)

| Task | Module | Priority |
|------|--------|----------|
| `security_dogforce_migration` scaffold + CSV templates | `security_dogforce_migration` | P0 |
| Employee import + validation | `security_dogforce_migration` | P0 |
| Client/site/leave balance/loan import | `security_dogforce_migration` | P0 |
| Attendance scenario automated tests | `security_attendance` | P1 |
| Full payroll pipeline integration test | `security_payroll_core` | P0 |
| NamRA PAYE submission report | `security_l10n_na` | P1 |
| SSC submission report | `security_l10n_na` | P1 |
| Load testing: posting sheet bulk operations | `security_attendance` | P1 |

---

## Appendix A — Module Dependency Graph (Updated)

```
Odoo [hr, mail, contacts, website]
    │
    ▼
security_base
    │
    ├──▶ security_operations
    │        │
    │        ├──▶ security_shift_planner  ←── security_ai_engine
    │        │
    │        └──▶ security_attendance
    │                 │
    │                 └──▶ security_leave
    │                           │
    │                           └──▶ security_l10n_na
    │                                     │
    │                                     └──▶ security_payroll_core
    │                                               │
    │                                    ┌──────────┤
    │                                    ▼          ▼
    │                               security_loans  security_discipline
    │                                    │          │
    │                                    └────┬─────┘
    │                                         ▼
    │                                   security_billing
    │                                         │
    │                           ┌─────────────┤
    │                           ▼             ▼
    │              security_accounting_controls  security_client_reports
    │                           │
    │                           └──▶ security_reporting
    │                                security_analytics
    │
    ├──▶ security_documents
    ├──▶ security_equipment
    ├──▶ security_fleet
    ├──▶ security_portal       ←── security_billing, security_client_reports
    ├──▶ security_notifications ←── all modules
    └──▶ security_mobile        ←── security_base, security_attendance, security_ai_engine
```

---

## Appendix B — Custom OWL Components Inventory

| Component | Type | Module | Tier |
|-----------|------|--------|------|
| `ReliabilityGauge` | Field widget | `security_base` | 1 |
| `CertificationBadgeList` | Field widget | `security_base` | 1 |
| `PayslipHistoryMini` | Field widget | `security_base` | 1 |
| `ReliabilityScoreHistory` | Field widget | `security_base` | 1 |
| `RosterBoard` | Client action root | `security_operations` | 3 |
| `RosterTimeline` | Component | `security_operations` | 3 |
| `RosterSlotCell` | Component | `security_operations` | 3 |
| `GuardPoolSidebar` | Component | `security_operations` | 3 |
| `ConflictWarningBadge` | Component | `security_operations` | 3 |
| `AIRosterSuggestionPanel` | Component | `security_operations` | 3 |
| `RosterApprovalBar` | Component | `security_operations` | 3 |
| `RosterMiniForm` | Component | `security_operations` | 3 |
| `AttendancePostingConsole` | Client action root | `security_attendance` | 3 |
| `AttendancePostingGrid` | Component | `security_attendance` | 3 |
| `PostingSheetStatusBar` | Component | `security_attendance` | 3 |
| `AIAnomalyAlert` | Component | `security_attendance` | 3 |
| `OvertimeApprovalQueue` | Component | `security_attendance` | 3 |
| `AttendanceSmartCard` | Component | `security_attendance` | 3 |
| `PayrollCommandCenter` | Client action root | `security_payroll_core` | 3 |
| `PayrollStepperBar` | Component | `security_payroll_core` | 3 |
| `PayrollSummaryCard` | Component | `security_payroll_core` | 3 |
| `AnomalyFlagPanel` | Component | `security_payroll_core` | 3 |
| `PayslipPreviewModal` | Component | `security_payroll_core` | 3 |
| `PayrollBulkActionBar` | Component | `security_payroll_core` | 3 |
| `EarningsDeductionsChart` | Component | `security_payroll_core` | 3 |
| `ExecutiveDashboard` | Client action root | `security_reporting` | 3 |
| `MetricCard` | Component | `security_reporting` | 3 |
| `AttendanceHeatmap` | Component | `security_reporting` | 3 |
| `AlertFeed` | Component | `security_reporting` | 3 |
| `InvoiceAgeingWidget` | Component | `security_reporting` | 3 |
| `MapWidget` | Component | `security_reporting` | 3 |
| `CopilotWidget` | Component | `security_reporting` | 3 |
| `AIAdminConfig` | Client action root | `security_ai_engine` | 3 |
| `AIFeedbackButtons` | Component | `security_ai_engine` | 1/2 |

---

*This document is the single source of truth for platform architecture and build decisions. Update it when major decisions change. Do not let implementation drift from this plan without updating the plan.*
