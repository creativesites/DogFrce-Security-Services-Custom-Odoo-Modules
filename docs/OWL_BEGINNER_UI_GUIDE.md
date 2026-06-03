# DogForce OWL UI Beginner Guide
## How to Customise the Look and Feel of Every Custom View

This guide is for someone new to Odoo and OWL. It explains everything you need to update the appearance of the DogForce custom dashboards and views while working offline. No prior OWL or frontend experience assumed.

---

## Part 1 — How the custom views work (the mental model)

Every custom view in DogForce is made of exactly **two files**:

```
static/src/js/name.js     ← the brain  (what data to load, what happens on clicks)
static/src/xml/name.xml   ← the face   (colours, layout, labels, icons, structure)
```

**To change how something looks: edit the XML file.**  
To change what data appears or what a button does: edit the JS file.  
You will mostly be editing XML.

The XML files use two technologies layered on top of each other:

| Technology | What it does | Example |
|------------|-------------|---------|
| **OWL directives** (`t-*`) | Connects live data to the template | `<t t-esc="state.kpis.activeGuards"/>` |
| **Bootstrap 5** | Controls layout, colours, spacing | `<div class="card shadow-sm p-3">` |

Think of Bootstrap as a big library of named CSS classes that make things look good without writing CSS yourself.

---

## Part 2 — The reload cycle (do this every time you make a change)

### Step 1 — Edit the file

Open the XML file in any text editor. Make your change. Save.

### Step 2 — Clear the asset cache

Odoo compiles your XML into a bundle and caches it. You must delete the cache or your changes won't appear.

Open Terminal and run:

```bash
cd "/Users/winstonzulu/Documents/GitHub/DogFrce Security Services Custom Odoo Modules"

# Delete the cached bundles from the database
docker exec dogforce-odoo-dev-db psql -U odoo -d odoo-security \
  -c "DELETE FROM ir_attachment WHERE name LIKE '/web/assets/%' OR url LIKE '/web/assets/%';"
```

### Step 3 — Hard refresh the browser

In Chrome/Safari: **Cmd + Shift + R**

That's it. Your change appears immediately. No restart needed for visual changes.

### If something breaks (blank screen / error)

Check your XML is valid first:
```bash
python3 -c "
import xml.etree.ElementTree as ET
ET.parse('custom_addons/MODULENAME/static/src/xml/FILENAME.xml')
print('XML is valid')
"
```
If it prints an error, you have a typo in the XML. Common causes: unclosed tag, raw `<` inside an attribute value, duplicate `style=` on one element.

---

## Part 3 — Bootstrap 5 colour, spacing, and layout cheat sheet

All the custom views use Bootstrap 5. Here are the classes you will use most often.

### Colours

**Text colour:**
```
text-primary    → blue
text-secondary  → grey
text-success    → green
text-danger     → red
text-warning    → yellow/amber
text-info       → cyan
text-muted      → light grey
text-dark       → near-black
text-white      → white
```

**Background colour:**
```
bg-primary   bg-secondary   bg-success   bg-danger
bg-warning   bg-info        bg-light     bg-dark
bg-white     bg-transparent
```

**Border colours (for `.card` and other bordered elements):**
```
border-primary   border-success   border-danger   border-warning
border-0   ← removes all borders
```

**Example — change a card's number from blue to green:**
```xml
<!-- Before -->
<div class="display-6 fw-bold text-primary">

<!-- After -->
<div class="display-6 fw-bold text-success">
```

### Text size and weight

```
display-1 display-2 display-3 display-4 display-5 display-6  ← large headings (1=biggest)
h1 h2 h3 h4 h5 h6                                            ← heading sizes
fs-1 fs-2 fs-3 fs-4 fs-5 fs-6                                ← font sizes (1=biggest)
small                                                          ← smaller text
fw-bold      ← bold
fw-semibold  ← semi-bold
fw-normal    ← normal weight
text-uppercase text-capitalize text-lowercase
```

### Spacing

Bootstrap uses a 0–5 scale. `m` = margin, `p` = padding. Direction: `t`op, `b`ottom, `s`tart(left), `e`nd(right), `x`(left+right), `y`(top+bottom).

