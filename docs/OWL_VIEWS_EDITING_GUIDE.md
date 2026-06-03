# DogForce OWL Views — Offline Editing Guide

Reference for editing all custom Tier-1, Tier-2, and Tier-3 OWL components in the DogForce Security Suite.  
All paths are relative to the repository root.

---

## Quick-reference: component inventory

| Tier | Component | Module | JS file | XML template | Registry key |
|------|-----------|--------|---------|--------------|--------------|
| 1 | `ReliabilityGauge` | `security_base` | `static/src/js/reliability_gauge.js` | `static/src/xml/reliability_gauge.xml` | `fields/"reliability_gauge"` |
| 2 | `PayslipPreviewDialog` + `PayslipPreviewAction` | `security_payroll_core` | `static/src/js/payslip_preview.js` | `static/src/xml/payslip_preview.xml` | `actions/"security_payroll_core.payslip_preview"` |
| 3 | `AttendancePostingConsole` | `security_attendance` | `static/src/js/posting_console.js` | `static/src/xml/posting_console.xml` | `actions/"security_attendance.posting_console"` |
| 3 | `RosterBoard` | `security_shift_planner` | `static/src/js/roster_board.js` | `static/src/xml/roster_board.xml` | `actions/"security_shift_planner.roster_board"` |
| 3 | `PayrollCommandCenter` | `security_payroll_core` | `static/src/js/payroll_command_center.js` | `static/src/xml/payroll_command_center.xml` | `actions/"security_payroll_core.payroll_command_center"` |
| 3 | `ExecutiveDashboard` | `security_reporting` | `static/src/js/executive_dashboard.js` | `static/src/xml/executive_dashboard.xml` | `actions/"security_reporting.executive_dashboard"` |
| 3 | `AIAdminDashboard` | `security_ai_engine` | `static/src/js/ai_admin_config.js` | `static/src/xml/ai_admin_config.xml` | `actions/"security_ai_engine.ai_admin"` |

**Tier definitions:**
- **Tier 1** — Field widget rendered inside an existing Odoo form view
- **Tier 2** — Dialog or panel mounted over the current view (no page-level navigation change)
- **Tier 3** — Full-screen client action that replaces the entire view area (`ir.actions.client`)

---

## The two-file rule

Every component is split across exactly two files that must stay in sync:

```
static/src/js/<name>.js      ← component class, state, methods, service wiring
static/src/xml/<name>.xml    ← QWeb/OWL template (markup + bindings)
```

The JS file declares `static template = "module.ComponentName"`.  
The XML file declares `<t t-name="module.ComponentName">`.  
These two strings **must match exactly** — a mismatch silently renders nothing.

---

## Edit–reload cycle

### Template-only changes (markup, labels, colours, layout)

No module update required. Just clear the asset cache and hard-refresh:

```bash
# 1. Stop Odoo
docker stop dogforce-odoo-dev-odoo

# 2. Delete cached bundle files from the database
docker exec dogforce-odoo-dev-db psql -U odoo -d odoo-security \
  -c "DELETE FROM ir_attachment WHERE name LIKE '/web/assets/%' OR url LIKE '/web/assets/%';"

# 3. Start Odoo
docker start dogforce-odoo-dev-odoo

# 4. Hard-refresh browser (Cmd+Shift+R on macOS)
```

### Logic changes (JS state, methods, computed getters)

Same as above — asset cache clear + hard refresh.  
You do **not** need to run `-u <module>` for static asset changes.

### Model-side changes (new fields, new actions, new views XML in `views/`)

Run a module update first, then clear assets and restart:

```bash
docker stop dogforce-odoo-dev-odoo

docker run --rm \
  --network dogforce-odoo-dev_default \
  -v "$(pwd)/.local/odoo.conf:/etc/odoo/odoo.conf:ro" \
  -v "$(pwd)/custom_addons:/mnt/extra-addons" \
  -v "$(pwd)/.local/odoo:/var/lib/odoo" \
  -e HOST=db -e USER=odoo -e PASSWORD=odoo \
  odoo:19.0 odoo \
  -c /etc/odoo/odoo.conf \
  -d odoo-security \
  -u <module_name> \
  --no-http --stop-after-init

docker exec dogforce-odoo-dev-db psql -U odoo -d odoo-security \
  -c "DELETE FROM ir_attachment WHERE name LIKE '/web/assets/%' OR url LIKE '/web/assets/%';"

docker start dogforce-odoo-dev-odoo
```

