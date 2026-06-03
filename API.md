# API Reference

HTTP API for the DogForce Security Suite mobile app and integrations.

**Base URL (local dev):** `http://localhost:8069`

**Module required:** `security_mobile` (plus its dependencies)

Implementation: `custom_addons/security_mobile/controllers/`

---

## Authentication

The mobile app uses **Odoo session authentication**. Custom endpoints under `/api/security/mobile/*` require an active Odoo session (`auth="user"`). Role-specific endpoints additionally require membership in a security group.

### Session login

| | |
|---|---|
| **Endpoint** | `POST /web/session/authenticate` |
| **Auth** | None (public) |
| **Content-Type** | `application/json` |

**Request body (JSON-RPC):**

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "db": "dogforce_dev",
    "login": "admin",
    "password": "admin"
  }
}
```

**Success response (200):**

```json
{
  "jsonrpc": "2.0",
  "id": null,
  "result": {
    "uid": 2,
    "is_system": false,
    "is_admin": true,
    "is_public": false,
    "is_internal_user": true,
    "user_context": { "lang": "en_US", "tz": "Africa/Windhoek", "uid": 2 },
    "db": "dogforce_dev",
    "user_settings": {},
    "server_version": "19.0",
    "server_version_info": [19, 0, 0, 0, 0, ""],
    "support_url": "https://www.odoo.com/buy",
    "name": "Administrator",
    "username": "admin",
    "partner_display_name": "Administrator",
    "partner_id": 3,
    "web.base.url": "http://localhost:8069",
    "active_ids_limit": 20000,
    "profile_session": null,
    "profile_collectors": null,
    "profile_params": null,
    "max_file_upload_size": 134217728,
    "home_action_id": false,
    "cache_hashes": {},
    "currencies": {},
    "bundle_params": {},
    "user_companies": {},
    "show_effect": true,
    "display_switch_company_menu": false,
    "user_id": [2, "Administrator"],
    "session_id": "abc123..."
  }
}
```

| Field | Description |
|-------|-------------|
| `result.uid` | Odoo user ID |
| `result.session_id` | Session token — store and send on subsequent requests |
| `result.name` | Display name |
| `result.username` | Login username |

**Failure response:** `result` is `false` or an `error` object is returned:

```json
{
  "jsonrpc": "2.0",
  "id": null,
  "error": {
    "code": 100,
    "message": "Odoo Session Expired",
    "data": { "name": "odoo.exceptions.AccessDenied", "message": "Access Denied" }
  }
}
```

### Session logout

| | |
|---|---|
| **Endpoint** | `POST /web/session/destroy` |
| **Auth** | Session required |
| **Content-Type** | `application/json` |

**Request body:**

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {}
}
```

**Success response (200):**

```json
{
  "jsonrpc": "2.0",
  "id": null,
  "result": {}
}
```

### Sending credentials on custom API requests

Include the session on every request to `/api/security/mobile/*`:

| Header | Value |
|--------|-------|
| `Content-Type` | `application/json` |
| `Accept` | `application/json` |
| `X-Openerp-Session-Id` | `{session_id}` from authenticate |
| `Cookie` | `session_id={session_id}` |

The mobile client also sets `withCredentials: true` on Axios (`mobile/src/api/client.ts`).

---

## Response envelope (custom API)

All `/api/security/mobile/*` endpoints return the same JSON envelope:

**Success:**

```json
{
  "success": true,
  "data": { }
}
```

**Error:**

```json
{
  "success": false,
  "error": "Human-readable error message"
}
```

---

## Authorization groups

Custom endpoints enforce Odoo security groups via `@require_group()`:

| Role | Odoo group XML ID | Endpoints |
|------|-------------------|-----------|
| Supervisor | `security_base.group_security_supervisor` | `/api/security/mobile/supervisor/*` |
| Manager | `security_base.group_security_manager` | `/api/security/mobile/manager/*` |
| Owner | `security_base.group_security_owner` | `/api/security/mobile/owner/*` |

Group hierarchy: **Owner → Manager → Supervisor** (each inherits the level below).

The user's `hr.employee` record must be linked via `user_id` for supervisor site scoping.

---

## Common HTTP status codes

| Status | When |
|--------|------|
| **200** | Success (`success: true`) |
| **400** | Validation error — missing/invalid body fields, invalid date format, batch in wrong state |
| **401** | No session or expired session (Odoo standard auth, before controller runs) |
| **403** | Authenticated but wrong role (`Access denied: insufficient role.`) |
| **404** | Record not found (attendance record, batch, site) |
| **500** | Unhandled server exception (e.g. batch submit failure) |