```
p-0  p-1  p-2  p-3  p-4  p-5   ← padding all sides
px-3                             ← padding left and right = 3
py-2                             ← padding top and bottom = 2
mt-3                             ← margin top = 3
mb-4                             ← margin bottom = 4
me-1                             ← margin right = 1 (used after icons)
ms-2                             ← margin left = 2
```

**Example — add more padding inside a card:**
```xml
<!-- Before: less padding -->
<div class="card p-2">

<!-- After: more padding -->
<div class="card p-4">
```

### Borders and shadows

```
border           ← thin grey border all around
border-top       ← only top border
rounded          ← rounded corners
rounded-3        ← more rounded
rounded-circle   ← circle (for avatar images)
shadow-sm        ← subtle shadow (used on cards)
shadow           ← medium shadow
shadow-lg        ← large shadow
border-0         ← no border
```

### Layout (flexbox)

These make elements sit side-by-side or stack:

```
d-flex              ← turn on flex layout
flex-column         ← stack children vertically
align-items-center  ← center children vertically
justify-content-between  ← push children to opposite ends
justify-content-center   ← center children horizontally
gap-2  gap-3  gap-4      ← space between children (2/3/4 units)
flex-fill               ← take up remaining space
flex-wrap               ← wrap to next line when too wide
```

**Example — put two things side by side with space between them:**
```xml
<div class="d-flex align-items-center justify-content-between">
    <span>Left side</span>
    <span>Right side</span>
</div>
```

### Grid columns

Bootstrap's 12-column grid. `col-N` takes N of 12 columns.

```
col        ← auto width
col-6      ← half width
col-4      ← one third
col-3      ← one quarter
col-12     ← full width
col-md-4   ← one third on medium screens, full width on small
```

### Badges

Small coloured labels. Very useful for status indicators:

```xml
<span class="badge bg-success">Active</span>
<span class="badge bg-danger">AWOL</span>
<span class="badge bg-warning text-dark">Pending</span>
<span class="badge bg-secondary">Draft</span>
<span class="badge rounded-pill bg-primary">42</span>
```

### Tables

```
table              ← base table styles
table-hover        ← row highlights on hover
table-striped      ← alternating row colours
table-sm           ← tighter row height
table-bordered     ← borders on all cells
table-light        ← light grey header/footer
thead class="table-dark"   ← dark header
```

---

## Part 4 — Font Awesome icons

All icons in the custom views use Font Awesome 4. The pattern is always:
```xml
<i class="fa fa-ICONNAME"/>
```

Common icons used in the views:

| Icon class | Looks like |
|------------|-----------|
| `fa-shield` | Shield (used for guard/security) |
| `fa-users` | Group of people |
| `fa-user` | Single person |
| `fa-user-times` | Person with X (AWOL) |
| `fa-check-circle` | Green tick circle |
| `fa-exclamation-circle` | ! in circle (alert) |
| `fa-exclamation-triangle` | ! in triangle (warning) |
| `fa-calendar` | Calendar |
| `fa-file-text-o` | Document |
| `fa-money` | Banknote |
| `fa-refresh` | Circular arrows (reload) |
| `fa-cog` | Gear / settings |
| `fa-list` | Lines (list view) |
| `fa-plug` | Plug (connection) |
| `fa-external-link` | Arrow leaving box |
| `fa-plus` | Plus sign |
| `fa-times` | X (close/remove) |
| `fa-search` | Magnifying glass |
| `fa-info-circle` | i in circle |
| `fa-clock-o` | Clock |
| `fa-bar-chart` | Bar chart |

**Size modifiers:**
```xml
<i class="fa fa-shield"/>          ← normal size
<i class="fa fa-shield fa-lg"/>    ← large
<i class="fa fa-shield fa-2x"/>    ← 2× size
<i class="fa fa-shield fa-3x"/>    ← 3× size
<i class="fa fa-refresh fa-spin"/> ← spinning (loading)
```

**Adding space after an icon** (before text):
```xml
<i class="fa fa-shield me-2"/> Security
```

Search the full icon list at: https://fontawesome.com/v4/icons/

