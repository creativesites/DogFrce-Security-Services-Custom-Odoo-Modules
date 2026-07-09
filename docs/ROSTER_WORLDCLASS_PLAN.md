# World-Class Rostering — Implementation Plan

> Transforming the existing scoring engine and Roster Board into a fully automated, client-winning operations platform — without throwing away what already works.

---

## Current Baseline

| Component | Status | What works | What's missing |
|---|---|---|---|
| 150-pt scoring engine | Solid | Hard constraints + soft scoring, fairness/AWOL penalties | Only runs one slot at a time; no batch auto-assign |
| RosterBoard OWL | Solid | 3-panel grid, click-to-assign from sidebar, color by state | No drag-and-drop; no critical gap (red) state; no Auto-Fill button |
| SecurityBillingInvoice | Partial | `action_generate_from_attendance()` exists | Doesn't use payable_hours / premium buckets; no contract cap validation |
| SecurityNotification | Solid | Types: awol_alert, roster_gap, document_expiry, invoice_overdue | awol_alert and roster_gap not triggered automatically; no check-in lateness cron |
| Client contract model | **Missing** | SecurityBillingPlan has date range | No formal contract record; no validation gate on roster creation |
| Weekly snapshot model | **Missing** | — | No security.roster.week; no ops manager review workflow |
| Mobile field names | **Bug** | Mobile endpoints exist | `batch_id` should be `attendance_batch_id`; posting sheet often empty in app |

---

## The Three Operational Cycles

### Monthly — Ops Manager

1. **Generate batch from active shift requirements** — contract validation fires; can't create without active, unexpired contract covering the site.
2. **Click "Auto-Fill All"** — engine assigns highest-scoring eligible guard to every slot. High-value posts prioritized. Returns summary: *"42 filled · 3 critical gaps."*
3. **Review on the RosterBoard visual grid** — red cells = critical gaps. Drag a guard from the side panel to swap. Click slot → quick actions.
4. **Confirm batch** — notifications fire to all supervisors: *"June roster published for Site Alpha."* Attendance batch auto-creates in draft.

### Weekly — Ops Manager Check-In

5. **Open Weekly Dashboard** — single screen showing this week's slots across all sites, pre-filtered to the current 7-day window.
6. **Alert panel surfaces gaps** — unassigned slots for coming days, AWOLs already recorded today, understaffed sites highlighted.
7. **Adjust on the board, add override reason** — all changes logged with user + reason for full audit trail.
8. **Confirm week snapshot** — locks the `security.roster.week` record; review notes saved for compliance.

### Daily — Supervisor (Mobile)

9. **Open mobile app → today's posting sheet is pre-filled** — mobile field-name bug fixed in Phase 1.
10. **Mark attendance. AWOL → instant replacement suggestion** — AWOL triggers SecurityNotification (awol_alert) to ops manager with top replacement candidate.

---

## The Four Pillars

---

### Pillar 1 — Contract Validation Layer

Every active deployment must be bound to a legal commercial contract. Guardrails prevent uncontracted operations from ever entering the system.

#### New Model: `security.client.contract`

**File:** `custom_addons/security_operations/models/security_client_contract.py`

```python
class SecurityClientContract(models.Model):
    _name = "security.client.contract"
    _description = "Client Commercial Contract"

    name            = fields.Char(required=True)
    partner_id      = fields.Many2one("res.partner", required=True, string="Client")
    site_ids        = fields.Many2many("security.client.site", string="Covered Sites")
    date_start      = fields.Date(required=True)
    date_end        = fields.Date()
    max_guard_count = fields.Integer(string="Max Guards / Shift")
    state = fields.Selection([
        ("draft", "Draft"), ("active", "Active"),
        ("expired", "Expired"), ("cancelled", "Cancelled"),
    ], default="draft")
    billing_plan_id = fields.Many2one("security.billing.plan")

    def _is_active_for_date(self, check_date):
        if self.state != "active":
            return False
        if self.date_start > check_date:
            return False
        if self.date_end and self.date_end < check_date:
            return False
        return True

    @api.model
    def _get_active_contract_for_site(self, site, check_date):
        return self.search([
            ("partner_id", "=", site.partner_id.id),
            ("site_ids", "in", site.id),
            ("state", "=", "active"),
            ("date_start", "<=", check_date),
            "|", ("date_end", "=", False), ("date_end", ">=", check_date),
        ], limit=1)
```

