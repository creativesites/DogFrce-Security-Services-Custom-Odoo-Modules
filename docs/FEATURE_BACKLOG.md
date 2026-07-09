# DogForce / DeployGuard — Feature Backlog & Improvement Plan

**Created:** 2026-06-16  
**Purpose:** Cohesive plan collecting all product feedback, missing features per module, and architectural decisions needed to reach 100% completion.

---

## Concept explanations

### Rate Multiplier (on Shift Requirements)
The **Rate Multiplier** is the factor applied to a guard's base hourly rate when they work a premium shift. It lives on `SecurityPayrollRuleSet` and `SecurityShiftRequirement`.

| Shift type | Multiplier | How it works |
|---|---|---|
| Normal weekday | 1.0× | Base hourly rate |
| Saturday | 1.25× | Base × 1.25 |
| Night (20:00–06:00) | 1.25× | Base × 1.25, applied to night hours only |
| Sunday | 1.5× | Base × 1.5 |
| Public Holiday | 1.5× | Base × 1.5 |
| Overtime (beyond 12h) | 1.5× | Base × 1.5 |

The `split_shift_by_boundaries()` utility splits a shift into buckets (e.g. a 18:00–06:00 shift crossing midnight into a Sunday correctly assigns 6 hours at normal + 6 hours at Sunday rate). Each bucket becomes a separate earning line on the payslip.

**Where to configure:** Security → Payroll → Rule Sets → Rate Multipliers tab.

### Fairness Weight (on Shift Requirements / Scoring Engine)
The **Fairness Weight** (0.0–1.0) in the scoring engine controls how heavily the system penalises guards who have accumulated disproportionately more premium or demanding shifts compared to their peers of the same grade at the same sites, over a rolling 90-day window.

- **Weight = 0.0** — fairness is ignored; the highest-reliability guard always wins regardless of how often they've worked Sundays or nights.
- **Weight = 1.0** — equalization dominates; the system strongly prefers guards who have worked fewer premium shifts, even if their reliability score is lower.
- **Default = 0.2** — light fairness correction. Reliability still drives most decisions; the system only redistributes if one guard has >50% more premium shifts than peers.

**Why it matters:** Without this, the most reliable guard on each site ends up working every Sunday and public holiday. Over time, this creates resentment, fatigue, and churn. The fairness weight ensures premium shifts rotate across the eligible pool.

**Where to configure:** Security → Operations → Shift Requirements → Scoring Weights (per shift requirement, overridable per site).

---

## Priority legend

| Code | Meaning |
|------|---------|
| 🔴 P0 | Blocking — system broken or data wrong without this |
| 🟠 P1 | Critical for daily operations — operators hit a wall |
| 🟡 P2 | Important — workaroundable but painful |
| 🟢 P3 | Nice-to-have |

---

## 1. Roster & Scheduling

### Philosophy
The system's job is to ensure **every client site is fully staffed every day with zero manual effort**. Humans approve, adjust, or handle exceptions. The generation and assignment loop should be as automated and frictionless as possible.

### 1.1 Roster Slots — custom assignment view 🟠 P1

**Problem:** Creating and assigning guards to slots is done one slot at a time. No batch workflow, no requirement visibility, no grade enforcement in the UI.

**Solution — new Roster Slot Assignment View:**

```
┌──────────────────────────────────────────────────────────────────┐
│  Roster Slots  [Batch: May 2026 ▼]  [Site: All ▼]  [Unassigned ▼]│
│  [✓ Select All]  [Batch Assign ▼]  [Auto-Fill Open Slots]        │
├─────────────┬───────────┬──────────┬──────────┬─────────────────┤
│ □ Date      │ Post      │ Shift    │ Required │ Assigned Guard   │
├─────────────┼───────────┼──────────┼──────────┼─────────────────┤
│ □ Fri 2 Jun │ Main Gate │ Day      │ Grade B+ │ A. Smith ▼      │
│ □ Fri 2 Jun │ Control Rm│ Day      │ Grade A  │ — (OPEN) ▼      │
│ □ Fri 2 Jun │ Main Gate │ Night    │ Grade B+ │ T. Nakale ▼     │
│ □ Sat 3 Jun │ Main Gate │ Day      │ Grade B+ │ — (OPEN) ▼      │
└─────────────┴───────────┴──────────┴──────────┴─────────────────┘
```