---

## Part 5 — OWL directives you'll encounter

You don't need to write new OWL logic — just understand what's already there.

### Displaying data

```xml
<t t-esc="state.kpis.activeGuards"/>
```
Outputs the value of `state.kpis.activeGuards` as plain text. Never remove the `t-esc` wrapper.

### Conditional visibility

```xml
<t t-if="state.kpis.overdueInvoices > 0">
    <div class="alert alert-danger">Overdue invoices!</div>
</t>
<t t-else="">
    <div>All invoices paid.</div>
</t>
```

### Looping

```xml
<t t-foreach="state.recentAlerts" t-as="alert" t-key="alert.id">
    <div><t t-esc="alert.message"/></div>
</t>
```

### Dynamic class (switching class based on data)

```xml
<!-- Single condition -->
<div t-att-class="isActive ? 'text-success' : 'text-muted'">

<!-- Building a class string (note the quote inside quote) -->
<div t-att-class="'nav-link' + (state.activeTab === 'overview' ? ' active' : '')">
```

### Dynamic style

```xml
<div t-att-style="'background-color:' + myColor + ';'">
```

### Click handlers

```xml
<!-- Calls this.setTab('overview') on click -->
<button t-on-click="() => this.setTab('overview')">Overview</button>

<!-- Calls this.refreshData on click (no arguments) -->
<button t-on-click="refreshData">Refresh</button>
```

**Important rule:** Inside arrow functions in templates, always write `this.methodName()` not just `methodName()`.

---

## Part 6 — Component-by-component customisation guide

---

### Component 1: Executive Dashboard
**File:** `custom_addons/security_reporting/static/src/xml/executive_dashboard.xml`

**Structure at a glance:**
```
Header bar (title + refresh button)
  └── KPI Cards row (8 cards: Guards, Present, AWOL, Slots, Invoices×2, Revenue, Incidents)
        └── Tab bar (Overview | Attendance | Billing)
              ├── Overview tab (Alert Feed + Quick Actions)
              ├── Attendance tab (stats table)
              └── Billing tab (invoice summary)
```

**Changing a KPI card colour:**

Find the card (they are labelled with comments like `<!-- Active Guards -->`):
```xml
<!-- Before: blue number -->
<div class="display-6 fw-bold text-primary">

<!-- After: dark teal -->
<div class="display-6 fw-bold" style="color:#0d6e6e;">
```

**Making a card bigger:**
```xml
<!-- Before -->
<div class="card h-100 border-0 shadow-sm text-center p-3 o_kpi_card">

<!-- After: more padding, slightly larger -->
<div class="card h-100 border-0 shadow p-4 o_kpi_card">
```

**Adding a coloured left border to any card** (draws attention):
```xml
<div class="card h-100 border-0 shadow-sm text-center p-3"
     style="border-left: 4px solid #198754 !important;">
```

**Changing the header bar background:**
```xml
<!-- Before -->
<div class="o_dashboard_header d-flex ... bg-white border-bottom shadow-sm">

<!-- After: dark header -->
<div class="o_dashboard_header d-flex ... bg-dark border-bottom shadow-sm">
    <!-- Also change text colour below -->
    <h4 class="mb-0 fw-bold text-white">Executive Dashboard</h4>
    <small class="text-white-50">Security Operations Overview</small>
```

**Changing an alert feed badge colour:**

Find the alert item in the template (inside `t-foreach="state.recentAlerts"`):
```xml
<!-- Before: type-driven colour -->
<span t-att-class="'badge rounded-pill me-2 ' + (alert.type === 'danger' ? 'bg-danger' : alert.type === 'warning' ? 'bg-warning text-dark' : 'bg-info text-dark')">

<!-- After: all badges use the same style -->
<span class="badge rounded-pill me-2 bg-primary">
```

---

### Component 2: Payroll Command Center
**File:** `custom_addons/security_payroll_core/static/src/xml/payroll_command_center.xml`

