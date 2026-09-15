# DG-ADR-018 — Odoo Bridge Addon Pattern

- **Status:** Accepted in principle (product decision R-2, 2026-09-15); design Proposed
- **Date:** 2026-09-15
- **Related:** [12-odoo-integration](../12-odoo-integration.md), [DG-ADR-006](DG-ADR-006-odoo-integration.md), [DG-ADR-007](DG-ADR-007-authentication.md), existing `docs/adr/0013-*` (`_inherit` integration)

## Context

The product owner decided that DeployGuard Platform connects to DeployGuard ERP through **Odoo-side bridge addons**. The repository already uses auto-install `*_bridge` modules (`security_compliance_roster`, `security_fleet_ops`, `security_mobile_bridge`, …) and an Intelligence Bus (`security.event.log`) whose dispatcher calls a **hardcoded list** of five bridge models. That list is why `security.mobile.bridge` and `security.portal.bridge` are never invoked (defect D-4).

DeployGuard ERP is multi-client: modules are installed per client and **never deleted** because a client doesn't use them (R-6). Namibian production must not receive Zambia-only modules.

## Decision

### 1. Module set

| Addon | Depends on | Auto-install | Responsibility |
|---|---|---|---|
| **`security_deployguard_bridge`** (core) | `security_base`, `auth_totp`, `rpc`, `mail` | No: installed explicitly per client that uses the Platform | Configuration, keys, integration user and group, **auth endpoints and SSO tickets** (DG-ADR-007), outbox and webhook delivery, facade API model, identity events, command log, audit, health endpoint |
| `security_deployguard_attendance` | core + `security_attendance` | Yes | Attendance batch/record events; facade reads for batches and day records |
| `security_deployguard_roster` | core + `security_operations` | Yes | Roster slot and batch events (published, assigned, unfilled, changed); shift projections |
| `security_deployguard_incidents` | core + `security_discipline` | Yes | Incident created / state changed / reviewed events |
| `security_deployguard_leave` | core + `security_leave` | Yes | Approved and cancelled leave events (expected-work exclusions) |
| `security_deployguard_compliance` | core + `security_documents` | Yes (V1) | Certification and document expiry events; allowlisted `create_employee_certification` command |
| `security_deployguard_notifications` | core + `security_notifications` | Yes | Forwards new `security.notification` alerts (roster gaps, missed check-ins, expiries) as signals (C-5) |

New domain bridges follow the naming rule `security_deployguard_<domain>` and auto-install when their domain module and the core bridge are both present. **Installing the core bridge is the per-client switch.**

### 2. Intelligence Bus subscriber registry (change in `security_base`)

Replace the hardcoded dispatch list in `security.event.log._dispatch_event` with a registry:

- An abstract mixin `security.bus.subscriber` declares `_bus_events = ['attendance.missed', ...]` (or `'*'`) and `_handle_bus_event(event)`.
- The dispatcher iterates installed models inheriting the mixin, and calls each in its own savepoint with error isolation (as today's try/except).
- Existing five bridges plus `security.mobile.bridge` and `security.portal.bridge` adopt the mixin. This **also fixes D-4**.

This is the only change the Platform requires in existing ERP modules. It is a separate, backwards-compatible PR with tests.

### 3. Outbox & delivery

- **Model `security.deployguard.outbox`:** `event_id` (UUIDv7), `event_type`, `event_version`, `occurred_at`, `model`, `res_id`, `write_date`, `payload` (JSON), `state` (pending/sent/failed/dead), `attempts`, `next_attempt_at`, `last_error`, `correlation_id`.
- **Written inside the originating transaction** by domain bridges, via ORM overrides (`create`/`write` on selected fields, state-transition methods) and bus subscriptions.
- **Delivery:**
  - an `ir.cron` runs every minute, plus a post-commit hook that schedules an immediate cron trigger;
  - batches of ≤ 200 are sent, HMAC-signed;
  - exponential backoff 1 m → 24 h, then `dead` with a health flag;
  - no HTTP calls inside business transactions.
- **Retention:** sent rows are purged after 14 days; dead rows are kept until resolved.
- Patterns (states, correlation ID, retry, log) mirror `security_reconciliation_core` for operator familiarity.

### 4. Facade API (JSON-2 surface)

- **Model `security.deployguard.api`** (abstract/transient, no table) exposes public, read-mostly methods returning plain JSON-serialisable dicts. Examples:
  - `get_sites(since)`, `get_roster_day(site_ids, date)`, `get_attendance_batches(since)`;
  - `get_employees(since)`, `get_user_identity(uid)`, `get_leave(since)`, `get_open_alerts(since)`.
- **Access:** `group_deployguard_integration`, held only by the integration user. Methods apply explicit field allowlists (no private HR fields such as bank details, national ID or medical documents unless a capability requires them and is approved).
- **Allowlisted commands (V1):** `create_employee_certification`, `post_record_note`. Each takes an `idempotency_key`, recorded in `security.deployguard.command.log`.

### 5. Auth & SSO endpoints

As specified in [DG-ADR-007](DG-ADR-007-authentication.md):

- `/api/deployguard/v1/auth/login`, `/auth/totp`, `/sso/ticket`, `/deployguard/sso/consume`;
- per-tenant Ed25519 signing keys (`kid` rotation);
- rate limiting (per login, IP and device), stored in a small throttle model or cache;
- CORS allowlist for the Platform web origin only;
- all security-relevant outcomes logged to `security.deployguard.audit`.

### 6. Configuration

Settings page under DeployGuard ERP Settings, restricted to `base.group_system`:

- Platform base URL, tenant ID;
- webhook HMAC secret (write-only display);
- signing key generation and rotation;
- integration user status;
- health (last delivery, backlog, dead letters);
- per-user "DeployGuard access" flag on `res.users` (also settable by the Platform provisioning flow via facade command in V1).

Secrets are stored encrypted using a key from the Odoo server configuration or environment, **not** in plain `ir.config_parameter`.

### 7. Quality gates

- Odoo unit tests for every event emission, outbox delivery states, signature generation, rate limiting and SSO ticket single-use and expiry.
- Contract tests validate emitted payloads against the vendored Platform JSON Schemas ([DG-ADR-005](DG-ADR-005-monorepo.md)).
- Security review of auth and SSO code before pilot.
- Performance check: bridge overhead on attendance batch submission < 50 ms p95.

## Alternatives

| Option | Why not |
|---|---|
| One monolithic `security_deployguard` addon depending on every domain module | Forces installing modules a client doesn't use; breaks per-client install policy. |
| Put Platform hooks directly into existing domain modules | Couples ERP modules to the Platform; every client inherits Platform code paths even without the Platform. |
| Extend `security_mobile` controllers | Mixed concerns; inherits its auth weaknesses. |
| Platform reads Odoo without any addon (JSON-2 on raw models only) | No push events, no SSO tickets, broad integration-user privileges, and schema coupling. |

## Tradeoffs

| We gain | We accept |
|---|---|
| Per-client installability consistent with ERP conventions | Several small addons to version and test |
| Least-privilege integration surface and push events | Bridge code is security-critical; needs review discipline |
| Fixes the Intelligence Bus dispatch defect as a side effect | A small refactor in `security_base` (core module) |

## Consequences

- The Namibian and Zambian module baselines ([26](../26-deployment-strategy.md)) list which bridges each client installs. `security_suite` is not used (R-5).
- Bridge addon versions declare the Platform contract version they implement (e.g. `contract: v1`). The Platform rejects webhooks from unsupported contract versions with a health alert.
