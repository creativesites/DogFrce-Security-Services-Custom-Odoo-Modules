# DG-ADR-006 — Odoo Integration

- **Status:** Proposed
- **Date:** 2026-09-15
- **Related:** [12-odoo-integration](../12-odoo-integration.md), [DG-ADR-007](DG-ADR-007-authentication.md), [DG-ADR-018](DG-ADR-018-odoo-bridge-addons.md), [14-data-model](../14-data-model.md) §Data ownership

## Context

The Platform must read ERP facts from each tenant's DeployGuard ERP (Odoo 19):

- employees, sites/posts, roster slots, attendance batches and records;
- incidents, leave;
- certifications and document expiry;
- Odoo-generated alerts.

It must react quickly to changes (for exceptions and task auto-completion), perform a small number of allowlisted writes (V1), and generate deep links. It must not scatter RPC calls throughout the code or couple Platform models to Odoo model shapes.

Verified in the Odoo 19 runtime (`odoo/addons/rpc`, auto-installed):

- **JSON-2** is available at `POST /json/2/<model>/<method>` with `auth='bearer'` (user API key).
- **`/xmlrpc`, `/xmlrpc/2` and `/jsonrpc` are deprecated in Odoo 19 and scheduled for removal in Odoo 22** (runtime deprecation notice).

Existing DeployGuard ERP assets to build on:

- `security.event.log` (bus with a hardcoded dispatch list);
- the `security_reconciliation_core` job, retry and conflict framework;
- `security.notification` scanners.

## Decision

A **hybrid push + pull integration**, with all Platform-side access in one package and all Odoo-side exposure in bridge addons.

### Platform side: `packages/odoo` (`OdooAdapter`)

- **Transport:** JSON-2 only. Bearer API key of a **dedicated integration user per tenant** (`DeployGuard Integration`), stored encrypted in Platform secret storage. Database selection header where the Odoo server hosts several databases (verify header name against Odoo 19 docs during P1).
- **Surface:** typed methods, not generic `call(model, method)` in feature code. Examples: `listSites(since)`, `getRosterForDay(siteIds, date)`, `getAttendanceBatches(since)`, `getEmployee(id)`, `buildDeepLink(target)`. Mappers convert Odoo records to Platform **projection DTOs** (`SiteProjection`, `ShiftProjection`, …) defined in `packages/contracts`.
- **Resilience:**
  - timeouts;
  - retry with jittered backoff on idempotent reads;
  - circuit breaker per tenant connection;
  - rate limit per tenant (default 5 req/s);
  - every call traced with the tenant and correlation ID.
- **Curated server methods:** the adapter prefers the bridge's facade model (`security.deployguard.api`) over raw model reads. The integration user then needs only that facade's access rights instead of broad ACLs, and Odoo field changes are absorbed in one place (the bridge).

### Odoo side: bridge addons ([DG-ADR-018](DG-ADR-018-odoo-bridge-addons.md))

- **Push:**
  - Domain changes write a row to `security.deployguard.outbox` **inside the same Odoo transaction** (never HTTP inside an ORM transaction).
  - A cron-driven dispatcher (every minute, plus a post-commit trigger) delivers batches to `POST {platform}/v1/integrations/odoo/webhooks`.
  - Signature: `X-DG-Signature: t=<unix>, v1=<HMAC-SHA256(secret, t + "." + body)>`.
  - Delivery is at-least-once, with exponential backoff up to 24 h, then a dead letter plus a Platform-visible health alert.
- **Pull (reconciliation):**
  - The Platform worker polls facade methods with `write_date` watermarks per entity type (default every 5 min; 1 min for roster and attendance on the current day).
  - Polling repairs missed webhooks and seeds initial sync.
- **Identity events** (user deactivated, password or TOTP changed, access revoked) are pushed with priority and also covered by polling ([DG-ADR-007](DG-ADR-007-authentication.md) §5).

### Ownership & conflicts

- **Odoo-owned facts** (employees, sites, roster, attendance, incidents, leave, certifications) are **read-only projections** in the Platform. On conflict, **Odoo wins, always**. Projections store `odoo_write_date` and a content hash, and never accept Platform edits.
- **Platform-owned facts** (tasks, training, competencies, exceptions) are never written into Odoo models, except via **allowlisted bridge commands** (V1). Examples: `create_employee_certification` (from an approved Platform certification, C-7) and `post_chatter_note` (link an exception resolution to an Odoo record). Each command:
  - is a public method on the facade with explicit parameters;
  - takes an idempotency key from the Platform (stored in the bridge's command log to prevent duplicates);
  - is audited on both sides.

### Idempotency

- Every webhook event carries a stable `event_id` (UUIDv7 generated in Odoo) and `(model, res_id, write_date)`. The Platform deduplicates on `event_id` at ingestion and on `(tenant, model, res_id, write_date)` in projections.
- Polling upserts by `(tenant, odoo_model, odoo_id)`; a projection is only updated when `write_date` or the content hash changes.

### Deep links

The adapter's `buildDeepLink({ action | model, id })` is the only place Odoo URL formats exist. The result is passed to the SSO ticket flow ([DG-ADR-007](DG-ADR-007-authentication.md) §4).

## Alternatives

| Option | Why not |
|---|---|
| XML-RPC / legacy JSON-RPC (`/jsonrpc`) | Deprecated in Odoo 19, removed in Odoo 22. |
| Polling only | Simple, but the 5-minute lag is too slow for exception detection, and costly at scale. Kept as the reconciliation path. |
| Webhooks only | Silent data loss when delivery fails or Odoo is restored from backup; polling is the safety net. |
| Direct PostgreSQL read replica of Odoo DB / CDC (Debezium) | Bypasses Odoo access rules and business logic, couples to Odoo's internal schema, and requires DB-level network access into customer infrastructure. Rejected for security and portability. |
| Odoo's `base_automation` webhooks (no-code) | Not version-controlled, no signing or retry guarantees we control, configuration drift per tenant. |
| Integration user with broad ORM ACLs | Excessive privilege; any Platform compromise exposes the whole ERP. Facade methods keep least privilege. |
| Reuse `security_reconciliation_core` jobs directly as the transport | Its model is designed for internal cross-module reconciliation with per-company rules. The bridge **reuses its patterns** (job states, correlation ID, retries, conflict log) in a dedicated outbox, avoiding coupling Platform delivery to finance reconciliation. |

## Tradeoffs

| We gain | We accept |
|---|---|
| Near-real-time changes with guaranteed eventual consistency | Two mechanisms (push + pull) to operate and monitor |
| Least-privilege, version-controlled integration surface | Bridge facade methods must evolve with Platform needs (coordinated releases) |
| Platform isolated from Odoo schema churn | Additional mapping layer |

## Consequences

- The Odoo side gets the bridge addons; the Platform side gets `packages/odoo` and the `odoo-sync` module (projections, watermarks, webhook ingestion, health metrics).
- Integration health is visible to tenant admins (PR-ODO-06): last webhook received, delivery lag, poll lag, error rate, dead letters.
- Contract tests run the real bridge addon inside an Odoo 19 container in CI ([25](../25-testing-strategy.md)).