**Features to build:**

1. **Batch assign** — checkbox column on each slot row; select multiple open slots → "Batch Assign" dropdown → pick one guard → assigns all selected slots in one action. (Backend: new `action_batch_assign(slot_ids, employee_id)` on `security.roster.slot`.)

2. **Grade enforcement** — the guard dropdown on each row only shows guards whose grade ≥ the slot's `post_type.min_grade_id`. Below-grade guards are hidden, not just warned.

3. **Site requirement panel** — hovering or clicking the post name shows a tooltip/popover with: required grade, required certifications, required attributes, minimum reliability score. So the operator knows exactly which guards fit before selecting.

4. **Preferred guard per shift** — add `preferred_employee_id` Many2one on `security.shift.requirement`. When generating roster slots, the wizard pre-fills `employee_id` from the preferred guard if they are eligible (no conflict, not on leave, grade met). Example use case: "Main Gate Day Shift should always be Guard X unless unavailable."

5. **Open slot alert strip** — a sticky banner at the top of the view showing: "⚠ 4 slots unassigned for tomorrow". Clicking filters to unassigned slots.

**Backend additions:**
- `action_batch_assign(slot_ids, employee_id)` on `security.roster.slot` — validates eligibility for each slot (grade, certs, not double-booked) before assigning; returns a report of any failures.
- `preferred_employee_id` Many2one field on `security.shift.requirement`.
- `action_auto_fill_open_slots(batch_id)` — runs the scoring engine on every open slot in a batch and assigns the top-ranked eligible guard.

---

### 1.2 Preferred guards per site/shift 🟠 P1

Some clients want the same guard at the same post every day. The system must support this.

**Implementation:**
- `preferred_employee_id` Many2one on `security.shift.requirement` — the guard preferred for this site/post/shift combination.
- `allow_preferred_only` Boolean — if True, only the preferred guard should be assigned here; any other assignment triggers a warning.
- Roster generation wizard checks `preferred_employee_id` first. If the guard is available and eligible, they are assigned. If not, the system falls back to the scoring engine and flags the slot as "Preferred guard unavailable."

---

### 1.3 All sites must be filled — zero-gap enforcement 🔴 P0

**The rule:** Every slot defined in shift requirements must be assigned a guard. Any unassigned slot, anywhere, is an operational failure.

**What to build:**

1. **Daily "Gaps" cron** (runs at 05:00 each day) — checks every `security.roster.slot` with `shift_date = today` and `state != cancelled`. Any slot with no `employee_id` triggers:
   - A `security.notification` record with `severity = 'critical'` — red, never auto-dismissed.
   - An email to the Operations Manager.
   - A flag on the client site: `has_open_slots_today = True` (computed).

2. **Roster Board coverage indicator** — the existing stats panel already shows assigned/unassigned. Add a red badge in the browser tab title when unassigned > 0.

3. **Guard unassigned alert** — any active guard who is not on leave and not assigned to any slot today also triggers an alert: "Guard X has no assignment today." Prevents accidental idle guards.

---

### 1.4 Auto-generate roster batches from contracts 🟠 P1

**Problem:** Every month, someone manually creates a roster batch and manually creates all the slots for every site. When a billing plan covers 2 years, this is 24 months of manual batch creation.

**Solution — Contract-Driven Auto-Generation:**

**Architecture decision:** Generate one month ahead, not the full contract. The system auto-creates the next month's batch on the 20th of each month, based on active billing plans + shift requirements.

**How it works:**

```
security.billing.plan (active)
    └── site_ids → security.client.site
           └── shift_requirement_ids → security.shift.requirement
                  (days_of_week, post_id, shift_template_id, required_guards_count)
                  └── auto-generate for each day in next month:
                         security.roster.slot (state=draft, no employee assigned)
```