#### Validation Hooks

Two `@api.constrains` hooks fire at the exact moments a violation could enter the system:

| Hook target | Triggers when | Checks | Error raised |
|---|---|---|---|
| SecurityShiftRequirement | Requirement state → active | Active contract covers the post's site; guard count cap ≥ requirement's guard_count | *"No active contract for Site Alpha. Activate a contract before enabling shift requirements."* |
| SecurityRosterBatch | Batch state → confirmed | All sites in batch have active contracts covering the full date range; max_guard_count not breached | *"Roster batch spans 2026-07-01–07-31 but the contract for Site Beta expires on 2026-07-15."* |

---

### Pillar 2 — One-Click Auto-Fill Engine

The scoring engine already exists and is correct. What's missing is a batch orchestrator that runs it across all unassigned slots in the right order, handles within-run double-bookings, and returns a useful summary.

#### `action_auto_fill_slots()` on SecurityRosterBatch

**File:** `custom_addons/security_shift_planner/models/security_shift_planner.py` (inherit SecurityRosterBatch here to avoid circular deps)

```python
def action_auto_fill_slots(self):
    self.ensure_one()
    unassigned = self.slot_ids.filtered(
        lambda s: not s.employee_id and s.state == "draft"
    )

    # Greedy order: high-value posts first, then by date, then shift start time.
    sorted_slots = unassigned.sorted(lambda s: (
        not s.is_high_value_shift,
        s.shift_date,
        s.shift_template_id.hour_start,
    ))

    assigned_today = {}   # {shift_date: set(employee_id)}
    filled, critical_gaps = [], []

    for slot in sorted_slots:
        slot.action_suggest_guards()
        suggestions = slot.suggestion_ids.sorted("rank")
        placed = False

        for sug in suggestions:
            guard_id = sug.employee_id.id
            day_set = assigned_today.setdefault(slot.shift_date, set())
            if guard_id not in day_set:
                sug.action_assign_to_slot()
                day_set.add(guard_id)
                filled.append(slot.id)
                placed = True
                break

        if not placed:
            critical_gaps.append(slot.id)

    # Flag critical gaps so the board can colour them red.
    self.env["security.roster.slot"].browse(critical_gaps).write({"critical_gap": True})

    msg = (
        f"Auto-fill complete: {len(filled)} slots assigned. "
        f"{len(critical_gaps)} critical gaps — no qualified guard available."
    )
    return {
        "type": "ir.actions.client",
        "tag": "display_notification",
        "params": {
            "title": "Auto-Fill Complete",
            "message": msg,
            "type": "success" if not critical_gaps else "warning",
            "sticky": True,
        },
    }
```

#### New field: `critical_gap` on SecurityRosterSlot

```python
# In SecurityRosterSlot (security_shift_planner.py extension)
critical_gap = fields.Boolean(default=False, string="Critical Gap")
```

#### Computed fields on SecurityRosterBatch

```python
unassigned_count   = fields.Integer(compute="_compute_gap_counts", store=True)
critical_gap_count = fields.Integer(compute="_compute_gap_counts", store=True)
fill_rate          = fields.Float(compute="_compute_gap_counts", store=True, string="Fill Rate %")

@api.depends("slot_ids.employee_id", "slot_ids.critical_gap", "slot_ids.state")
def _compute_gap_counts(self):
    for batch in self:
        total = len(batch.slot_ids.filtered(lambda s: s.state != "cancelled"))
        batch.unassigned_count = len(batch.slot_ids.filtered(lambda s: not s.employee_id and s.state == "draft"))
        batch.critical_gap_count = len(batch.slot_ids.filtered(lambda s: s.critical_gap))
        batch.fill_rate = ((total - batch.unassigned_count) / total * 100) if total else 0.0
```

A smart button on the batch form shows **"3 Critical Gaps"** — clicking it opens a filtered list of unfilled slots for manual intervention.

---

### Pillar 3 — Gap Alerts & Live Operations Dashboard

Three distinct alert surfaces: the batch summary (planning time), the weekly check-in (week-ahead), and the live ops view (day-of).