---

## Rules and pitfalls — learned from this codebase

### 1. Always use `this.method()` in template event handlers

**Wrong** — `this` is `undefined` inside a free arrow function in OWL 2 strict mode:
```xml
<button t-on-click="() => setTab('overview')">
```

**Correct** — explicit `this`:
```xml
<button t-on-click="() => this.setTab('overview')">
```

This applies to every method call in `t-on-click`, `t-on-change`, `t-on-input`, etc.  
Direct method references without arguments are fine without parens:
```xml
<button t-on-click="refreshData">   <!-- calls this.refreshData(event) -->
```

### 2. Escape `<` and `>` inside attribute values

XML attribute values cannot contain raw `<` or `>`. These appear in ORM domain filters:

**Wrong:**
```xml
t-on-click="() => this.openList([['due_date','<', today]])"
```

**Correct:**
```xml
t-on-click="() => this.openList([['due_date','&lt;', today]])"
```

Always replace `<` → `&lt;` and `>` → `&gt;` inside any XML attribute value.

### 3. No duplicate attributes on the same element

**Wrong** — two `style` attributes on one element:
```xml
<div class="card" style="min-width:80px;"
     t-on-click="..."
     style="cursor:pointer; min-width:80px;">
```

**Correct** — merge into one:
```xml
<div class="card"
     t-on-click="..."
     style="cursor:pointer; min-width:80px;">
```

The XML parser silently uses the last value but Odoo's validator throws.

### 4. `t-att-class` vs `class` — never mix them on the same element

If you need dynamic classes, use only `t-att-class`:
```xml
<!-- Wrong: mixing static class and t-att-class -->
<div class="nav-link" t-att-class="isActive ? 'active' : ''">

<!-- Correct: put everything in t-att-class -->
<div t-att-class="'nav-link' + (isActive ? ' active' : '')">
```

### 5. `<group expand="0">` is invalid in Odoo 19 search views

Odoo 19 removed the `expand` attribute from `<group>` in `<search>` view XML (not OWL — this applies to server-side view XML in `views/`). Replace with flat `<filter>` elements:

**Wrong:**
```xml
<group expand="0" string="Group By">
    <filter string="By Feature" context="{'group_by': 'feature'}"/>
</group>
```

**Correct:**
```xml
<filter string="By Feature" name="group_feature" context="{'group_by': 'feature'}"/>
```

### 6. Validate XML before saving

Run this before any Docker operations to catch errors immediately:

```bash
python3 -c "
import xml.etree.ElementTree as ET, sys
f = 'custom_addons/<module>/static/src/xml/<name>.xml'
try:
    ET.parse(f); print('OK')
except ET.ParseError as e:
    print('ERROR:', e); sys.exit(1)
"
```

### 7. `env.company` not `doc.company_id` in QWeb PDF reports

Custom models that don't extend `mail.thread` or `account.move` don't have a `company_id` field. In QWeb report templates, always use:

```xml
<t t-esc="env.company.name"/>
<t t-esc="env.company.vat or 'N/A'"/>
```

Not `doc.company_id.name` or `period.company_id.name`.

### 8. `useState` must be assigned in `setup()`, not a constructor

```js
// Correct
setup() {
    this.state = useState({ loading: true, tab: "overview" });
}

// Wrong — component lifecycle won't track it
constructor() {
    super(...arguments);
    this.state = useState({ ... }); // don't do this
}
```

### 9. `password=True` is not a valid field parameter in Odoo 19

Use `widget="password"` in the view XML instead of `password=True` on the field definition. Odoo 19 logs a warning and ignores it.

---

## Per-component reference

---

### `ReliabilityGauge` — Tier 1 field widget

**Module:** `security_base`  
**JS:** `custom_addons/security_base/static/src/js/reliability_gauge.js`  
**XML:** `custom_addons/security_base/static/src/xml/reliability_gauge.xml`  
**Template name:** `security_base.ReliabilityGauge`  
**Registry:** `fields/"reliability_gauge"`

**What it does:** SVG circular gauge that renders an integer field (0–100). Green ≥ 80, amber 60–79, red < 60. Used on `hr.employee` for `security_reliability_score`.

**Key computed properties:**
```js
get score()       // raw integer from this.props.record.data[this.props.name]
get color()       // "#28a745" | "#ffc107" | "#dc3545"
get dashoffset()  // SVG stroke-dashoffset for arc length
get circumference() // 2 * π * r (r = 45)
```