**Cron job:** `action_cron_auto_generate_next_month_batches()` — runs on the 20th of each month:
1. For each active `security.billing.plan`:
2. Calculate next month's date range.
3. If no `security.roster.batch` exists for that plan + month: create one.
4. For each day in the range, for each `shift_requirement` on the plan's sites:
   - Create `required_guards_count` draft `security.roster.slot` records.
5. Notify Operations Manager: "June 2026 roster batch auto-created. 186 slots need assignment."

**Wizard fallback:** Operations Manager can also trigger this manually for any period: "Generate Roster for Next Month" button on the billing plan form.

**Why not generate the full 2-year contract?**
- Guard availability, grades, and certs change month to month.
- Generating too far ahead means most assignments will be wrong by the time the shifts arrive.
- One month ahead is the right balance: enough lead time to fix gaps, not so far that data is stale.

---

### 1.5 Client Site page — comprehensive management view 🟡 P2

**Problem:** The client site form is a standard Odoo form. Managers can't see day-to-day status, can't manage slots, can't see the full picture of a site without navigating to five different menus.

**Solution — Site Management Hub (custom Tier-3 OWL page for each site):**

```
SITE: Acme HQ — Main Branch                          [Client: Acme Corp]
Active contract: May 2026 – Apr 2028                 [Status: ● Active]

TABS: Overview | Calendar | Guards | Requirements | Billing | History

── OVERVIEW TAB ─────────────────────────────────────────────────────
  Today: 4/4 posts filled ✅          This month: 96.2% coverage ✅
  Next open slot: None                Outstanding invoice: N$28,400

── CALENDAR TAB ─────────────────────────────────────────────────────
  [◀ May]  JUNE 2026  [Jul ▶]

  Mon 1  Tue 2  Wed 3  Thu 4  Fri 5  Sat 6  Sun 7
  ████   ████   ████   ████   ████   ████   ██░░  ← 1 open slot
  ↑ all filled        ↑ click → slot detail + guard names + change

  Clicking a day opens a popover:
  ┌────────────────────────────────────┐
  │  Thursday 4 June                   │
  │  Main Gate Day  → A. Smith    [✎] │
  │  Main Gate Night→ T. Nakale   [✎] │
  │  Control Room   → B. Jones    [✎] │
  │  Guard 4 Post   → — OPEN ⚠   [+] │
  └────────────────────────────────────┘
  [✎] opens inline guard-change picker
  [+] opens assign-guard picker for the open slot

── REQUIREMENTS TAB ─────────────────────────────────────────────────
  Post          Shift    Days     Guards  Grade Min  Certifications
  Main Gate     Day      Mon–Sun  1       Grade B    Firearm
  Main Gate     Night    Mon–Sun  1       Grade B    Firearm
  Control Room  Day      Mon–Fri  1       Grade A    CCTV, Firearm

── GUARDS TAB ───────────────────────────────────────────────────────
  Currently assigned guards at this site (from active roster slots)
  with reliability scores, any upcoming leave, any document expiries.
```

**Backend additions:**
- `site_coverage_today` computed field on `security.client.site`.
- `site_coverage_month` computed field.
- API endpoint for the calendar: `GET /security/site/<id>/calendar?month=2026-06` returns daily fill status.

---

### 1.6 Client sites organised by client 🟡 P2

**Simple fix:** In the `security.client.site` list view, set default `group_by = partner_id`. Also add `partner_id` as the first column and make it a clickable link to the client (res.partner) form. The tree view should be grouped by client by default so the operator immediately sees "Acme Corp → 3 sites", "Bank of Namibia → 2 sites" etc.

---

## 2. Workforce / Attendance

### 2.1 Custom Attendance Records view 🟡 P2

**Problem:** The default list view shows one record per row with no visual hierarchy. With 30+ guards across multiple sites, reviewing attendance is tedious.

**Solution — Attendance Summary View (new Tier-2 OWL):**

A **daily summary grid** — each column is a posting batch (site + date), each row is a guard, each cell shows their status for that batch:

- Green chip = Present
- Orange chip = Late (shows late minutes on hover)
- Red chip = AWOL
- Grey = Absent (authorised)
- Empty = Not scheduled

Clicking any cell opens the attendance record form for inline correction.

Filters: date range, site, status. Sortable by name, site, reliability score.

This replaces the need to open individual records and gives supervisors and managers a daily snapshot in one screen.

---

### 2.2 Attendance Heatmap improvements 🟡 P2

**Fixes needed:**
1. ~~`v2 is not a function` bug on site filter~~ — **fixed** (2026-06-16, `onFilterSiteChange` named method).
2. **Site filter actually works** — currently `visibleGuards` ignores the `filterSiteId` (marked as placeholder in the code). Needs to enrich the guard query with `site_id` from their current roster assignment: `searchRead("hr.employee", [...], ["id", "name", "security_current_site_id"])`.
3. **Date range selector** — currently hard-coded to 30 days. Add a date range picker: "Last 7 / 14 / 30 / 60 days" buttons.
4. **Summary row** — add a summary row at the bottom showing attendance % per day (green if ≥90%, amber if 80–89%, red if <80%).
5. **Guard search** — a search input to filter by guard name.
6. **Export button** — CSV export of the visible heatmap data.

---

## 3. Client Billing

### 3.1 Billing tightly linked to rostering 🔴 P0

**Rule:** An active billing plan = the client's sites must be staffed. The system should enforce this automatically.

**What to build:**
- When a new `security.billing.plan` is activated: automatically trigger roster batch generation for the current and next month (calls the same cron logic as §1.4).
- The "Gaps" cron (§1.3) should also check: for any site that has an active billing plan but no roster batch for today → critical alert.
- On the billing plan form: add a "Roster Coverage" smart button showing % of slots filled for the current month's batch across all the plan's sites.

### 3.2 Billing dashboard 🟡 P2

**New Tier-3 OWL client action: Billing Command Center**

```
┌─────────────────────────────────────────────────────────────────┐
│  BILLING — June 2026                    [Generate Invoices] [▼] │
├───────────┬──────────────┬──────────────┬────────────────────────┤
│ Active    │ Invoiced MTD │ Collected MTD│ Outstanding            │
│ Plans: 12 │ N$284,000    │ N$242,000    │ N$42,000               │
├───────────┴──────────────┴──────────────┴────────────────────────┤
│  ACTIVE BILLING PLANS                                           │
│  Client          Sites  Rate/shift  Status    Invoice Due       │
│  Acme Corp       3      N$1,200     ✅ Paid    —                │
│  Bank of Namibia 2      N$1,400     ⚠ 12 days N$28,400         │
│  City Council    1      N$900       ⚠ 3 days  N$15,200         │
│  Namibia Police  4      N$1,100     ❌ Overdue N$44,800 (45d)   │
├─────────────────────────────────────────────────────────────────┤
│  RECENT INVOICES [Aging: Current | 1-30 | 31-60 | 61-90 | 90+] │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 Document preview and print 🟠 P1

All billing documents (invoices, credit notes, statements) need:
- **Preview** — clicking "Preview" renders the QWeb PDF in an iframe within the Odoo interface. No download required to see what will be sent.
- **Print** — browser print dialog triggered with the correct paper size (A4).
- **Download** — current PDF download behaviour preserved.

**Implementation:** OWL `PreviewModal` component wrapping an `<iframe src="/report/pdf/...">`. Add a "Preview" button to invoice form header alongside existing "Print" button.

---

## 4. Reporting

### 4.1 All reporting views — improvement plan 🟡 P2

For each existing report, add:
- **Filter toolbar** — date range, site, guard, status filters at the top of every view.
- **Export button** — PDF and CSV export on every report view.
- **Custom OWL view** where the standard pivot/list is insufficient.

Specific views to improve:

| Report | Improvement |
|--------|-------------|
| Attendance summary | Replace pivot with the grid view described in §2.1 |
| Payroll register | Add column-level totals and comparison to prior period |
| Incident report | Add severity breakdown chart (doughnut) |
| Guard reliability | Add trend arrows (↑ ↓ →) vs 30-day snapshot |
| Invoice aging | Already done (5-bucket); add chart visualisation |
| Leave balance | Add projected-to-year-end column |

### 4.2 Client Service Reports — PDF preview, generate, print 🟠 P1

**Current state:** Client service report records exist but the workflow for generating and delivering them is unclear.

**What to build:**
1. **"Generate Report" button** on the `security.client.service.report` form — triggers the QWeb PDF render and attaches it to the record.
2. **"Preview" button** — same PreviewModal as §3.3.
3. **"Send to Client" button** — emails the PDF to the client's billing contact with a standard covering letter template.
4. **Auto-generate on period close** — when a payroll period closes, automatically generate client service reports for all active billing plans covering that period.

---

## 5. Equipment & Fleet

### 5.1 Equipment Dashboard 🟡 P2

**New Tier-3 OWL client action: Equipment Overview**

```
┌─────────────────────────────────────────────────────────────────┐
│  EQUIPMENT & ASSETS                               [Issue Kit] [▼]│
├──────────┬──────────┬──────────────┬───────────────────────────┤
│ Allocated│ Returned │ Damaged/Lost │ Pending Return             │
│ 142      │ 18 (mth) │ 3            │ 7 overdue                  │
├──────────┴──────────┴──────────────┴───────────────────────────┤
│  BY CATEGORY          │  RECENT ACTIVITY                        │
│  Uniforms     94 out  │  ● A. Smith returned radio (Good)       │
│  Radios       31 out  │  ● B. Jones: damage claim (Radio N$350) │
│  Firearms     12 out  │  ● 3 guards: pending acknowledgement    │
│  ID Cards     142 out │  ● 7 allocations overdue for return     │
│                       │  [View All Overdue →]                   │
├───────────────────────┴─────────────────────────────────────────┤
│  OVERDUE RETURNS (7)                                            │
│  Guard       Equipment  Issued       Days Overdue  Site         │
│  C. David    Radio #14  2026-05-01   46 days       Site Alpha   │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Fleet Dashboard 🟡 P2