#### Notification Triggers to Wire Up

| Event | Trigger method | Notification type | Severity | Recipients |
|---|---|---|---|---|
| Roster batch confirmed | SecurityRosterBatch.action_confirm() post-hook | system | info | All supervisors for covered sites |
| Guard marked AWOL | SecurityAttendanceRecord.write() on presence = awol | awol_alert | critical | Ops manager + site supervisor; includes top-1 replacement suggestion |
| Check-in 15 min late | Scheduled cron every 10 min | awol_alert | warning | Site supervisor |
| Slot starts within 2 h, still unassigned | Same cron | roster_gap | critical | Ops manager |
| auto_fill leaves critical gaps | action_auto_fill_slots() post-hook | roster_gap | warning | Ops manager |

#### Computed Fields on SecurityAttendanceBatch

```python
awol_count_today      = fields.Integer(compute="_compute_live_counts")
absent_count_today    = fields.Integer(compute="_compute_live_counts")
missing_checkin_count = fields.Integer(compute="_compute_live_counts")

def _compute_live_counts(self):
    now = fields.Datetime.now()
    threshold = now - timedelta(minutes=15)
    for batch in self:
        recs = batch.record_ids
        batch.awol_count_today = len(recs.filtered(lambda r: r.presence == "awol"))
        batch.absent_count_today = len(recs.filtered(lambda r: r.presence == "absent"))
        batch.missing_checkin_count = len(recs.filtered(
            lambda r: r.scheduled_start
                and r.scheduled_start <= threshold
                and not r.check_in
                and r.presence not in ("absent", "awol")
        ))
```

#### New Model: `security.roster.week`

```python
class SecurityRosterWeek(models.Model):
    _name = "security.roster.week"
    _description = "Weekly Roster Review"

    batch_id       = fields.Many2one("security.roster.batch", required=True)
    week_start     = fields.Date(required=True)
    week_end       = fields.Date(compute="_compute_week_end", store=True)
    state          = fields.Selection([
        ("draft","Draft"), ("reviewed","Reviewed"), ("confirmed","Confirmed")
    ], default="draft")
    reviewer_id    = fields.Many2one("res.users")
    review_notes   = fields.Text()
    reviewed_at    = fields.Datetime(readonly=True)
    gap_count_snap = fields.Integer(string="Gaps at Review Time")

    def action_confirm_week(self):
        self.write({
            "state": "confirmed",
            "reviewer_id": self.env.uid,
            "reviewed_at": fields.Datetime.now(),
        })
```

#### New Crons

| Cron | Interval | Action |
|---|---|---|
| Scan Late Check-Ins & Gaps | Every 10 min | `action_scan_roster_gaps()` on SecurityNotification |
| Scan Upcoming Unassigned Slots | Every 30 min | Same action; checks slots starting within 2 hours |

---

### Pillar 4 — Roster-to-Billing Automation

Invoices pulled directly from verified payable hours with contract cap validation.

#### Enhanced Invoice Line Generation

**File:** `custom_addons/security_billing/models/security_billing.py`

Rewrite `_prepare_grouped_invoice_lines()` to use the five premium buckets from `shift_split.py` instead of a single hours total. Each premium category becomes a separate invoice line.

```python
PREMIUM_MAP = {
    "normal_hours":         ("Normal Hours",     1.0),
    "sunday_hours":         ("Sunday Premium",   "sunday_multiplier"),
    "saturday_hours":       ("Saturday Premium", "saturday_multiplier"),
    "public_holiday_hours": ("Public Holiday",   "public_holiday_multiplier"),
    "night_hours":          ("Night Shift",      "night_shift_multiplier"),
}

def _prepare_grouped_invoice_lines(self, attendance_records):
    lines = {}
    for rec in attendance_records:
        rule_set = rec.employee_id._get_active_rule_set()
        base_rate = rec.roster_slot_id.bill_rate or 0.0

        for field, (label, mult_field) in PREMIUM_MAP.items():
            hours = getattr(rec, field, 0.0)
            if not hours:
                continue
            multiplier = (
                getattr(rule_set, mult_field, 1.0)
                if rule_set and isinstance(mult_field, str)
                else mult_field
            )
            key = (rec.site_id.id, rec.post_id.id, rec.shift_template_id.id, field)
            lines.setdefault(key, {
                "name": label,
                "quantity": 0.0,
                "unit_price": base_rate * multiplier,
                "site_id": rec.site_id.id,
                "post_id": rec.post_id.id,
                "shift_template_id": rec.shift_template_id.id,
            })
            lines[key]["quantity"] += hours

    return list(lines.values())
```

