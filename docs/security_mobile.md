# `security_mobile` & React Native App — Implementation Plan

## Background

We have a full suite of 12 custom Odoo modules managing the DogForce Security Services operation. The attendance workflow today is:

1. **Roster Slots** (`security.roster.slot`) are generated for each date/site/post.
2. A **Posting Sheet Batch** (`security.attendance.batch`) is created to group records for a day.
3. **Attendance Records** (`security.attendance.record`) are linked to slots; supervisors fill in `check_in`, `check_out`, or `manual_presence` (Present / Absent / AWOL).

The goal is to mobilize this workflow with a React Native app that talks to Odoo via a dedicated `security_mobile` module that exposes secure API endpoints.

---

## User Roles & Access

Three account types will use the mobile app:

| Role | Odoo Group | App Capabilities |
|---|---|---|
| **Supervisor** | `group_security_supervisor` (existing) | View today's assigned roster, mark presence, log check-in/out |
| **Manager** | `group_security_manager` (new) | Multi-site attendance overview, approve overtime, view all posting sheets |
| **Owner** | `group_security_owner` (new) | Executive KPI dashboard (payroll costs, attendance rates, incident counts) |

> [!IMPORTANT]
> A new `group_security_manager` and `group_security_owner` group will be added to `security_base/security/security_groups.xml`. Manager inherits from Supervisor, Owner inherits from Manager (Odoo group hierarchy).

---

## Part 1 — `security_mobile` Odoo Module

### Architecture

The module exposes a set of **Odoo HTTP JSON controllers** at `/api/security/mobile/*`. These use Odoo's built-in session-based authentication (JSON-RPC `/web/session/authenticate`) so we reuse the existing user/password system — no extra auth server needed.

For supervisor PIN-based quick re-auth (after phone lock), we will store a hashed PIN on the employee record.

### Proposed Changes

---

#### [MODIFY] [security_groups.xml](file:///Users/winstonzulu/Documents/GitHub/DogFrce%20Security%20Services%20Custom%20Odoo%20Modules/custom_addons/security_base/security/security_groups.xml)

Add two new groups to the existing `Security Operations` privilege:

```xml
<record id="group_security_manager" model="res.groups">
    <field name="name">Security Manager</field>
    <field name="privilege_id" ref="security_base.group_privilege_security_operations"/>
    <field name="implied_ids" eval="[(4, ref('security_base.group_security_supervisor'))]"/>
</record>

<record id="group_security_owner" model="res.groups">
    <field name="name">Security Owner</field>
    <field name="privilege_id" ref="security_base.group_privilege_security_operations"/>
    <field name="implied_ids" eval="[(4, ref('security_base.group_security_manager'))]"/>
</record>
```

---

#### [MODIFY] [hr_employee.py](file:///Users/winstonzulu/Documents/GitHub/DogFrce%20Security%20Services%20Custom%20Odoo%20Modules/custom_addons/security_base/models/hr_employee.py)

Add mobile-specific fields to `hr.employee`:

```python
security_mobile_pin_hash = fields.Char(string="Mobile PIN (hashed)", copy=False)
security_mobile_device_token = fields.Char(string="FCM Device Token", copy=False)
security_mobile_last_login = fields.Datetime(readonly=True)
```

---

#### [NEW] `custom_addons/security_mobile/`

New module with the following structure:

```
security_mobile/
├── __manifest__.py
├── __init__.py
├── controllers/
│   ├── __init__.py
│   ├── main.py           # Base auth controller
│   ├── supervisor.py     # Supervisor-specific endpoints
│   ├── manager.py        # Manager-specific endpoints
│   └── owner.py          # Owner KPI endpoints
├── models/
│   ├── __init__.py
│   └── security_mobile_session.py  # Optional: device session tokens
├── security/
│   └── ir.model.access.csv
└── views/
    └── security_mobile_views.xml   # Odoo-side config views for device tokens
```

---

### API Contract

All endpoints return JSON. Authentication is via Odoo session cookie obtained from `/web/session/authenticate`. The mobile app stores the session ID in secure storage.

#### `POST /web/session/authenticate`
Standard Odoo auth. Mobile app sends `{db, login, password}`.

---

#### `GET /api/security/mobile/supervisor/today`
Returns the authenticated supervisor's posting sheet for today.