**New Tier-3 OWL client action: Fleet Overview**

```
┌─────────────────────────────────────────────────────────────────┐
│  FLEET MANAGEMENT                                               │
├──────────┬──────────┬──────────────┬───────────────────────────┤
│ Vehicles │ Active   │ In Service   │ Fuel Cost MTD              │
│ 8 total  │ 6        │ 1            │ N$12,400                   │
├──────────┴──────────┴──────────────┴───────────────────────────┤
│  TODAY'S RUNS                │  SERVICE DUE                     │
│  Van 1 → Site Alpha 05:30    │  Van 3: service in 850 km        │
│  Van 2 → Site Bravo 05:45    │  Van 5: inspection overdue       │
│  Van 3 → City Centre 06:00   │                                  │
├──────────────────────────────┴─────────────────────────────────┤
│  VEHICLE STATUS (click to drill in)                            │
│  Van 1  NWD 2341  ● Running  Driver: J. Nakawa  12 passengers  │
│  Van 2  NWD 1882  ● Running  Driver: K. Amupala  8 passengers  │
│  Van 3  NWD 5503  ◐ In Service  (due back: 14:00)              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Payroll

### 6.1 Fix Payroll Period creation 🔴 P0

**Problem:** Users cannot add a new Payroll Period.

**Likely cause:** The `state` field default or the `action_generate_payslips()` method has a constraint that requires all attendance batches for the period to be locked before a period can be confirmed. But the UI doesn't guide the user through this prerequisite.

**Fix — two parts:**

1. **Backend:** Add validation in `SecurityPayrollPeriod.action_generate_payslips()` that checks for unlocked batches and returns a user-friendly error: "4 attendance batches for this period are still in Draft state. Please lock all posting sheets before generating payslips." (Not a hard block — add a "Proceed Anyway (override)" option for the Payroll Manager role.)

2. **Frontend:** On the payroll period creation wizard (Step 1), show a checklist of attendance batches for the selected date range and their lock status. If any are unlocked, show a warning but allow the payroll officer to navigate directly to Attendance → Posting Sheets to lock them.

**Workaround until fixed:** Go to Attendance → Posting Sheets → filter by month → lock each batch. Then retry creating the Payroll Period.

### 6.2 Loans — auto-generate deduction schedule 🔴 P0

**Problem:** Active loans exist on the demo server but no deduction lines are being generated. Payroll runs complete without deducting loan installments.

**Root cause:** The `action_activate()` method on `SecurityEmployeeLoan` is supposed to generate `SecurityLoanDeduction` schedule lines when the loan is activated. If existing loans were created directly in `active` state (bypassing `action_activate()`), the schedule lines were never created.

**Fix — two parts:**

1. **Backfill migration:** Add a one-time button "Regenerate Deduction Schedule" on the loan form (visible when `state = 'active'` and `deduction_ids` is empty). This calls `action_activate()` logic to generate the missing schedule lines.

2. **Guard on `action_compute_from_sources()`:** When computing payslip deductions, if an active loan has no schedule lines, log a warning notification to HR rather than silently skipping the deduction.

3. **Fix going forward:** The loan form should validate on save: if `state = 'active'` and `deduction_ids` is empty → raise a `ValidationError` prompting the user to generate the schedule.

---

## 7. New module: Client Onboarding 🟠 P1

### Purpose
Automate the full setup required when a new client signs a contract: create the billing plan, sites, posts, shift requirements, and the first month's roster batch in a single guided wizard. Eliminates 20–30 minutes of manual data entry.

### Module: `security_client_onboarding`

**Wizard model:** `security.client.onboard.wizard` (transient)

**Step 1 — Client & Contract:**
- Select or create `res.partner` (client)
- Contract start date, contract end date
- Payment terms

**Step 2 — Sites:**
- Add one or more sites (name, location, supervisor)
- For each site: add posts (name, post type)

**Step 3 — Shift Requirements:**
- For each site + post: define shifts (template, days of week, required guard count, minimum grade, required certs, rate per shift for billing, preferred guard)
- System shows a preview: "This will generate 186 slots per month"

**Step 4 — Billing Plan:**
- Auto-created from Step 1 + 3 data
- Invoice frequency (monthly/fortnightly), auto-invoice toggle
- Payment terms

**Step 5 — First Roster:**
- "Generate this month's roster batch now" toggle (default: On)
- Preview: shows the slots that will be created
- Option to auto-assign guards using the scoring engine or leave unassigned for manual review

**Step 6 — Confirm:**
- Summary of everything that will be created
- "Complete Onboarding" button creates all records atomically

**What gets created in one click:**
- 1× `res.partner` (if new client)
- N× `security.client.site`
- N× `security.post` per site
- N× `security.shift.requirement` per post
- 1× `security.billing.plan`
- 1× `security.roster.batch` for current month
- N× `security.roster.slot` for all shift requirements × days in month

---

## 8. Missing features — complete module checklist

### `security_operations` (to 100%)
- [ ] Preferred guard per shift requirement (`preferred_employee_id`, `allow_preferred_only`)
- [ ] Batch assign action on roster slots
- [ ] Site Management Hub OWL view (§1.5)
- [ ] `site_coverage_today` and `site_coverage_month` computed fields
- [ ] Gaps cron + critical alerts for unfilled slots (§1.3)
- [ ] Guard unassigned alert (guard with no slot today)
- [ ] Contract-driven batch auto-generation cron (§1.4)
- [ ] Client sites grouped by client by default in list view

### `security_shift_planner` (to 100%)
- [x] ~~Roster Board modal JS bugs fixed~~ (2026-06-16)
- [ ] Grade enforcement in guard pool — don't show below-minimum-grade guards
- [ ] Roster Slot Assignment View with batch assign
- [ ] `action_batch_assign(slot_ids, employee_id)` backend method
- [ ] `action_auto_fill_open_slots(batch_id)` backend method
- [ ] Preferred guard pre-fill in slot generation

### `security_attendance` (to 100%)
- [x] ~~Heatmap v2 bug fixed~~ (2026-06-16)
- [ ] Heatmap site filter actually filters guards (enrich guard query with site)
- [ ] Heatmap date range selector (7/14/30/60 days)
- [ ] Heatmap summary row (daily attendance %)
- [ ] Custom Attendance Summary Grid OWL view
- [ ] Attendance CSV export from summary view

### `security_billing` (to 100%)
- [ ] Billing linked to rostering: activating plan triggers batch generation
- [ ] Billing Command Center dashboard OWL
- [ ] Invoice/credit note PDF preview modal
- [ ] Client service report: generate, preview, send buttons
- [ ] Auto-generate client service reports on period close

### `security_payroll_core` (to 100%)
- [ ] Fix payroll period creation — prerequisite checklist in wizard
- [ ] Payroll period creation: friendly error when attendance batches unlocked
- [ ] Loan backfill: "Regenerate Deduction Schedule" button on loan form
- [ ] Loan guard: warn when active loan has no deduction lines

### `security_loans` (to 100%)
- [ ] Backfill deduction lines for existing active loans with no schedule
- [ ] Validate on save: active loan must have deduction lines
- [ ] Loan statement PDF (QWeb report showing installments + remaining balance)

### `security_equipment` (to 100%)
- [ ] Equipment Dashboard OWL (§5.1)
- [ ] Overdue return alerts (wire to notifications module)

### `security_fleet` (to 100%)
- [ ] Fleet Dashboard OWL (§5.2)
- [ ] Service due alerts (wire to notifications module)

### `security_reporting` (to 100%)
- [ ] Date range / site / guard filter toolbar on all report views
- [ ] PDF + CSV export on all views
- [ ] Incident report with severity breakdown chart
- [ ] Guard reliability trend arrows

### `security_client_reports` (to 100%)
- [ ] "Generate Report" button on service report form
- [ ] PDF preview modal (PreviewModal OWL component)
- [ ] "Send to Client" button with email template
- [ ] Auto-generate on payroll period close

### New module: `security_client_onboarding`
- [ ] Scaffold module
- [ ] 6-step wizard model
- [ ] Wizard OWL view
- [ ] Atomic creation of all records on completion
- [ ] Integration with billing plan activation

---

## 9. Bug tracker

| ID | Module | Description | Status | Fixed |
|----|--------|-------------|--------|-------|
| BUG-001 | `security_shift_planner` | Roster Board modal: `v12`/`v14`/`v16 is not a function` on Post, Shift Template, Guard selects | ✅ Fixed | 2026-06-16 |
| BUG-002 | `security_attendance` | Heatmap: `v2 is not a function` on Site filter | ✅ Fixed | 2026-06-16 |
| BUG-003 | `security_payroll_core` | Cannot create new Payroll Period | 🔴 Open | — |
| BUG-004 | `security_loans` | Active loans not generating payroll deductions | 🔴 Open | — |

---

## 10. Implementation sequence (recommended)

### Week 1 — Blockers (P0)
1. BUG-003: Fix Payroll Period creation
2. BUG-004: Fix Loans deduction backfill
3. §1.3: Gaps cron + critical alerts
4. §3.1: Billing ↔ rostering link

### Week 2 — Core UX (P1)
5. §1.1: Roster Slot Assignment View + batch assign
6. §1.2: Preferred guards per shift
7. §1.4: Contract-driven auto-batch generation
8. §3.3: Invoice PDF preview and print
9. §4.2: Client Service Report generate/preview/send

### Week 3 — Site & Reporting (P1–P2)
10. §1.5: Site Management Hub OWL
11. §1.6: Sites grouped by client
12. §7: Client Onboarding module
13. §4.1: Report filter toolbars + exports

### Week 4 — Dashboards & Polish (P2)
14. §3.2: Billing Command Center
15. §5.1: Equipment Dashboard
16. §5.2: Fleet Dashboard
17. §2.1: Attendance Summary Grid
18. §2.2: Heatmap improvements

---

*Update this document as items are completed. Move completed items to the Bug Tracker table with their fix date.*
