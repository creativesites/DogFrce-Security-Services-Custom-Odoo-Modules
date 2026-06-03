# DogForce Security Suite — Completion Plan
## Road to 100% Production Go-Live

**Current status:** ~58% complete  
**Target:** Production-ready for DogForce Security Services (Namibia)  
**Last updated:** 2026-06-02

This plan picks up from Sprint F. Each sprint is a coherent unit of work that can be done independently and deployed as a batch. Tasks are marked P0 (production blocker), P1 (critical for daily operations), P2 (important but workaroundable), P3 (nice-to-have).

---

## Sprint G — Core operational gaps (Weeks 1–3)
*These are the gaps where an HR officer or payroll manager would hit a wall in daily use.*

---

### `security_payroll_core`

**G-1 · Deduction cap logic** `P0`  
If the sum of loan + incident + equipment damage deductions would reduce net pay below zero (or below a configurable floor, e.g. 30% of gross), cap the deduction for this period and carry the excess forward to the next period.

Implementation:
- Add `deduction_floor_pct` Float field (default 0.30) on `SecurityPayrollRuleSet`
- In `action_compute_from_sources()`, after all deduction lines are written, check `total_deductions > total_earnings * (1 - floor_pct)`. If exceeded, reduce the last-priority deductions proportionally and write `carry_forward_amount` to each affected loan/incident record.
- Add `carry_forward_amount` Float field to `SecurityLoanDeduction` and `SecurityIncident`
- Deduction lines include a `capped` Boolean for audit visibility

**G-2 · Payroll period wizard** `P1`  
A guided wizard: pick date range → auto-select rule set → preview eligible guards → one-click generate payslips.

Implementation:
- New transient model `security.payroll.period.wizard` with fields: `date_from`, `date_to`, `rule_set_id`, `eligible_employee_ids` (Many2many computed)
- `_compute_eligible_employees()`: active guards not already in an overlapping period
- `action_generate()`: creates `SecurityPayrollPeriod` and calls `action_generate_payslips()`
- Wizard view with 2-step notebook: Step 1 (dates + rule set), Step 2 (preview employee list + confirm)
- Add wizard launcher button to the payroll period list view

**G-3 · Payslip email delivery** `P2`  
- Add `action_email_payslips()` method on `SecurityPayrollPeriod`
- For each confirmed/paid payslip: render PDF → attach to email → send to `employee.work_email` (or supervisor email if guard has no work email)
- Add "Email All Payslips" button to period form header (visible when state = 'paid')
- Uses Odoo's `mail.template` system; create a template record in data XML

**G-4 · Payroll Excel export** `P2`  
- Add `action_export_payroll_register()` on `SecurityPayrollPeriod`
- Returns an XLS file (use `xlwt` or Python `csv` module — csv is simpler and available in standard Docker image)
- Columns: Employee, SSC No., Tax No., Normal Hrs, Sat Hrs, Sun Hrs, PH Hrs, Night Hrs, OT Hrs, Gross, SSC, PAYE, Loans, Incidents, Equipment, Net Pay
- Button on period form next to Management Report

---

### `security_leave`

**G-5 · Verify and harden leave accrual cron** `P1`  
The `action_cron_accrue_leave()` method exists but has not been tested end-to-end with real data. Steps:
- Write a unit test (`tests/test_leave_accrual.py`) that creates a guard, creates attendance records for one month, calls the cron, and asserts the balance increased by the correct amount
- Add a "Run Accrual Now" button to the leave type form (calls cron for that type only) for manual testing

**G-6 · Leave carryover rules** `P1`  
At year-end, each leave type should apply one of: carry over up to N days, forfeit all unused, or pay out at hourly rate.

Implementation:
- Add `carryover_policy` Selection field on `SecurityLeaveType`: `('carry', 'Carry Over'), ('forfeit', 'Forfeit'), ('payout', 'Pay Out')`
- Add `max_carryover_days` Integer field (used when policy = 'carry')
- Add `action_cron_year_end_carryover()` scheduled action (runs 1 January each year)
- For payout: creates a payslip earning line on the guard's next payslip