### Common error messages

| Message | Cause |
|---------|-------|
| `Access denied: insufficient role.` | User lacks the required security group |
| `No employee record linked to your user account.` | Supervisor user has no linked `hr.employee` |
| `record_id is required.` | POST body missing `record_id` |
| `batch_id is required.` | POST body missing `batch_id` |
| `manual_presence must be present \| absent \| awol \| not_marked.` | Invalid presence value |
| `action must be check_in or check_out.` | Invalid quick check-in action |
| `Invalid check_in datetime: …` / `Invalid check_out datetime: …` | Not valid ISO 8601 |
| `Nothing to update — provide at least one field.` | Empty update in mark endpoint |
| `Attendance record {id} not found.` | Invalid `record_id` |
| `Batch {id} not found.` | Invalid `batch_id` |
| `Batch is already in state '…' and cannot be submitted again.` | Batch not in `draft` |
| `Site {id} not found.` | Invalid site ID in URL |
| `Invalid date: …` | Query param `date` not `YYYY-MM-DD` |
| `Invalid month format: … Use YYYY-MM.` | Query param `month` not `YYYY-MM` |

---

## Endpoint index

| Method | Path | Role | Description |
|--------|------|------|-------------|
| `GET` | `/api/security/mobile/supervisor/today` | Supervisor | Today's posting sheet or roster fallback |
| `POST` | `/api/security/mobile/supervisor/mark` | Supervisor | Mark/update presence for one record |
| `POST` | `/api/security/mobile/supervisor/checkin` | Supervisor | Quick check-in/out (UTC now) |
| `POST` | `/api/security/mobile/supervisor/batch/submit` | Supervisor | Submit (capture) a posting sheet batch |
| `GET` | `/api/security/mobile/manager/dashboard` | Manager | Multi-site attendance summary |
| `GET` | `/api/security/mobile/manager/site/<site_id>` | Manager | Single-site roster detail |
| `POST` | `/api/security/mobile/manager/overtime/approve` | Manager | Approve or reject overtime |
| `GET` | `/api/security/mobile/owner/kpis` | Owner | Executive KPI dashboard |

---

## Supervisor endpoints

### GET `/api/security/mobile/supervisor/today`

Returns today's posting sheet for sites supervised by the logged-in employee.

| | |
|---|---|
| **Auth** | Session + `group_security_supervisor` |
| **Query params** | None |
| **Request body** | None |

**Logic:**

1. Find active sites where `supervisor_id` = current user's employee.
2. Find today's `security.attendance.batch` records for those sites.
3. If none, fall back to batches captured by the current user today.
4. If still none, return unassigned roster slots (no batch yet).

#### Response A — existing batch(es)

When one batch exists, `data` is a single batch object. When multiple exist, `data` is an array of batch objects.