**Response:**
```json
{
  "batch_id": 42,
  "batch_state": "draft",
  "date": "2026-05-29",
  "site": { "id": 3, "name": "Acme HQ" },
  "slots": [
    {
      "slot_id": 101,
      "record_id": 201,
      "guard": { "id": 5, "name": "John Doe", "grade": "Grade B" },
      "post": "Main Gate",
      "shift": "Day Shift 06:00-18:00",
      "status": "scheduled",
      "manual_presence": "not_marked",
      "check_in": null,
      "check_out": null,
      "late_minutes": 0
    }
  ]
}
```

---

#### `POST /api/security/mobile/supervisor/mark`
Mark presence for a single attendance record.

**Request:**
```json
{
  "record_id": 201,
  "manual_presence": "present",   // "present" | "absent" | "awol"
  "check_in": "2026-05-29T06:05:00",  // optional
  "check_out": "2026-05-29T18:10:00"  // optional
}
```

---

#### `POST /api/security/mobile/supervisor/checkin`
Quick check-in for a single guard (timestamps now).

**Request:**
```json
{ "record_id": 201, "action": "check_in" }  // or "check_out"
```

---

#### `POST /api/security/mobile/supervisor/batch/submit`
Submit (capture) the full posting sheet batch.

**Request:** `{ "batch_id": 42 }`

---

#### `GET /api/security/mobile/manager/dashboard`
Multi-site attendance summary for today (Manager+).

**Response:**
```json
{
  "date": "2026-05-29",
  "sites": [
    {
      "site_id": 3, "site_name": "Acme HQ",
      "total_slots": 8, "present": 6, "absent": 1, "not_marked": 1,
      "late": 2, "awol": 0,
      "batch_state": "captured"
    }
  ]
}
```

---

#### `GET /api/security/mobile/manager/site/{site_id}`
Detailed roster list for a specific site (Manager+).

---

#### `POST /api/security/mobile/manager/overtime/approve`
Approve overtime for a record (Manager+).

**Request:** `{ "record_id": 201, "note": "Client authorised" }`

---

#### `GET /api/security/mobile/owner/kpis`
Executive KPIs (Owner only).

**Response:**
```json
{
  "period": "May 2026",
  "attendance_rate_percent": 94.2,
  "total_guards": 45,
  "awol_this_month": 3,
  "open_incidents": 7,
  "payroll_cost_ytd": 285000.0,
  "outstanding_invoices": 42000.0,
  "sites_active": 8
}
```

---

## Part 2 — React Native App

### Technology Stack

| Concern | Choice | Reason |
|---|---|---|
| Framework | React Native (Expo managed) | Cross-platform iOS + Android, fast iteration |
| Navigation | Expo Router (file-based) | Clean stack + tab navigation, deep links |
| State | Zustand | Lightweight, no boilerplate |
| API | `axios` + React Query (`@tanstack/query`) | Caching, background refresh, retry |
| Auth storage | `expo-secure-store` | Encrypted key-value for session ID & PIN |
| UI components | `react-native-paper` (Material 3) | Ready-made components, dark mode support |
| Icons | `@expo/vector-icons` (MaterialCommunityIcons) | Large icon set |
| Charts (Owner) | `victory-native` | Declarative charting for RN |
| Push notifications | `expo-notifications` + FCM | Alerts for AWOL guards, overtime requests |

---

### App Project Structure

```
DogForce-Mobile/
├── app/                       # Expo Router screens
│   ├── (auth)/
│   │   └── login.tsx
│   ├── (supervisor)/
│   │   ├── _layout.tsx        # Tab layout
│   │   ├── index.tsx          # Today's Posting Sheet
│   │   ├── mark/[recordId].tsx  # Mark presence screen
│   │   └── history.tsx        # Past batches
│   ├── (manager)/
│   │   ├── _layout.tsx
│   │   ├── index.tsx          # Multi-site dashboard
│   │   ├── site/[siteId].tsx  # Site detail roster
│   │   └── overtime.tsx       # Overtime approval list
│   ├── (owner)/
│   │   ├── _layout.tsx
│   │   └── index.tsx          # KPI dashboard
│   └── _layout.tsx            # Root layout + auth guard
├── src/
│   ├── api/
│   │   ├── client.ts          # Axios instance + session interceptors
│   │   ├── auth.ts
│   │   ├── supervisor.ts
│   │   ├── manager.ts
│   │   └── owner.ts
│   ├── stores/
│   │   ├── authStore.ts       # Zustand: session, user, role
│   │   └── appStore.ts        # Zustand: selected date, site filter
│   ├── components/
│   │   ├── GuardCard.tsx      # Attendance record row card
│   │   ├── StatusBadge.tsx    # Present/Absent/AWOL colour chip
│   │   ├── SiteKpiCard.tsx    # Manager site summary card
│   │   ├── KpiMetric.tsx      # Owner KPI number tile
│   │   └── CheckInButton.tsx  # Large CTA button with timer
│   ├── hooks/
│   │   ├── useToday.ts        # React Query: supervisor today
│   │   ├── useDashboard.ts    # React Query: manager dashboard
│   │   └── useKpis.ts         # React Query: owner kpis
│   └── theme/
│       └── index.ts           # Color palette, typography, spacing
├── assets/
│   └── dogforce-logo.png
├── app.json
└── package.json
```

