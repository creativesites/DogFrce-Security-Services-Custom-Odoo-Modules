# 19 — Backend Architecture

> Status: Draft · Owner: Platform engineering · Decisions: [DG-ADR-002](adr/DG-ADR-002-backend-architecture.md), [DG-ADR-004](adr/DG-ADR-004-orm.md), [DG-ADR-009](adr/DG-ADR-009-event-architecture.md)

---

## 1. Shape

One TypeScript codebase, two entrypoints:

```
apps/api
├── src/server.ts        Fastify HTTP (clients, bridge webhooks, SSE)
├── src/worker.ts        pg-boss consumers, event dispatcher, schedules
├── src/platform/        http, auth, db, events, jobs, files, telemetry, config, policy
└── src/modules/         the domain modules (below)
```

Shared, dependency-free rules live in `packages/domain` so they can be unit-tested and reused by tests and tooling.

## 2. Modules

| Module | Responsibility | Key events emitted |
|---|---|---|
| `tenancy` | Tenants, configuration, feature flags, quotas | `tenant.configured` |
| `identity` | Sign-in exchange, sessions, devices, roles, scopes, reporting lines, identity links | `identity.*` |
| `odoo-sync` | Connection, webhooks, polling, projections, watermarks, commands | `odoo.*` |
| `work` | Templates, schedules, tasks, checklist instances, verification | `work.*` |
| `training` | Programs, courses, versions, assignments, attempts, progress | `training.*` |
| `competency` | Framework, requirements, evidence, status, Platform certifications | `competency.*` |
| `adoption` | Expected work, snapshots, factors, abandonment, check-ins | `adoption.*` |
| `exceptions` | Rules, lifecycle, evidence, escalation policies | `exception.*` |
| `notifications` | Intents, policy engine, channel adapters, digests | `notification.*` |
| `feedback-support` | Feedback capture, support requests and messages | `feedback.*`, `support.*` |
| `knowledge` | Articles, versions, targeting, search | `knowledge.*` |
| `analytics` | Rollups, metric definitions, query services | — |
| `intelligence` | Capability registry, context assembly, provider calls, insights and recommendations | `ai.*` |
| `audit` | Append-only audit writing and querying | — |
| `admin` | Tenant admin operations, health, exports | — |

**Boundary rules** (lint-enforced):

- a module may import another only through its `index.ts` (commands and queries);
- no module reads another module's tables;
- cross-module reactions happen via events;
- `packages/domain` imports nothing from `apps/api`.

## 3. Module anatomy

```
modules/work/
├── index.ts           public commands + queries (the only export surface)
├── commands/          createTask, submitChecklist, verifyInstance …
├── queries/           listMyWork, getInstance …
├── policy.ts          can(actor, action, resource)
├── events.ts          typed emitters (contracts-backed)
├── subscribers.ts     reactions to other modules' events
├── schedules.ts       recurrence materialisation, overdue detection
├── repo/              Drizzle repositories (tenant-scoped)
└── schema.ts          Drizzle tables for this module
```

Every command follows the same skeleton: authorise → validate → load → apply domain rule (`packages/domain`) → persist + emit event(s) + audit, all in one transaction.

## 4. Request lifecycle

```
HTTP → auth plugin (verify token, load actor, tenant)
     → rate limit (tenant/user/endpoint)
     → schema validation (Zod)
     → policy check
     → withTenant(tx) { command/query }
     → response (+ correlation id, reference code on errors)
```

Errors map to a stable taxonomy ([24](24-api-design.md) §5). The API never returns a raw database or provider error.

## 5. Background work

| Type | Examples | Mechanism |
|---|---|---|
| Event consumers | projections, adoption fulfilment, exception evaluation, notification intents, work auto-complete | dispatcher reading `event` by `global_seq` with per-consumer checkpoints |
| Scheduled | nightly adoption snapshots (tenant timezone), expected-work materialisation, overdue sweeps, digest sends, Odoo polling, retention, AI briefs (V1) | pg-boss cron per tenant |
| Deferred | email send, AI call, file scan, webhook retry | pg-boss queues with retries and dead letters |

Rules: every job is idempotent, carries `tenant_id` and `correlation_id`, has a timeout and a maximum attempt count, and reports metrics.

## 6. Determinism and rule versioning

- Deterministic logic (expected work, scoring, exception conditions, recurrence, escalation timing) lives in `packages/domain` as pure functions with fixture tests.
- Every derived record stores the `rule_version` that produced it, so historical numbers remain explainable after logic changes; replays can recompute a window with a stated version.
- AI never participates in these computations ([11](11-ai-intelligence.md) §2).

## 7. Real-time

- SSE endpoint `/v1/stream` per authenticated session; server pushes inbox counts, new notifications, sync status, and exception updates within the caller's scope.
- Backpressure: coalesced updates at most every 2 s per client.
- Fallback: polling with ETag on the notification and inbox summary endpoints.

## 8. Configuration

- Environment variables for infrastructure (DB URL, KMS key ids, provider endpoints).
- Tenant-level behaviour is database configuration, never environment variables.
- Feature flags: platform-level definitions, tenant-level values, evaluated server-side and exposed to clients through a capabilities endpoint.

## 9. Failure and degradation

| Dependency down | Behaviour |
|---|---|
| Tenant Odoo | Projections go stale with banners; Odoo-dependent exception rules pause; sign-in for that tenant fails with a clear message (existing sessions keep working) |
| Email provider | Queue and retry; escalation falls back to in-app and desktop channels; ops alert |
| AI provider | Capability marked degraded; deterministic features unaffected; queued runs retried |
| Object storage | Evidence uploads queue client-side; UI states "pending upload" |
| Database | API returns 503 with reference codes; desktop continues in offline mode |