#### Contract Cap Safety Check

```python
def _check_contract_caps(self):
    if not self.billing_plan_id:
        return
    contract = self.billing_plan_id.contract_id
    if not contract or not contract.max_guard_count:
        return
    actual = len(self.attendance_record_ids.mapped("employee_id"))
    if actual > contract.max_guard_count:
        raise ValidationError(
            f"Invoice covers {actual} guards but contract cap is {contract.max_guard_count}. "
            "Flag for executive review before sending."
        )
```

#### Attendance-to-Invoice Gate

When a `SecurityAttendanceBatch` is locked, a **"Generate Invoice"** smart button appears. Clicking it opens `SecurityBillingInvoiceWizard` pre-populated with the batch period and source set to "attendance". Zero manual data entry.

---

## Custom UI Components

### RosterBoard v2 — Delta from Current

The existing board is a solid foundation. These are targeted additions only — no rewrite.

| Feature | Status in v1 | Change in v2 |
|---|---|---|
| Auto-Fill button in toolbar | Missing | Add button calling `action_auto_fill_slots()`; on return, refresh board and show toast |
| Critical gap (red) cell color | Missing | Check `slot.critical_gap`; render red CSS class |
| Drag-and-drop guard assignment | Click-to-assign only | Make guard pool items `draggable="true"`; slot cells are drop targets; on drop call `action_assign_to_slot` |
| Slot context menu | Missing | Right-click slot: "Suggest Guards", "Clear Assignment", "View Guard Profile", "Mark Override" |
| Batch summary bar | Basic stats sidebar | Top bar: fill rate progress bar, critical gap count badge, contract expiry warning |
| "Show gaps only" toggle | Missing | Hides fully-assigned rows so manager sees only what needs attention |

**Color coding:**
- 🟢 Green — assigned, guard confirmed
- 🟡 Yellow — unassigned, eligible guards exist (suggestions available)
- 🔴 Red — critical gap, no eligible guard found anywhere
- ⬜ Grey — draft/empty slot

### WeeklyCheckIn OWL Component

Registered as `security_shift_planner.weekly_checkin`. Reuses the RosterBoard component internally, pre-filtered to a 7-day window. Adds:
- Alert panel above the grid showing unassigned count, AWOLs today, understaffed sites
- "Confirm Week" button that creates/updates the `security.roster.week` snapshot
- Compact view mode (no right sidebar) to maximize grid space

### Live Operations View (Today's Deployments)

Built as an Odoo Kanban view with custom groupBy — keeps it maintainable without a full OWL build.

| Column | Records shown | Indicator |
|---|---|---|
| Scheduled | Shift not yet started | Neutral |
| On Shift | check_in recorded, shift ongoing | Green |
| Late / No Check-In | Scheduled start + 15 min, no check_in | Amber |
| AWOL | presence = awol | Red |
| Absent | presence = absent | Muted red |

---

## New Models Summary

| Model | Module | Purpose |
|---|---|---|
| `security.client.contract` | security_operations | Commercial contract; date range, site coverage, guard cap, links to billing plan |
| `security.roster.week` | security_shift_planner | Ops manager weekly review snapshot; state, reviewer, notes, gap count at review time |

## Key Backend Actions Summary

| Action | Model | Output |
|---|---|---|
| `action_auto_fill_slots()` | SecurityRosterBatch | Toast + critical_gap flags; smart button count updated |
| `_compute_gap_counts()` | SecurityRosterBatch | unassigned_count, critical_gap_count, fill_rate stored fields |
| `_compute_live_counts()` | SecurityAttendanceBatch | awol_count_today, absent_count_today, missing_checkin_count |
| `action_scan_roster_gaps()` cron | SecurityNotification | Creates roster_gap + awol_alert notifications with replacement suggestions |
| `action_confirm_week()` | SecurityRosterWeek | State → confirmed; reviewer + timestamp recorded |
| `_prepare_grouped_invoice_lines()` | SecurityBillingInvoice | Invoice lines split by premium bucket with correct rate multipliers |
| `_check_contract_caps()` | SecurityBillingInvoice | ValidationError if guard count exceeds cap |