**To change the colour thresholds:**
Edit the `get color()` getter in `reliability_gauge.js` — change the `>= 80` and `>= 60` boundaries.

**To change the gauge size:**
Edit the `viewBox`, `cx`, `cy`, `r` attributes in `reliability_gauge.xml` and update `get circumference()` accordingly.

**Used in view:** `security_base/views/hr_employee_views.xml` — Reliability tab, `widget="reliability_gauge"` on `security_reliability_score`.

---

### `PayslipPreviewDialog` + `PayslipPreviewAction` — Tier 2 dialog

**Module:** `security_payroll_core`  
**JS:** `custom_addons/security_payroll_core/static/src/js/payslip_preview.js`  
**XML:** `custom_addons/security_payroll_core/static/src/xml/payslip_preview.xml`  
**Template names:** `security_payroll_core.PayslipPreviewDialog`, `security_payroll_core.PayslipPreviewAction`  
**Registry:** `actions/"security_payroll_core.payslip_preview"`, `dialogs/"PayslipPreviewDialog"`

**What it does:** Opens a modal dialog containing an iframe that loads the payslip QWeb PDF at `/report/html/security_payroll_core.report_security_payslip/{id}`.

**Props:**
```js
static props = {
    payslipId: Number,   // record ID passed from action context
    close: Function,     // injected by DialogService
}
```

**To change the dialog size:** Edit `style` on the `<div class="modal-dialog">` wrapper in `payslip_preview.xml`. Default is `max-width: 900px`.

**To load a different report:** Change the iframe `src` in `payslip_preview.xml`:
```xml
<iframe t-att-src="'/report/html/security_payroll_core.report_security_payslip/' + props.payslipId"/>
```

**Triggered by:** `action_preview_payslip()` on `SecurityPayslip` model in `security_payroll_core.py`.

---

### `AttendancePostingConsole` — Tier 3 client action

**Module:** `security_attendance`  
**JS:** `custom_addons/security_attendance/static/src/js/posting_console.js`  
**XML:** `custom_addons/security_attendance/static/src/xml/posting_console.xml`  
**Template name:** `security_attendance.PostingConsole`  
**Registry:** `actions/"security_attendance.posting_console"`  
**Menu:** Operations → Attendance → Posting Console

**What it does:** Spreadsheet-style bulk attendance marking grid. Supervisor selects date + site, loads or creates an attendance batch, edits presence/times inline for all guards, submits in one click.

**State shape:**
```js
{
    loading: bool,
    sites: [],           // [{id, name}] for filter dropdown
    batches: [],         // loaded roster batches
    selectedDate: str,   // "YYYY-MM-DD"
    selectedSiteId: int | null,
    batchId: int | null,
    records: [],         // attendance record rows
    dirtyRecords: Set,   // record IDs with unsaved changes
    saving: bool,
}
```

**Key methods:**
- `loadBatch()` — search for an existing `security.attendance.batch` matching date + site
- `createBatch()` — create new batch and generate records from roster
- `saveAll()` — calls `action_bulk_mark_attendance` on the batch model with dirty records
- `markRow(recordId, presence)` — set `manual_presence` on a row

**To add a new column to the grid** (e.g. a notes field):
1. Add the field to the `records` state in `loadBatch()` (include it in `orm.searchRead` fields list)
2. Add a `<td>` column in the grid header and body rows in `posting_console.xml`
3. Include the field in the dirty record payload in `saveAll()`

---

### `RosterBoard` — Tier 3 client action

**Module:** `security_shift_planner`  
**JS:** `custom_addons/security_shift_planner/static/src/js/roster_board.js`  
**XML:** `custom_addons/security_shift_planner/static/src/xml/roster_board.xml`  
**Template name:** `security_shift_planner.RosterBoard`  
**Registry:** `actions/"security_shift_planner.roster_board"`  
**Menu:** Operations → Roster Board (sequence 42)

**What it does:** Visual grid of roster slots by site × date. Right-side Guard Pool Sidebar shows AI-scored suggestions for selected unassigned slot. Assign/unassign guards with one click.

**State shape:**
```js
{
    loading: bool,
    batches: [],          // recent roster batches
    batchId: int | null,
    sites: [],
    posts: [],
    slots: [],            // all slots for selected batch
    filterSiteId: int | null,
    selectedSlot: obj | null,
    suggestions: [],      // scored guard suggestions for selected slot
}
```