```json
{
  "success": true,
  "data": {
    "batch_id": 12,
    "batch_state": "draft",
    "date": "2026-05-30",
    "site": { "id": 3, "name": "Bank Windhoek HQ" },
    "client": { "id": 45, "name": "Bank Windhoek" },
    "slots": [
      {
        "record_id": 101,
        "slot_id": 55,
        "guard": { "id": 8, "name": "Johannes Iita", "grade": "Grade A" },
        "post": "Main Gate",
        "shift": "Day Shift",
        "shift_start": 6.0,
        "shift_end": 18.0,
        "status": "scheduled",
        "manual_presence": "not_marked",
        "check_in": null,
        "check_out": null,
        "late_minutes": 0,
        "overtime_hours": 0,
        "override_reason": null
      }
    ]
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `batch_id` | integer | `security.attendance.batch` ID |
| `batch_state` | string | `draft`, `captured`, `reviewed`, `locked`, `cancelled` |
| `date` | string | ISO date (`YYYY-MM-DD`) |
| `site` | object \| null | `{ id, name }` |
| `client` | object \| null | `{ id, name }` |
| `slots` | array | Attendance records (see slot object below) |

**Slot / attendance record object:**

| Field | Type | Description |
|-------|------|-------------|
| `record_id` | integer | `security.attendance.record` ID |
| `slot_id` | integer \| null | Linked `security.roster.slot` ID |
| `guard` | object | `{ id, name, grade }` |
| `post` | string \| null | Post name |
| `shift` | string \| null | Shift template name |
| `shift_start` | float \| null | Start hour as float (e.g. `6.0` = 06:00) |
| `shift_end` | float \| null | End hour as float |
| `status` | string | Computed: `scheduled`, `present`, `late`, `early_leave`, `absent`, `incomplete` |
| `manual_presence` | string | `not_marked`, `present`, `absent`, `awol` |
| `check_in` | string \| null | ISO 8601 datetime |
| `check_out` | string \| null | ISO 8601 datetime |
| `late_minutes` | integer | Minutes late |
| `overtime_hours` | float | Approved overtime hours |
| `override_reason` | string \| null | Supervisor override note |

#### Response B — roster fallback (no batch)

```json
{
  "success": true,
  "data": {
    "date": "2026-05-30",
    "has_batch": false,
    "roster_slots": [
      {
        "slot_id": 55,
        "guard": { "id": 8, "name": "Johannes Iita", "grade": "Grade A" },
        "post": "Main Gate",
        "site": { "id": 3, "name": "Bank Windhoek HQ" },
        "shift": "Day Shift",
        "shift_start": 6.0,
        "shift_end": 18.0,
        "state": "assigned"
      }
    ]
  }
}
```

---

### POST `/api/security/mobile/supervisor/mark`

Mark or update presence and timestamps for a single attendance record.

| | |
|---|---|
| **Auth** | Session + `group_security_supervisor` |
| **Content-Type** | `application/json` |

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `record_id` | integer | Yes | `security.attendance.record` ID |
| `manual_presence` | string | No | `present`, `absent`, `awol`, `not_marked` |
| `check_in` | string | No | ISO 8601 datetime |
| `check_out` | string | No | ISO 8601 datetime |
| `override_reason` | string | No | Reason for manual override |

**Example request:**

```json
{
  "record_id": 101,
  "manual_presence": "present",
  "check_in": "2026-05-30T06:12:00",
  "check_out": "2026-05-30T18:05:00",
  "override_reason": "Guard arrived slightly late — verified on CCTV"
}
```

**Success response (200):** `data` is a single slot/attendance record object (same shape as in GET today).

**Errors:** 400 (validation), 404 (record not found)

---

### POST `/api/security/mobile/supervisor/checkin`

Quick check-in or check-out using the current UTC timestamp.

| | |
|---|---|
| **Auth** | Session + `group_security_supervisor` |
| **Content-Type** | `application/json` |

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `record_id` | integer | Yes | `security.attendance.record` ID |
| `action` | string | Yes | `check_in` or `check_out` |

**Example request:**

```json
{
  "record_id": 101,
  "action": "check_in"
}
```

**Behaviour:**

| `action` | Effect |
|----------|--------|
| `check_in` | Sets `check_in` to UTC now; sets `manual_presence` to `present` |
| `check_out` | Sets `check_out` to UTC now |

**Success response (200):** `data` is a single attendance record object.

**Errors:** 400 (validation), 404 (record not found)

---

### POST `/api/security/mobile/supervisor/batch/submit`

Submit (capture) a posting sheet batch.

| | |
|---|---|
| **Auth** | Session + `group_security_supervisor` |
| **Content-Type** | `application/json` |

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `batch_id` | integer | Yes | `security.attendance.batch` ID |

**Example request:**

```json
{
  "batch_id": 12
}
```

**Success response (200):**

```json
{
  "success": true,
  "data": {
    "batch_id": 12,
    "new_state": "captured"
  }
}
```

**Errors:**

| Status | Condition |
|--------|-----------|
| 400 | Missing `batch_id`; batch not in `draft` state |
| 404 | Batch not found |
| 500 | Odoo action failure (message in `error`) |

---

## Manager endpoints

### GET `/api/security/mobile/manager/dashboard`

Multi-site attendance summary for all active client sites.

| | |
|---|---|
| **Auth** | Session + `group_security_manager` |
| **Query params** | `date` (optional) — `YYYY-MM-DD`, defaults to today |

**Example:** `GET /api/security/mobile/manager/dashboard?date=2026-05-30`

**Success response (200):**

```json
{
  "success": true,
  "data": {
    "date": "2026-05-30",
    "overall": {
      "total_slots": 24,
      "present": 20,
      "absent": 2,
      "awol": 1,
      "late": 3,
      "attendance_rate": 83.3
    },
    "sites": [
      {
        "site_id": 3,
        "site_name": "Bank Windhoek HQ",
        "client": "Bank Windhoek",
        "supervisor": "Maria Kandjii",
        "total_slots": 8,
        "present": 7,
        "absent": 0,
        "awol": 0,
        "late": 1,
        "not_marked": 1,
        "attendance_rate": 87.5,
        "batch_state": "captured",
        "batch_id": 12
      }
    ]
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `overall.total_slots` | integer | Sum across all sites |
| `overall.attendance_rate` | float | Percent present / total |
| `sites[].batch_state` | string | Batch state, or `no_batch` if none exists |
| `sites[].batch_id` | integer \| null | Batch ID if exists |

**Errors:** 400 (invalid `date` format)

---

### GET `/api/security/mobile/manager/site/<site_id>`

Detailed roster and pending overtime for one site.

| | |
|---|---|
| **Auth** | Session + `group_security_manager` |
| **Path params** | `site_id` — `security.client.site` ID |
| **Query params** | `date` (optional) — `YYYY-MM-DD`, defaults to today |

**Example:** `GET /api/security/mobile/manager/site/3?date=2026-05-30`

**Success response (200):**

```json
{
  "success": true,
  "data": {
    "date": "2026-05-30",
    "site": {
      "id": 3,
      "name": "Bank Windhoek HQ",
      "client": "Bank Windhoek"
    },
    "batch_id": 12,
    "batch_state": "captured",
    "supervisor": "Maria Kandjii",
    "roster": [
      {
        "record_id": 101,
        "guard": { "id": 8, "name": "Johannes Iita", "grade": "Grade A" },
        "post": "Main Gate",
        "shift": "Day Shift",
        "manual_presence": "present",
        "check_in": "2026-05-30T06:12:00",
        "check_out": "2026-05-30T18:05:00",
        "late_minutes": 12,
        "overtime_hours": 0.5,
        "overtime_approved": false
      }
    ],
    "overtime_pending": [
      {
        "record_id": 101,
        "guard": { "id": 8, "name": "Johannes Iita", "grade": "Grade A" },
        "post": "Main Gate",
        "shift": "Day Shift",
        "manual_presence": "present",
        "check_in": "2026-05-30T06:12:00",
        "check_out": "2026-05-30T18:05:00",
        "late_minutes": 12,
        "overtime_hours": 0.5,
        "overtime_approved": false
      }
    ]
  }
}
```

When no batch exists, `roster` items use `record_id: null` and include `slot_id` instead:

```json
{
  "slot_id": 55,
  "record_id": null,
  "guard": { "id": 8, "name": "Johannes Iita", "grade": "Grade A" },
  "post": "Main Gate",
  "shift": "Day Shift",
  "manual_presence": "not_marked"
}
```

**Errors:** 400 (invalid date), 404 (site not found)

---

### POST `/api/security/mobile/manager/overtime/approve`

Approve or reject overtime on an attendance record.

| | |
|---|---|
| **Auth** | Session + `group_security_manager` |
| **Content-Type** | `application/json` |

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `record_id` | integer | Yes | `security.attendance.record` ID |
| `approved` | boolean | No | Default `true` |
| `note` | string | No | Approval/rejection note |

**Example request:**

```json
{
  "record_id": 101,
  "approved": true,
  "note": "Approved — client requested extended cover"
}
```

**Success response (200):**

```json
{
  "success": true,
  "data": {
    "record_id": 101,
    "overtime_approved": true
  }
}
```

**Errors:** 400 (missing `record_id`), 404 (record not found)

---

## Owner endpoints

### GET `/api/security/mobile/owner/kpis`

Executive KPI dashboard aggregated across the operation.

| | |
|---|---|
| **Auth** | Session + `group_security_owner` |
| **Query params** | `month` (optional) — `YYYY-MM`, defaults to current month |

**Example:** `GET /api/security/mobile/owner/kpis?month=2026-05`

**Success response (200):**

```json
{
  "success": true,
  "data": {
    "period": "May 2026",
    "period_start": "2026-05-01",
    "period_end": "2026-05-31",
    "attendance": {
      "rate_percent": 91.2,
      "total_records": 480,
      "present": 438,
      "absent": 30,
      "awol": 12,
      "late": 45
    },
    "total_guards": 86,
    "sites_active": 12,
    "open_incidents": 3,
    "payroll_cost_ytd": 1250000.0,
    "outstanding_invoices": 340000.0,
    "monthly_payroll_trend": [
      { "month": "Dec 2025", "cost": 980000.0 },
      { "month": "Jan 2026", "cost": 1020000.0 },
      { "month": "Feb 2026", "cost": 1050000.0 },
      { "month": "Mar 2026", "cost": 1080000.0 },
      { "month": "Apr 2026", "cost": 1100000.0 },
      { "month": "May 2026", "cost": 1120000.0 }
    ],
    "top_sites_by_attendance": [
      {
        "site_id": 3,
        "site_name": "Bank Windhoek HQ",
        "client": "Bank Windhoek",
        "total_records": 60,
        "present": 58,
        "attendance_rate": 96.7
      }
    ]
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `attendance.rate_percent` | float | Present / total records in period |
| `total_guards` | integer | Active guards (`security_guard = true`) |
| `sites_active` | integer | Active client sites |
| `open_incidents` | integer | Non-closed `security.incident` records (0 if module absent) |
| `payroll_cost_ytd` | float | Sum of `gross_pay` on done payslips since Jan 1 |
| `outstanding_invoices` | float | Residual on posted customer invoices (requires Odoo Accounting) |
| `monthly_payroll_trend` | array | Last 6 months gross payroll |
| `top_sites_by_attendance` | array | Top 5 sites by attendance rate in period |

**Errors:** 400 (invalid `month` format)

---

## Data types reference

| Type | Format | Example |
|------|--------|---------|
| Date | `YYYY-MM-DD` | `2026-05-30` |
| Month | `YYYY-MM` | `2026-05` |
| Datetime | ISO 8601 | `2026-05-30T06:12:00` or `2026-05-30T06:12:00+00:00` |
| Shift hour | Float (24h) | `6.0` = 06:00, `18.5` = 18:30 |
| Presence | Enum | `not_marked`, `present`, `absent`, `awol` |
| Batch state | Enum | `draft`, `captured`, `reviewed`, `locked`, `cancelled`, `no_batch` |

---

## Example: full supervisor flow

```bash
# 1. Authenticate
curl -s -c cookies.txt -X POST http://localhost:8069/web/session/authenticate \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"call","params":{"db":"dogforce_dev","login":"admin","password":"admin"}}'

# Extract session_id from result, then:

# 2. Get today's posting sheet
curl -s -b cookies.txt \
  -H 'Content-Type: application/json' \
  http://localhost:8069/api/security/mobile/supervisor/today

# 3. Mark presence
curl -s -b cookies.txt -X POST http://localhost:8069/api/security/mobile/supervisor/mark \
  -H 'Content-Type: application/json' \
  -d '{"record_id":101,"manual_presence":"present","check_in":"2026-05-30T06:00:00","check_out":"2026-05-30T18:00:00"}'

# 4. Submit batch
curl -s -b cookies.txt -X POST http://localhost:8069/api/security/mobile/supervisor/batch/submit \
  -H 'Content-Type: application/json' \
  -d '{"batch_id":12}'
```

---

## Mobile client mapping

TypeScript client wrappers live in `mobile/src/api/`:

| API module | File |
|------------|------|
| Auth | `mobile/src/api/auth.ts` |
| Supervisor | `mobile/src/api/supervisor.ts` |
| Manager | `mobile/src/api/manager.ts` |
| Owner | `mobile/src/api/owner.ts` |
| HTTP client | `mobile/src/api/client.ts` |

---

## Known implementation notes

These are documented so integrators understand current controller behaviour vs. the underlying Odoo models:

| Issue | Detail |
|-------|--------|
| **Batch field name** | Controllers query attendance records with `batch_id`, but the model field is `attendance_batch_id`. Batch slot lists may return empty until aligned. |
| **Overtime note field** | Manager approve endpoint writes `overtime_note`; the model field is `overtime_approval_note`. Notes may not persist. |
| **Owner KPI domain** | Owner endpoint filters on `batch_id.attendance_date`; should use `attendance_batch_id.attendance_date`. |
| **Batch submit action** | Controller calls `action_capture()` if present; otherwise sets `state = captured`. The model defines `action_generate_from_roster()` but not `action_capture()`. |
| **PIN re-auth** | Documented in `docs/security_mobile.md`; `security_mobile_pin_hash` exists on `hr.employee` but no PIN endpoint is implemented yet. |

---

## Related documentation

| Document | Description |
|----------|-------------|
| [docs/security_mobile.md](docs/security_mobile.md) | Mobile implementation plan and design rationale |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Mobile API layer in system context |
| [CODEBASE_MAP.md](CODEBASE_MAP.md) | Controller and client file locations |
| [INSTALL.md](INSTALL.md) | Local setup and module installation |