**Structure at a glance:**
```
Left sidebar (period list — 220px)
  └── Main area
        ├── Header (period name + Open Period button)
        ├── Stats bar (Total | Draft | Confirmed | Paid | Anomalies | Net Pay)
        ├── Tab bar (Overview | Payslips | Anomalies)
        ├── Overview tab (Financial Summary + Bulk Actions + Status table)
        ├── Payslips tab (full table with all payslips)
        └── Anomalies tab (only flagged payslips)
```

**Changing the sidebar background colour:**
```xml
<!-- Before: white -->
<div class="o_pcc_sidebar d-flex flex-column bg-white border-end"

<!-- After: dark sidebar -->
<div class="o_pcc_sidebar d-flex flex-column border-end"
     style="width:220px; min-width:220px; overflow-y:auto; background:#1e2a3a;">
```
If you do this, also change the text colours inside sidebar items from `text-dark` to `text-white`.

**Changing selected period highlight colour:**
```xml
<!-- The selected period gets bg-primary. Change to another colour: -->
t-att-class="'o_period_item p-3 border-bottom d-flex flex-column gap-1 ' + 
    (state.selectedPeriodId === period.id ? 'text-white' : 'text-dark')"
t-att-style="state.selectedPeriodId === period.id ? 'background:#0d6e6e; cursor:pointer;' : 'cursor:pointer;'"
```

**Making the stats bar cards stand out more:**
```xml
<!-- Before -->
<div class="card border-0 shadow-sm text-center px-3 py-2 flex-fill" style="min-width:80px;">

<!-- After: add colour accent -->
<div class="card border-0 shadow text-center px-3 py-2 flex-fill"
     style="min-width:80px; border-top: 3px solid #0d6e6e !important;">
```

**Highlighting anomaly rows in the payslip table:**
The anomaly rows already use amber. To change to red:
```xml
<!-- Find the payslip table row, look for t-att-style with anomaly_score -->
t-att-style="ps.anomaly_score > 0 ? 'background-color:#fff0f0;' : ''"
```

---

### Component 3: Attendance Posting Console
**File:** `custom_addons/security_attendance/static/src/xml/posting_console.xml`

**Structure at a glance:**
```
Header (title + batch info)
  └── Filter bar (date picker + site selector + action buttons)
        └── Attendance grid (one row per guard)
              └── Status bar (saved/unsaved count)
```

**Changing status indicator colours in the grid:**

Find the rows that show status badges (look for `manual_presence` or `status` references). Each row colour is set via `t-att-class` or `t-att-style`. Example:
```xml
<!-- Change present rows from green to teal -->
t-att-class="'table-row ' + (row.manual_presence === 'present' ? 'table-success' : 
              row.manual_presence === 'absent' ? 'table-danger' : 
              row.manual_presence === 'awol' ? 'table-warning' : '')"
```

**Making the header bar more prominent:**
```xml
<!-- Find the header div -->
<div class="o_posting_console_header ... bg-white border-bottom">

<!-- Change to branded dark header -->
<div class="o_posting_console_header ... border-bottom"
     style="background: linear-gradient(135deg, #1a3a5c 0%, #0d6e6e 100%);">
```

---

### Component 4: Roster Board
**File:** `custom_addons/security_shift_planner/static/src/xml/roster_board.xml`

**Structure at a glance:**
```
Left panel (batch + filter selectors)
  └── Main grid (site × date matrix)
        └── Right sidebar (guard pool + suggestions)
```

**Changing slot cell colours by state:**

Find the slot card cells — they use state-based classes. Example change:
```xml
<!-- Find t-att-class on slot cells -->
t-att-class="'o_slot_cell rounded p-2 mb-1 ' + 
    (slot.employee_id ? 'bg-success bg-opacity-10 border border-success' : 
                        'bg-warning bg-opacity-10 border border-warning')"
```

**Making the guard suggestion cards more visual:**
```xml
<!-- Find suggestion list items -->
<div class="suggestion-item d-flex justify-content-between align-items-center p-2 mb-1 rounded border">

<!-- Add hover effect and score bar -->
<div class="suggestion-item d-flex justify-content-between align-items-center p-2 mb-1 rounded border shadow-sm"
     style="cursor:pointer; transition: all 0.15s;">
```

---

