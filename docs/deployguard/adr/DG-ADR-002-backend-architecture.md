# DG-ADR-002 — Backend Architecture

- **Status:** Proposed
- **Date:** 2026-09-15
- **Related:** [19-backend-architecture](../19-backend-architecture.md), [24-api-design](../24-api-design.md), [DG-ADR-005](DG-ADR-005-monorepo.md), [DG-ADR-009](DG-ADR-009-event-architecture.md), [DG-ADR-015](DG-ADR-015-relationship-to-odoo-adrs.md)

## Context

The Platform backend owns tenants, sessions, authorisation, training, competencies, tasks, workflows, checklists, notifications, feedback and support, events, adoption analytics, exceptions, AI intelligence, audit, Odoo integration and configuration.

Its clients are:

- the Tauri desktop app;
- the web SPA;
- later, the Expo mobile app;
- Odoo bridge webhooks;
- possibly partner integrations.

The team is small (A-7); scale is modest (A-6); correctness, auditability and clear domain boundaries matter more than raw throughput. Existing DogForce architecture favours a modular monolith (ADR-0004).

Options considered:

1. building these capabilities as more Odoo addons;
2. a separate backend.

Option 1 fails the product goals:

- it cannot aggregate across tenants (one Odoo database per customer);
- it ties the Platform to each customer's Odoo upgrade and deployment cycle;
- it forces device identity, desktop sync and analytics workloads into Odoo workers;
- it would put employee-adoption data inside the HR system that also holds discipline records (PR-ADO-07).

## Decision

A **separate, TypeScript modular monolith** with two process types from one codebase:

- **`server`**: HTTP API (Fastify). Handles client requests and bridge webhooks.
- **`worker`**: background jobs (pg-boss on PostgreSQL). Event projections, adoption scoring, exception rules, escalations, notifications, Odoo polling, AI tasks, retention.

Stack:

| Concern | Choice |
|---|---|
| Runtime | **Node.js 24 LTS**, TypeScript strict, ESM |
| HTTP framework | **Fastify 5** (schema-first, fast, mature plugin model, good OpenTelemetry support) |
| Validation & contracts | **Zod** schemas in `packages/contracts` → Fastify type provider → **OpenAPI 3.1** generated → typed client (`packages/api-client`) |
| Data access | Drizzle + PostgreSQL 16 ([DG-ADR-003](DG-ADR-003-database.md), [DG-ADR-004](DG-ADR-004-orm.md)) |
| Jobs & scheduling | pg-boss (PostgreSQL-backed queues, cron schedules, retries, dead-letter) |
| Events | Transactional outbox + append-only `event` store ([DG-ADR-009](DG-ADR-009-event-architecture.md)) |
| Real-time to clients | Server-Sent Events for inbox/notification updates; polling fallback |
| AuthN/Z | Platform tokens per [DG-ADR-007](DG-ADR-007-authentication.md); authorisation policy functions per module (`can(actor, action, resource)`) with scope evaluation |
| Rules | Pure functions in `packages/domain` (expected work, scoring, exception rules), executed by the worker |

Module boundaries (details in [19](../19-backend-architecture.md)):

`identity` · `tenancy` · `odoo-sync` · `work` · `training` · `competency` · `adoption` · `exceptions` · `notifications` · `feedback-support` · `knowledge` · `analytics` · `intelligence` · `audit` · `admin`

Each module owns its tables, exposes a public interface (commands and queries) and publishes domain events. Modules never write another module's tables.

## Alternatives

| Option | Assessment |
|---|---|
| **More Odoo addons (Python, inside each tenant's Odoo)** | Rejected (see Context). Odoo remains the ERP; bridge addons are the only Platform code inside Odoo. |
| **NestJS** | Solid, but decorator and DI heaviness adds ceremony; module boundaries can be enforced without it. Reasonable if the team grows. |
| **Express** | Older ergonomics, no schema-first typing, weaker performance and plugin encapsulation. |
| **Hono** | Excellent and lightweight; less mature ecosystem for OpenAPI plus complex plugin lifecycles at the time of writing. Close alternative. |
| **tRPC-only API** | Great TS-to-TS DX, but Odoo webhooks, Rust native code and future partners need a language-neutral contract. Rejected as the primary API style. |
| **Python (FastAPI)** | Shares language with Odoo addons, but loses end-to-end type sharing with the React/Tauri clients; two backends in Python with different frameworks invites confusion with Odoo code. |
| **Go / .NET** | Strong runtimes, but a third language and no shared contracts with the UI. |
| **Microservices** | Premature: deployment, tracing and data-consistency costs with no scaling need (A-6). |

## Tradeoffs

| We gain | We accept |
|---|---|
| One deployable codebase, shared types end-to-end, simple operations | Discipline is required to keep module boundaries (lint + review) |
| Horizontal scaling by adding server/worker replicas | Long-running CPU-heavy analytics could contend with the API; mitigated by separate worker processes and later a read replica |
| OpenAPI contract usable from Python (bridge), Rust and TS | Generated-client pipeline to maintain |

## Consequences

- **Deployment:** two container entrypoints from one image, `node dist/server.js` and `node dist/worker.js` ([DG-ADR-013](DG-ADR-013-deployment.md)).
- **Extraction path:** if a module ever needs extraction (e.g. `intelligence` for GPU/latency reasons), its public interface and event contracts are the seam. No extraction is planned.
- **Future Odoo AI option:** Odoo's `security_ai_engine` may call Platform intelligence endpoints later (OQ-3). That is an optional client, not a dependency.