**G-7 · Public holiday detection in leave** `P1`  
If an approved leave period spans a public holiday, that day must not consume a leave day.

Implementation:
- In `_compute_requested_days()` on `SecurityLeaveRequest`, query `security.public.holiday` for dates that fall within `[date_from, date_to]` and subtract that count from `requested_days`
- Add a note on the leave request: "2 public holidays excluded from this leave period"

**G-8 · Leave calendar view** `P2`  
- Add a calendar view (`view_type="calendar"`) on `SecurityLeaveRequest`
- `date_start = date_from`, `date_stop = date_to`, `color = leave_type_id`
- Add to the leave menu as "Leave Calendar" item
- Shows all approved leaves across all guards, colour-coded by type

---

### `security_loans`

**G-9 · Loan application workflow** `P1`  
Currently loans are created directly in an active state. Need: guard/HR submits request → manager approves → HR activates → payroll deducts.

Implementation:
- Add `state` Selection to `SecurityEmployeeLoan`: `draft → submitted → approved → active → closed → written_off`
- Add `action_submit()`, `action_approve()`, `action_activate()`, `action_close()`, `action_write_off()` methods
- `action_activate()` sets `start_date` and generates `SecurityLoanDeduction` schedule lines
- Add state statusbar and buttons to loan form view
- Only `state = 'active'` loans generate deductions in payroll

**G-10 · Loan deduction cap** `P0`  
Links to G-1 above — loan deductions must be capped before net pay goes negative. Also add a `max_loan_amount` per grade field on `SecurityGrade` for enforcement at application.

**G-11 · Loan statement PDF** `P2`  
- QWeb report on `security.employee.loan` showing: loan amount, disbursement date, all paid installments, remaining balance, projected payoff date
- Button on loan form: "Print Statement"

**G-12 · Multiple loan priority** `P2`  
- Add `deduction_priority` Integer field (1 = first deducted) on `SecurityEmployeeLoan`
- Payroll deduction logic orders active loans by priority before applying the cap

---

### `security_discipline`

**G-13 · Evidence attachments** `P1`  
- Enable `ir.attachment` on `SecurityIncident` by adding `_inherit = ['mail.thread', 'mail.activity.mixin']` to the model (this gives the chatter + attachments)
- Add chatter to the incident form view with `<chatter/>` tag

**G-14 · Employee notification and acknowledgment** `P1`  
- After incident approval, create an Odoo internal note (or email) to the guard's supervisor
- Add `acknowledged` Boolean and `acknowledged_date` Datetime fields on `SecurityIncident`
- Add "Mark Acknowledged" button (visible after approval)

**G-15 · Appeal workflow** `P2`  
- Add `appeal_state` Selection: `('none','No Appeal'), ('appealed','Appealed'), ('upheld','Upheld'), ('overturned','Overturned')`
- Add `appeal_reason` Text field and `appeal_reviewed_by` Many2one to `res.users`
- If appeal overturned: `action_overturn_appeal()` reverses the reliability score delta and voids the payroll deduction line
- Add Appeal section to incident form (visible after approval)

**G-16 · Progressive discipline tracking** `P2`  
- Add `severity` Selection on `SecurityIncidentType`: low, medium, high, critical
- On guard employee record, add computed `_compute_progressive_discipline_flag()`: searches incidents in last 90 days, if count of severity ≥ medium ≥ 3 → sets `security_suspension_recommended = True`
- Show a banner/warning on the employee form when flag is True

---

### `security_documents`

**G-17 · Post type → document requirement mapping** `P1`  
Guards must have all required documents for a post type before assignment.

Implementation:
- Add `required_document_type_ids` Many2many `security.document.type` field on `SecurityPostType`
- In `security_shift_planner`'s `_get_eligible_guards()`, add a check: for each required document type, guard must have a non-expired verified document of that type
- If missing, guard is excluded with reason "Missing required document: Firearm Certificate"