### Component 5: AI Engine Dashboard
**File:** `custom_addons/security_ai_engine/static/src/xml/ai_admin_config.xml`

**Changing the stats cards:**
```xml
<!-- Make total calls card dark blue -->
<div class="card flex-fill text-center p-3" style="min-width:140px; background:#1a3a5c; color:white;">
    <div class="h1 m-0" style="color:#60cdff;">
        <t t-esc="state.stats.total"/>
    </div>
    <div class="small" style="color:rgba(255,255,255,0.7);">Total API Calls</div>
</div>
```

**Changing feature toggle badge colours:**
```xml
<!-- Find the feat.enabled conditional badge -->
<span t-att-class="feat.enabled ? 'badge bg-success' : 'badge bg-secondary'">

<!-- Change OFF colour from grey to red -->
<span t-att-class="feat.enabled ? 'badge bg-success' : 'badge bg-danger'">
```

---

### Component 6: Payslip Preview Dialog
**File:** `custom_addons/security_payroll_core/static/src/xml/payslip_preview.xml`

**Changing dialog size:**
```xml
<!-- Find the modal-dialog div -->
<div class="modal-dialog modal-xl" style="max-width:900px; width:95vw;">

<!-- Make it even wider -->
<div class="modal-dialog" style="max-width:1100px; width:98vw;">
```

**Changing dialog header:**
```xml
<div class="modal-header bg-primary text-white">
    <h5 class="modal-title">
        <i class="fa fa-file-text-o me-2"/> Payslip Preview
    </h5>
```

---

### Component 7: Reliability Gauge (field widget)
**File:** `custom_addons/security_base/static/src/xml/reliability_gauge.xml`

This is an SVG circle gauge. The colour thresholds are in the JS file, not the XML.

**To change colour thresholds** — edit `reliability_gauge.js`:
```js
// Find get color()
get color() {
    if (this.score >= 80) return "#198754";  // green — change threshold here
    if (this.score >= 60) return "#ffc107";  // amber — change threshold here
    return "#dc3545";                         // red
}
```

**To change the gauge size** — edit `reliability_gauge.xml`:
```xml
<!-- Find the SVG — increase width/height and the r (radius) attribute -->
<svg width="120" height="120" viewBox="0 0 120 120">
    <!-- track circle — cx/cy = centre, r = radius -->
    <circle cx="60" cy="60" r="50" .../>
    <!-- progress arc — same cx/cy/r -->
    <circle cx="60" cy="60" r="50" .../>
```
If you change `r`, also update `get circumference()` in the JS: `return 2 * Math.PI * r`.

**To add a label below the score** — edit `reliability_gauge.xml`:
```xml
<!-- Find the text elements inside the SVG and add: -->
<text x="60" y="75" text-anchor="middle" font-size="10" fill="#666">
    Reliability
</text>
```

---

## Part 7 — Custom CSS for advanced styling

For changes too complex for Bootstrap classes alone, add a custom CSS file.

### Step 1 — Create the file

Create: `custom_addons/security_reporting/static/src/css/dashboard.css`

```css
/* DogForce dashboard custom styles */

.o_executive_dashboard .o_kpi_card {
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.o_executive_dashboard .o_kpi_card:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0,0,0,0.12) !important;
}

/* Custom gradient header */
.o_dashboard_header {
    background: linear-gradient(135deg, #1a3a5c 0%, #2d6a9f 100%) !important;
}

.o_dashboard_header h4,
.o_dashboard_header small,
.o_dashboard_header span {
    color: rgba(255,255,255,0.9) !important;
}
```

### Step 2 — Register it in the manifest

In `custom_addons/security_reporting/__manifest__.py`:

```python
"assets": {
    "web.assets_backend": [
        "security_reporting/static/src/css/dashboard.css",  # ← add this line
        "security_reporting/static/src/js/executive_dashboard.js",
        "security_reporting/static/src/xml/executive_dashboard.xml",
    ],
},
```

### Step 3 — Update the module, then clear cache