**Key methods:**
- `loadBatch(batchId)` — load sites, posts, slots for the batch
- `loadSuggestions(slotId)` — calls `action_suggest_guards` on the slot model (Python scoring engine)
- `assignGuard(slotId, employeeId)` — writes `employee_id` directly via ORM
- `unassignSlot(slotId)` — clears `employee_id`

**To change the grid layout** (e.g. group by date instead of site):
Swap the outer/inner loops in `roster_board.xml` — the current structure is `site → post → slot`. To flip to `date → site → slot`, restructure the `t-foreach` loops.

**To add a new scoring factor:**
Edit `_score_guard()` in `security_shift_planner/models/security_shift_planner.py`. Return a modified `score` float. The `score_breakdown` field stores the explanation string shown in the sidebar.

---

### `PayrollCommandCenter` — Tier 3 client action

**Module:** `security_payroll_core`  
**JS:** `custom_addons/security_payroll_core/static/src/js/payroll_command_center.js`  
**XML:** `custom_addons/security_payroll_core/static/src/xml/payroll_command_center.xml`  
**Template name:** `security_payroll_core.PayrollCommandCenter`  
**Registry:** `actions/"security_payroll_core.payroll_command_center"`  
**Menu:** Operations → Payroll Command Center (sequence 85)

**What it does:** Left sidebar period selector + main area with stats bar, payslip register table, and anomaly tab. Bulk confirm/pay actions. Clicking any row opens the payslip form.

**State shape:**
```js
{
    loading: bool,
    periods: [],               // last 6 security.payroll.period records
    selectedPeriodId: int | null,
    payslips: [],              // payslips for selected period
    stats: {
        total, draft, confirmed, paid,
        anomalyCount, totalGross, totalNet, totalDeductions
    },
    activeTab: "overview" | "payslips" | "anomalies",
}
```

**Key computed getters:**
```js
get selectedPeriod()     // period object from state.periods
get anomalyPayslips()    // payslips where anomaly_score > 0
get draftPayslips()
get confirmedPayslips()
get paidPayslips()
```

**To add a new tab:**
1. Add `"newtab"` as a valid value in the `activeTab` state
2. Add a `<li>` tab button in `payroll_command_center.xml` calling `() => this.setTab('newtab')`
3. Add a `<t t-if="state.activeTab === 'newtab'">` block with the tab content

**To add a new bulk action:**
1. Add a method in `payroll_command_center.js`:
   ```js
   async bulkNewAction() {
       const ids = this.draftPayslips.map(p => p.id);
       await this.orm.call("security.payslip", "your_action_method", [ids]);
       await this._loadPayslips(this.state.selectedPeriodId);
   }
   ```
2. Add a button in the Overview tab in `payroll_command_center.xml`:
   ```xml
   <button class="btn btn-outline-primary btn-sm" t-on-click="bulkNewAction">
       New Action
   </button>
   ```

---

### `ExecutiveDashboard` — Tier 3 client action

**Module:** `security_reporting`  
**JS:** `custom_addons/security_reporting/static/src/js/executive_dashboard.js`  
**XML:** `custom_addons/security_reporting/static/src/xml/executive_dashboard.xml`  
**Template name:** `security_reporting.ExecutiveDashboard`  
**Registry:** `actions/"security_reporting.executive_dashboard"`  
**Menu:** Reporting → Executive Dashboard (sequence 1, requires `hr.group_hr_manager`)

**What it does:** Live KPI dashboard with 8 metric cards, colour-coded alert feed, and tabbed detail views (Overview, Attendance, Billing). All KPIs loaded via ORM on mount; refresh button reloads.

**State shape:**
```js
{
    loading: bool,
    kpis: {
        activeGuards, todayPresent, todayAbsent, todayAwol,
        unassignedSlots, pendingInvoices, overdueInvoices,
        totalRevenueMtd, openIncidents, expiringDocuments,
    },
    recentAlerts: [],    // [{type, message, record_model, record_id}]
    activeTab: "overview" | "attendance" | "billing",
    lastUpdated: Date | null,
}
```

**To add a new KPI card:**
1. Add the field to `state.kpis` in `setup()`
2. Load it in `_loadData()` using `this.orm.searchCount(...)` or `this.orm.searchRead(...)`
3. Add a `<div class="col-...">` KPI card block in `executive_dashboard.xml` inside the KPI cards row
4. Optionally add an alert rule in `_buildAlerts()`