---

### Screen Designs

#### Supervisor — Posting Sheet (`index.tsx`)
- Header: Date + Site name + Batch status badge (Draft / Captured)
- Search bar to filter guards by name
- **`FlatList`** of `<GuardCard>` components, each showing:
  - Guard name + grade badge
  - Post + shift
  - `<StatusBadge>` coloured chip (Scheduled / Present / Late / Absent / AWOL)
  - Check-In / Check-Out timestamps if logged
- Swipe-right action on card → instantly marks **Present** (optimistic update)
- Swipe-left action → opens bottom sheet to select **Absent / AWOL**
- FAB **"Submit Posting Sheet"** button, enabled when all guards are marked
- Pull-to-refresh every 30 seconds

#### Supervisor — Mark Presence (`mark/[recordId].tsx`)
- Large guard name + photo avatar
- Post / shift details
- **Check-In** big button (logs current timestamp, green)
- **Check-Out** big button (logs current timestamp, red)
- Manual override toggles: Present / Absent / AWOL
- Text input for override reason
- Save button

#### Manager — Site Dashboard (`(manager)/index.tsx`)
- Date picker at top
- Scrollable list of `<SiteKpiCard>` components per site:
  - Site name + client
  - Progress bar: present / total slots
  - Color-coded breakdown (green=present, orange=late, red=absent)
  - Tap → navigate to `site/[siteId]`
- Bottom tabs: Today | Overtime Requests

#### Manager — Site Detail (`site/[siteId].tsx`)
- Same `<GuardCard>` list as supervisor but **read-only** by default
- Manager can override any record if needed
- **Overtime Requests** section at bottom with Approve / Reject buttons

#### Owner — KPI Dashboard (`(owner)/index.tsx`)
- Period selector (Month)
- Row of `<KpiMetric>` tiles:
  - Attendance Rate %
  - Guards on Duty
  - AWOL This Month
  - Open Incidents
- Bar chart: Monthly Payroll Cost (last 6 months)
- Donut chart: Attendance breakdown (Present / Late / Absent / AWOL)
- Horizontal scroll: Top 5 Sites by attendance rate

---

## Open Questions

> [!IMPORTANT]
> **1. Offline mode?** Should the supervisor app work offline (cache roster slots locally, queue marks for sync when reconnected)? This is important for remote sites with poor network. Adds significant complexity with `react-native-mmkv` + sync queue.

> [!IMPORTANT]
> **2. PIN vs Biometric?** For quick re-auth after phone lock, should we use a 4-digit PIN stored (hashed) on the Odoo employee record, or device biometrics (`expo-local-authentication`) with no server-side state? Biometrics is simpler and more secure.

> [!NOTE]
> **3. Odoo version?** The manifests declare `19.0.1.0.0`. The HTTP controller auth approach is the same across 16–19 but the exact session cookie behaviour should be confirmed.

> [!NOTE]
> **4. Expo Go vs bare workflow?** Expo Go is fastest for development. If push notifications via FCM are required before Expo's managed push service, we may need a bare/prebuild workflow.

> [!NOTE]
> **5. Supervisor site assignment?** Currently `security.client.site` has a `supervisor_id` field. The API will filter today's roster slots by `site.supervisor_id == current_user.employee_id`. Does each supervisor manage exactly one site, or can they float across multiple? This affects the "today" screen layout.

---

## Verification Plan

### Odoo Module (`security_mobile`)
- `python -m pytest` for controller unit tests using Odoo's test framework
- Manually call each endpoint via curl/Postman with valid session cookies
- Verify group-based access: Supervisor cannot access `/manager/*`, etc.

### React Native App
- Expo local dev with simulator (iOS Simulator / Android Emulator)
- Point to local Odoo dev instance (`ODOO_BASE_URL=http://localhost:8069`)
- Manual QA: complete posting-sheet workflow end-to-end
- TestFlight / Internal Track for device testing before release