```bash
cd "/Users/winstonzulu/Documents/GitHub/DogFrce Security Services Custom Odoo Modules"

docker stop dogforce-odoo-dev-odoo

docker run --rm \
  --network dogforce-odoo-dev_default \
  -v "$(pwd)/.local/odoo.conf:/etc/odoo/odoo.conf:ro" \
  -v "$(pwd)/custom_addons:/mnt/extra-addons" \
  -v "$(pwd)/.local/odoo:/var/lib/odoo" \
  -e HOST=db -e USER=odoo -e PASSWORD=odoo \
  odoo:19.0 odoo -c /etc/odoo/odoo.conf -d odoo-security \
  -u security_reporting --no-http --stop-after-init

docker exec dogforce-odoo-dev-db psql -U odoo -d odoo-security \
  -c "DELETE FROM ir_attachment WHERE name LIKE '/web/assets/%' OR url LIKE '/web/assets/%';"

docker start dogforce-odoo-dev-odoo
```

A module update (`-u`) is only needed when you add a NEW file to the manifest. For changes to an existing CSS/JS/XML file that's already listed in the manifest, just clear the asset cache and hard-refresh.

---

## Part 8 — Quick recipes

### Make any card clickable and highlighted on hover

```xml
<div class="card shadow-sm p-3"
     style="cursor:pointer; transition: box-shadow 0.15s;"
     onmouseover="this.style.boxShadow='0 4px 16px rgba(0,0,0,0.15)'"
     onmouseout="this.style.boxShadow=''">
```

### Add a gradient background to a header

```xml
<div class="p-4 rounded-3 mb-4"
     style="background: linear-gradient(135deg, #1a3a5c 0%, #0d6e6e 100%); color:white;">
    <h3 class="mb-0 text-white">Section Title</h3>
</div>
```

### Show a coloured progress bar

```xml
<!-- value must be 0–100 -->
<div class="progress" style="height:8px;">
    <div class="progress-bar bg-success"
         t-att-style="'width:' + attendancePercent + '%'"/>
</div>
```

### Add a divider line between sections

```xml
<hr class="my-3 border-secondary opacity-25"/>
```

### Create a stat row with icon + number + label

```xml
<div class="d-flex align-items-center gap-3 p-3 border-bottom">
    <div class="rounded-circle d-flex align-items-center justify-content-center bg-primary bg-opacity-10"
         style="width:48px; height:48px;">
        <i class="fa fa-users fa-lg text-primary"/>
    </div>
    <div>
        <div class="fw-bold fs-4"><t t-esc="state.kpis.activeGuards"/></div>
        <div class="text-muted small">Active Guards on Duty</div>
    </div>
</div>
```

### Style a status badge by value

```xml
<!-- In a t-foreach loop where row.status is 'present', 'absent', or 'awol' -->
<span t-att-class="'badge ' + 
    (row.status === 'present' ? 'bg-success' :
     row.status === 'absent'  ? 'bg-secondary' :
     row.status === 'awol'    ? 'bg-danger' : 'bg-light text-dark')">
    <t t-esc="row.status"/>
</span>
```

---

## Part 9 — Things NOT to change

| What | Why |
|------|-----|
| The `t-name` attribute in XML | Breaks the link between JS and template |
| The `static template = "..."` line in JS | Same — must match `t-name` exactly |
| The `registry.category("actions").add(...)` line | Breaks the menu action |
| Any `t-esc` expressions | These output live data — removing them loses the data |
| The `t-on-click="() => this.methodName(...)"` pattern | Changing to `methodName()` without `this.` causes errors |
| The `models/` Python files | Those are the database models — separate from the UI |

---

## Part 10 — Starting Docker when it's shut down

If you come back and nothing loads:

```bash
cd "/Users/winstonzulu/Documents/GitHub/DogFrce Security Services Custom Odoo Modules"

# Start everything
docker compose -f deploy/docker-compose.yml --env-file .env up -d

# Wait ~15 seconds, then open http://localhost:8069/odoo
```

If the database container keeps restarting (crash loop):

```bash
# Remove and recreate containers (data is safe — it lives in .local/postgres)
docker rm -f dogforce-odoo-dev-db dogforce-odoo-dev-odoo
docker compose -f deploy/docker-compose.yml --env-file .env up -d
```