**To add a new tab:**
1. Extend `activeTab` in state with a new string value
2. Add a `<li class="nav-item">` button calling `() => this.setTab('newtab')`
3. Add a `<t t-if="state.activeTab === 'newtab'">` content block

**Alert severity colours:** `danger` → red (`#dc3545`), `warning` → amber, `info` → blue. Controlled by `t-att-class` on alert badges in the template.

---

### `AIAdminDashboard` — Tier 3 client action

**Module:** `security_ai_engine`  
**JS:** `custom_addons/security_ai_engine/static/src/js/ai_admin_config.js`  
**XML:** `custom_addons/security_ai_engine/static/src/xml/ai_admin_config.xml`  
**Template name:** `security_ai_engine.AIAdminDashboard`  
**Registry:** `actions/"security_ai_engine.ai_admin"`  
**Menu:** Operations → AI Engine → AI Dashboard (sequence 10)

**What it does:** Provider status, feature toggle overview, usage stats (total/success/error calls, success rate), and a recent call log table. Connection test button fires the Python `action_test_connection` method.

**State shape:**
```js
{
    loading: bool,
    config: obj | null,     // security.ai.config record
    logs: [],               // last 50 security.ai.log records
    stats: { total, success, error },
    testingConnection: bool,
    activeTab: "overview" | "logs",
}
```

**To add a new feature toggle display:**
In `ai_admin_config.js`, extend the `get featureList()` getter:
```js
get featureList() {
    return [
        // ... existing entries ...
        { key: "feature_new_thing", label: "New AI Feature",
          enabled: this.state.config.feature_new_thing },
    ];
}
```
No template change needed — the `t-foreach="featureList"` loop picks it up automatically.

**To add a new tab:** Same pattern as `PayrollCommandCenter` above.

---

## Manifest wiring checklist

When adding a **new** OWL component to an existing module, verify all four wiring points:

```python
# __manifest__.py
"depends": [..., "web"],          # 1. "web" must be in depends

"assets": {
    "web.assets_backend": [
        "module_name/static/src/js/component.js",    # 2. JS file
        "module_name/static/src/xml/component.xml",  # 3. XML template
    ],
},

"data": [
    "views/client_action.xml",    # 4. ir.actions.client record
],
```

The `ir.actions.client` record must have a `tag` that exactly matches the string passed to `registry.category("actions").add(tag, Component)`.

---

## Debugging blank screens

If the Odoo frontend shows a white/blank page after editing:

1. **Check XML validity** — run the Python `ET.parse()` check above on the changed template
2. **Check for `<` in attribute values** — search for unescaped `<` inside `t-on-click`, `t-att-*`, etc.
3. **Check for duplicate attributes** — an element with `style=` twice will fail silently in the browser but error in the validator
4. **Clear asset cache** — stale bundles from failed attempts hide real errors:
   ```bash
   docker exec dogforce-odoo-dev-db psql -U odoo -d odoo-security \
     -c "DELETE FROM ir_attachment WHERE name LIKE '/web/assets/%' OR url LIKE '/web/assets/%';"
   ```
5. **Open browser DevTools → Console** — OWL runtime errors appear here with the component name and line number
6. **Use `?debug=assets`** — append to the URL to force Odoo to recompile and surface template errors in the console

---

## Common ORM patterns used in these components

```js
// Count matching records
const n = await this.orm.searchCount("security.attendance.record", [
    ["shift_date", "=", today],
    ["status", "in", ["present", "late"]],
]);

// Read specific fields
const records = await this.orm.searchRead(
    "security.payslip",
    [["period_id", "=", periodId]],
    ["name", "employee_id", "state", "total_earnings", "net_pay"],
    { limit: 200, order: "employee_id asc" }
);

// Call a Python method
await this.orm.call("security.payslip", "action_confirm", [[...ids]]);

// Write a field value
await this.orm.write("security.roster.slot", [slotId], { employee_id: employeeId });

// Navigate to a list view
await this.action.doAction({
    type: "ir.actions.act_window",
    res_model: "security.billing.invoice",
    views: [[false, "list"], [false, "form"]],
    domain: [["state", "=", "draft"]],
});

// Navigate to a form view
await this.action.doAction({
    type: "ir.actions.act_window",
    res_model: "security.payslip",
    res_id: payslipId,
    views: [[false, "form"]],
});
```