---

## Phased Delivery Roadmap

### Phase 1 — Foundation (2–3 weeks)

- `security.client.contract` model + views + validation hooks on ShiftRequirement and RosterBatch
- `action_auto_fill_slots()` in shift_planner module; `critical_gap` flag on slot
- `unassigned_count` / `critical_gap_count` / `fill_rate` computed fields on batch
- Auto-Fill button on RosterBoard; red critical-gap cell color; batch summary bar
- **Fix mobile field bug:** `batch_id` → `attendance_batch_id` in all security_mobile controllers

> **Outcome:** Ops manager opens the board, clicks Auto-Fill, sees 42 green and 3 red cells in seconds. Mobile posting sheet actually works.

### Phase 2 — Ops Dashboard (1–2 weeks)

- `security.roster.week` model + confirm workflow + views
- WeeklyCheckIn OWL component (reuses RosterBoard, adds alert panel + "Confirm Week")
- Live Ops kanban view (today's attendance by site, grouped by status)
- `awol_count` / `missing_checkin_count` computed fields on attendance batch
- Wire AWOL notification trigger on `SecurityAttendanceRecord.write()`
- 10-min cron: scan late check-ins and upcoming unassigned slots → roster_gap notifications
- Batch confirmed hook → notify supervisors

> **Outcome:** Duty manager opens Live Ops at 06:15 and sees exactly which guards haven't checked in. AWOL triggers instant notification with replacement name.

### Phase 3 — Billing Pipeline (1–2 weeks)

- Enhance `_prepare_grouped_invoice_lines()` to use payable_hours + 5 premium buckets
- `_check_contract_caps()` constraint on invoice confirmation
- "Generate Invoice" smart button on locked attendance batch
- Wire `contract_id` FK from SecurityBillingPlan → SecurityClientContract
- Invoice line view: show premium category breakdown per line

> **Outcome:** Lock a posting sheet → one click → draft invoice with itemized premium hours. Contract cap violation blocks sending with a clear message.

### Phase 4 — Polish (ongoing)

- Drag-and-drop guard assignment on RosterBoard (HTML5 DnD API)
- Shift-swap workflow: clear slot → override reason → re-assign with audit trail
- SMS gateway stub for AWOL and replacement alerts
- Saturday/night premium multipliers wired in payroll compute (existing gap)
- Automated E2E tests: auto-fill, AWOL notification, invoice generation

> **Outcome:** Full end-to-end audit trail, drag-and-drop UX, SMS alerts. Demo-ready for enterprise prospects.

---

## What's New vs Extended vs Fixed

| New | Extended | Fixed |
|---|---|---|
| `security.client.contract` model | RosterBoard (Auto-Fill btn, red cells, context menu) | Mobile `batch_id` field name bug |
| `security.roster.week` model | Billing invoice line generation (premium buckets) | Saturday/night multipliers in payroll |
| Live Ops kanban view | SecurityNotification (new cron triggers) | |
| WeeklyCheckIn OWL component | | |

---

## The Demo Script

> *"Here's your June roster. I click Auto-Fill. Done — 42 guards assigned across 10 sites in 3 seconds. Those two red cells? Critical gaps — no certified guard available. You need to hire or cross-train, and the system just told you that before the month even starts. Now watch — I drag Khumalo from the sidebar onto Gate A Saturday. Assigned. One critical gap left. I click Confirm. Every supervisor gets a notification right now. And when your duty manager arrives at 06:00 Monday, this screen shows him exactly who checked in and who didn't — in real time, across all sites. If anyone goes AWOL, his replacement candidate is already in the notification."*

Full monthly roster → confirmed → live ops monitoring, under 2 minutes of screen time.

---

*See [ARCHITECTURE.md](../ARCHITECTURE.md) for module dependency context. Implementation starts on branch `claude/repo-system-overview-v0t71v`.*