**G-18 · Firearm certificate as first-class type** `P1`  
- Add fields to `SecurityEmployeeDocument` when `document_type_id.is_firearm_cert = True`: `weapon_type`, `calibre`, `licence_number`, `issuing_authority`, `next_inspection_date`
- Add `is_firearm_cert` Boolean to `SecurityDocumentType`
- These extra fields show/hide in the document form using `invisible` domain

**G-19 · Compliance dashboard** `P1`  
- New list/pivot view: all guards with documents expiring in the next 30/60/90 days
- Grouped by site (using the guard's current roster assignment) and document type
- Add as a menu item under the Documents menu: "Compliance Report"
- Simple computed model or query on existing `SecurityEmployeeDocument` with date filter

---

## Sprint H — Operations & billing completion (Weeks 4–6)

---

### `security_operations`

**H-1 · Monthly roster generation wizard** `P0`  
The single most-used operational feature. Currently rosters are created manually slot by slot.

Implementation:
- New transient model `security.roster.generate.wizard` with: `date_from`, `date_to`, `site_ids` Many2many, `use_scoring_engine` Boolean
- `action_preview()`: runs the scoring engine for each site × shift × date, returns a preview list (which guard would be assigned to each slot)
- `action_confirm()`: creates `SecurityRosterBatch` and `SecurityRosterSlot` records, assigns guards from the preview
- Wizard view: Step 1 (month + sites), Step 2 (preview table with override capability), Step 3 (confirm)
- Entry point: "Generate Roster" button on the Roster Batch list view

**H-2 · Bulk roster copy** `P1`  
- Add `action_copy_from_previous_month()` on `SecurityRosterBatch`
- Finds the most recent batch for the same set of sites, copies all confirmed slots to a new draft batch with dates shifted by one month
- Button: "Copy from Previous Month" on batch form header
- Useful for recurring same-guard-same-post deployments

**H-3 · Roster approval state machine** `P1`  
Currently batches go draft → confirmed with no intermediate review.

Add state: `draft → submitted → approved → closed`
- `action_submit()`: Operations Supervisor submits the roster for Manager review
- `action_approve()`: Operations Manager approves; roster becomes source of truth for attendance generation
- `action_reject()`: sends back to draft with reason
- Add `submitted_by`, `approved_by`, `rejection_reason` fields
- Add to `security_notifications`: when submitted, notify manager; when approved, notify supervisor

**H-4 · Fairness score warnings** `P2`  
- In the scoring engine `_score_guard()`, compute each guard's Sunday + holiday + night shift count in the last 90 days relative to peers of the same grade at the same sites
- Add a `fairness_warning` Boolean on `SecurityRosterSlot`: True if assigned guard has >50% more premium shifts than their grade average
- Show a yellow warning badge on the Roster Board OWL for flagged slots

---

### `security_billing`

**H-5 · Invoice email delivery** `P1`  
- Create a `mail.template` record for `security.billing.invoice` in `data/security_billing_email_template.xml`
- Subject: "Invoice [invoice.name] — [partner.name]"
- Body: professional covering letter with invoice summary + PDF attachment
- Add `action_send_email()` method that renders the template and sends via Odoo mail
- "Send Invoice" button on invoice form (visible when state = 'draft' or 'sent')

**H-6 · Credit notes** `P1`  
- New model `security.billing.credit.note` with fields: `invoice_id` Many2one, `partner_id`, `reason` Text, `amount` Float, `state` (draft/confirmed/applied), `date`
- `action_apply()`: reduces the invoice's outstanding balance or generates a negative adjustment
- Form view + list view + Print button (QWeb report)
- Add "Issue Credit Note" button to invoice form (visible when state = 'sent' or 'paid')

**H-7 · Monthly invoice wizard** `P1`  
- New transient model `security.invoice.generate.wizard`: `billing_plan_id`, `period_month` Date, `generation_source` Selection (roster/attendance), preview `line_ids`
- `action_preview()`: runs the same logic as `action_generate_from_roster/attendance` but returns preview data without committing
- `action_confirm()`: creates the invoice
- "Generate Invoice" button on billing plan form

**H-8 · Invoice aging report** `P2`  
- New QWeb PDF report on `res.partner` (or `security.billing.invoice`) showing outstanding invoices bucketed by: Current, 1–30 days, 31–60 days, 61–90 days, 90+ days
- Totals per bucket, per client, and grand total
- "Print Aging Report" action in Billing menu

---

### `security_equipment`

**H-9 · Equipment issuance workflow** `P1`  
Currently allocations are created directly as "issued". Need a formal handover.

- Add `state` Selection to `SecurityEquipmentAllocation`: `draft → issued → acknowledged → returned → damaged`
- Add `acknowledged_date` Datetime and `returned_date` Datetime fields
- `action_issue()`: marks as issued; triggers notification to supervisor
- `action_acknowledge()`: guard/supervisor confirms receipt; adds acknowledgment note
- `action_return()`: starts return process; prompts for condition (good/damaged/lost)
- If returned damaged or lost: auto-creates a damage claim if one doesn't exist

**H-10 · Return and damage workflow** `P1`  
- Add `SecurityEquipmentReturn` model (or extend allocation with return fields): `return_date`, `condition` Selection (good/damaged/lost), `damage_description`, `damage_claim_id` Many2one
- `action_close_return()`: if condition is good, closes the allocation; if damaged/lost, auto-creates or links a damage claim
- Add return tab to allocation form view

**H-11 · Equipment inventory count** `P2`  
- Computed view: count of allocated (active) items per equipment type per site
- Simple list view with `group_by` on `equipment_type_id` and `site_id`
- "Inventory" menu item under Equipment

---

### `security_base`

**H-12 · Certification expiry join model** `P1`  
Currently certifications are a flat Many2many tag. Need per-guard expiry dates.

- New model `security.employee.certification` (join model): `employee_id`, `certification_id`, `issue_date`, `expiry_date`, `document_id` Many2one to `SecurityEmployeeDocument`, `verified` Boolean
- Replace `security_certification_ids` Many2many with One2many to the join model on `hr.employee`
- Update the scoring engine in `security_shift_planner` to check `expiry_date >= today` when testing eligibility
- **Migration note**: existing Many2many data must be migrated to the join model in `security_dogforce_migration`

**H-13 · Emergency contact fields** `P1`  
- Add to `hr.employee` (via `security_base` extension): `emergency_contact_name` Char, `emergency_contact_relationship` Char, `emergency_contact_phone` Char
- Add to Guard Profile form view under Details tab

**H-14 · Payslip history tab on employee form** `P2`  
- Add a Smart Button or tab on the employee form showing last 12 payslips: period name, gross, net, state
- Computed One2many via `security.payslip` domain `[('employee_id','=',id)]` ordered by period date desc, limit 12

---

## Sprint I — Reporting, notifications, portal (Weeks 7–9)

---

### `security_reporting`

**I-1 · Payroll expenditure dashboard** `P1`  
Extend the Executive Dashboard or add a new Tier-3 OWL action:
- Gross pay by site (bar chart using `Chart.js` or just a table)
- Month-on-month net pay comparison (this month vs last month per site)
- Hours breakdown pie (normal vs. overtime vs. weekend premium)
- Load data from `security.payslip` grouped by `period_id` and `employee_id.security_site_id`

**I-2 · AWOL/absence heatmap** `P2`  
- New Tier-3 OWL component: Y axis = guards sorted by site, X axis = dates (last 30 days), cell colour = attendance status (green/amber/red/grey)
- Data loaded via `orm.searchRead("security.attendance.record", ...)` for the date range
- Clickable cells open the attendance record form

**I-3 · Guard reliability leaderboard** `P2`  
- Simple list view (or inline table in Executive Dashboard): top 20 and bottom 20 guards by `security_reliability_score`
- Show 90-day trend: compare current score to score 90 days ago (store `score_snapshot_90d` as a computed field updated by cron)
- Arrow indicators: ↑ improving, ↓ declining, → stable

**I-4 · Headcount trend graph** `P2`  
- Pivot/graph view on `hr.employee` showing active guard count by month
- Uses `create_date` grouped by month for hires, and a `termination_date` field (to be added to `security_base`) for departures
- Included in the Executive Dashboard Reporting tab

---

### `security_notifications`

**I-5 · Wire notifications to all event sources** `P1`  
Currently only document expiry and overdue invoices generate notifications. Add:
- Roster gap: when a batch has unassigned slots past its `date_from`, trigger a "Roster Gap" notification (called from `security_operations` cron)
- Leave approval: when a leave request is approved, notify the operations supervisor responsible for that guard's site
- Incident approval: when an incident is approved, notify the guard's direct supervisor
- Document rejection: when a document is rejected, notify the HR officer

For each: call `self.env["security.notification"].create({...})` from the relevant model action method.

**I-6 · Email delivery for critical notifications** `P1`  
- Add `send_email` Boolean (default True for `severity = 'critical'`) on `SecurityNotification`
- On `create()`, if `send_email = True`, send via `self.env['mail.mail'].create({...}).send()`
- Use the recipient's work email; fall back to admin email if none

**I-7 · Notification bell widget in Odoo top bar** `P2`  
- Create a systray OWL widget that shows unread notification count
- `registry.category("systray").add("security.notifications", NotificationBell, {sequence: 5})`
- Clicking opens a dropdown list of the 10 most recent unread notifications
- "Mark All Read" button

---

### `security_accounting_controls`

**I-8 · Client payment recording UI** `P1`  
Currently the model exists but there's no easy UI to record a payment against an invoice.

- Add "Record Payment" button to billing invoice form (visible when state = 'sent')
- Opens a wizard: `amount`, `payment_date`, `payment_reference`, `payment_method` (EFT/cash/cheque)
- Creates a `SecurityClientPayment` record linked to the invoice
- If `payment.amount >= invoice.total_amount`: sets invoice to 'paid'
- If partial: creates a "partial payment" note and leaves invoice as 'sent'

**I-9 · Outstanding balance on client/partner form** `P2`  
- Add a smart button or stat field on `res.partner` (for clients): "Outstanding: N$ X" showing total unpaid invoice amount
- Computed via `sum` of unpaid invoice `total_amount` for that partner

---

### `security_client_reports`

**I-10 · Client service report improvements** `P1`  
The current PDF exists but is minimal. Expand to:
- DogForce branding header (logo, company address, registration number)
- Guard names listed (with toggle: `include_guard_names` Boolean on the report record)
- Planned vs. actual comparison table (scheduled shifts vs. attended shifts per post)
- Incident count for the period (if any incidents at that site)
- Client signature block at the bottom

**I-11 · Excel attendance export** `P2`  
- Add `action_export_to_excel()` on `SecurityClientServiceReport`
- Returns a CSV file: Date, Guard Name, Post, Shift, Check-in, Check-out, Hours, Status
- Button "Export to Excel" on report form

---

## Sprint J — Mobile app completion (Weeks 10–12)
*The field supervisor workflow is the highest-frequency daily use case. It must work reliably on mobile.*

---

### `security_mobile` (backend) + `mobile/` (frontend)

**J-1 · Verify all API endpoints against live data** `P0`  
- Test every endpoint in `security_mobile/controllers/main.py` against the current database
- Fix any field name mismatches (the `employee_id` vs `partner_id` issue noted in `KNOWN_ISSUES.md`)
- Write `HttpCase` tests for each endpoint: supervisor posting sheet, mark presence, batch submit, manager dashboard, overtime approve/reject, owner KPIs

**J-2 · Supervisor posting sheet — full flow** `P0`  
In `mobile/app/(supervisor)/`:
- `index.tsx`: loads today's batch for the supervisor's assigned site(s) — currently scaffolded, needs the real `useBatch()` hook implementation
- `mark/[recordId].tsx`: mark presence screen — needs the PUT call to the API and optimistic UI update
- `history.tsx`: past batches list — needs pagination

**J-3 · Manager multi-site dashboard** `P1`  
In `mobile/app/(manager)/`:
- `index.tsx`: all-sites attendance summary — needs real `useManagerDashboard()` hook
- `site/[siteId].tsx`: per-site attendance detail with overtime approval
- `overtime.tsx`: list of pending overtime records with approve/reject buttons

**J-4 · Owner KPI dashboard** `P1`  
In `mobile/app/(owner)/index.tsx`:
- Attendance rate (today), payroll YTD total, outstanding invoices — needs real API calls
- Currently placeholder — implement `useOwnerKPIs()` hook

**J-5 · Offline resilience (basic)** `P2`  
- Cache the most recent batch data in `AsyncStorage` (Expo)
- If network request fails, show cached data with a "Offline — showing last sync" banner
- Queue presence marks locally and sync when connectivity returns (simple retry queue in `appStore.ts`)

**J-6 · PIN quick re-auth** `P2`  
- The `security_mobile_pin_hash` field exists on `hr.employee`
- Add a `/api/security/mobile/auth/pin` endpoint that accepts `{employee_id, pin_hash}` and returns a new session
- Mobile: after session expiry, show PIN entry screen instead of full login

---

## Sprint K — Testing, CI, migration hardening (Weeks 13–14)
*Go-live readiness: nothing ships without this.*

---

### Testing

**K-1 · Full payroll pipeline integration test** `P0`  
A single test that exercises the complete flow:
1. Create rule set + public holidays
2. Create a guard with grade + certifications
3. Create a roster batch + slots + assign guard
4. Create attendance batch + records (present, late, AWOL, Sunday, night shift)
5. Call `action_generate_payslips()` on a payroll period
6. Call `action_compute_from_sources()` on the payslip
7. Assert: correct normal hours, Saturday hours, night hours, SSC amount, PAYE amount, net pay
8. Assert: anomaly flags triggered correctly (AWOL count, late count)

**K-2 · Billing pipeline integration test** `P1`  
- Create billing plan + generate invoice from attendance
- Assert line items match attendance hours
- Assert VAT computation is correct
- Assert amount-in-words is correct

**K-3 · Leave accrual integration test** `P1`  
- Create leave type with worked-time accrual (1 day per 22 worked days)
- Create 22 attendance records for a guard
- Run cron
- Assert balance increased by 1 day

**K-4 · Roster generation test** `P1`  
- Create site + posts + shift requirements + 5 guards with varying scores
- Run `action_suggest_guards()` on a slot
- Assert highest-scoring eligible guard is ranked first
- Assert disqualified guard is excluded
- Assert guard on approved leave is excluded

**K-5 · HttpCase API tests for mobile endpoints** `P1`  
- Authenticate as supervisor group user
- GET today's posting sheet → assert correct format
- POST mark presence → assert record updated
- POST batch submit → assert batch state changes

---

### CI / GitHub Actions

**K-6 · GitHub Actions test workflow** `P1`  
Create `.github/workflows/ci.yml`:
```yaml
on: [pull_request]
jobs:
  odoo-tests:
    runs-on: ubuntu-latest
    services:
      postgres: postgres:16
    steps:
      - checkout
      - install odoo
      - run: odoo --test-enable -i security_payroll_core,security_attendance,...
```
Run all `TransactionCase` tests on every PR. Block merge if tests fail.

**K-7 · Mobile TypeScript check** `P1`  
Add to CI:
```yaml
  mobile-typecheck:
    steps:
      - cd mobile && npm ci && npx tsc --noEmit
```

---

### `security_dogforce_migration`

**K-8 · Dry-run validation mode** `P0`  
Before a real import runs, a dry-run mode should:
- Parse the entire CSV
- Validate every row (required fields present, referenced records exist, no format errors)
- Return a validation report: total rows, valid rows, error rows with specific error per row
- Do NOT write to the database
- Add `dry_run` Boolean field to the migration job; "Validate Only" button in addition to "Run Import"

**K-9 · Dogforce-specific field mapping** `P0`  
Map real Dogforce data fields to the model fields:
- Existing employee Excel from Dogforce → `_import_employees()` column mapping
- Existing client list → `_import_clients()` column mapping
- Leave balances from current system → `_import_leave_balances()`
- Any outstanding loans → `_import_loans()`

Document the exact expected column names for each CSV template.

**K-10 · Rollback capability** `P1`  
- Before each import run, record all newly created record IDs in `created_ids` JSON field on the job
- Add "Rollback Import" button: deletes all records created by this job
- Guards against partial imports leaving orphaned data

---

## Sprint L — Go-live checklist (Week 15)

Before switching Dogforce from their current system to this platform:

**L-1 · Production environment** `P0`  
- Set up a VPS or cloud instance (not Docker Desktop) with: Odoo 19 + PostgreSQL 16 + Nginx reverse proxy + SSL certificate
- Configure `odoo.conf` for production: `workers = 4`, `proxy_mode = True`, `log_level = warn`
- Set up daily automated PostgreSQL backups to cloud storage

**L-2 · Data migration dry run** `P0`  
- Export all data from Dogforce's current system
- Run through the migration importer in dry-run mode
- Fix all validation errors
- Run live migration into a test database
- Verify payslip calculations match current system outputs for 3 historical payroll periods

**L-3 · Payroll parallel run** `P0`  
For the first 2 months after go-live, run payroll in both systems and compare:
- Namibia Labour Act compliance check against an independent payroll consultant
- Verify SSC and PAYE figures match NamRA requirements exactly

**L-4 · User training** `P1`  
Using the existing `OWL_BEGINNER_UI_GUIDE.md` and to-be-created user guides:
- HR/Payroll Officer training: payroll periods, payslips, leave management
- Operations Supervisor training: posting console, attendance marking
- Operations Manager training: roster board, payroll command center, executive dashboard
- Train one DogForce IT person on the Docker setup and backup/restore procedures

**L-5 · Mobile app deployment** `P1`  
- Build Expo standalone app for Android (APK or AAB for Play Store internal testing)
- Distribute to field supervisors via internal testing track
- Configure `EXPO_PUBLIC_ODOO_BASE_URL` in `.env` to point to production instance

---

## Task summary by effort

| Sprint | Focus | Weeks | % completion gain |
|--------|-------|-------|-------------------|
| G | Core module gaps (payroll, leave, loans, discipline, documents) | 1–3 | +12% → 70% |
| H | Operations, billing, equipment, base completions | 4–6 | +10% → 80% |
| I | Reporting, notifications, portal, accounting | 7–9 | +7% → 87% |
| J | Mobile app | 10–12 | +6% → 93% |
| K | Testing, CI, migration hardening | 13–14 | +5% → 98% |
| L | Go-live: production env, data migration, parallel run | 15 | +2% → 100% |

**Total remaining: ~15 weeks of focused development.**

---

## Priority order for a leaner go-live (if timeline is tight)

If you need to go live faster and can defer some features, here is the strict P0/P1-only path:

**Must have before first real payroll run:**
- G-1 (deduction cap), G-5 (leave accrual verified), G-9 (loan workflow), G-17 (doc requirements), H-1 (roster wizard), H-5 (invoice email), I-8 (payment UI), K-1 (payroll pipeline test), K-8 (migration dry-run), K-9 (field mapping), L-1, L-2, L-3

**Can run without (add in Month 2):**
- G-3 (payslip email), G-4 (Excel export), G-8 (leave calendar), G-11 (loan statement), G-14 (incident notification), G-16 (progressive discipline), H-2 (bulk copy), H-4 (fairness), H-7 (invoice wizard), H-8 (aging report), I-1, I-2, I-3, I-4, J-5, J-6, K-6, K-7

This leaner path takes approximately **8 weeks** to a minimum viable production go-live.
