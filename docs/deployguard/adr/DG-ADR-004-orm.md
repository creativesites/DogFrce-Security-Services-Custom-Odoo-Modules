# DG-ADR-004 — ORM / Data Access

- **Status:** Proposed
- **Date:** 2026-09-15
- **Related:** [DG-ADR-003](DG-ADR-003-database.md), [DG-ADR-008](DG-ADR-008-multi-tenancy.md), [19-backend-architecture](../19-backend-architecture.md)

## Context

The TypeScript backend needs type-safe data access for PostgreSQL with:

- first-class migrations, including raw SQL for RLS policies, partitions and triggers;
- per-transaction tenant context (`SET LOCAL app.tenant_id`);
- predictable SQL for performance-sensitive rollups (adoption scoring);
- no heavy runtime.

The team is small and values explicitness over magic.

## Decision

Use **Drizzle ORM** with **drizzle-kit** for schema-driven migrations. Raw SQL migration files are allowed and expected for:

- RLS policies;
- partition management;
- functions and triggers.

Data access conventions:

- All queries run through a `withTenant(tenantId, fn)` helper. It opens a transaction, sets `SET LOCAL app.tenant_id` and `SET LOCAL app.actor_id`, and passes a typed `tx` handle. Repositories never accept a bare connection.
- Each backend module owns its tables and exposes repositories only through its module interface ([19](../19-backend-architecture.md) §3). Cross-module joins go through read models or explicit query services, not ad-hoc imports of another module's tables.
- Complex analytical SQL (scoring, rollups) is written as reviewed SQL in the `adoption` and `analytics` modules using Drizzle's `sql` template, with tests against a real PostgreSQL.

## Alternatives

| Option | Assessment |
|---|---|
| **Prisma** | Excellent DX and schema tooling. For this project: RLS needs extension or transaction workarounds for tenant context; migration flexibility for policies and partitions is weaker; heavier generated client and historically a separate query-engine runtime. Rejected for friction with RLS-centric tenancy. |
| **Kysely** | Very good type-safe query builder, close to SQL. No schema-as-code or migration generation; we would hand-maintain types or add codegen. A close second; a reasonable fallback. |
| **TypeORM / MikroORM** | Decorator/active-record patterns and unit-of-work magic conflict with explicit transaction control; weaker type inference. |
| **Raw `pg` + SQL files** | Maximum control, but loses schema typing and increases boilerplate for a small team. |

## Tradeoffs

| We gain | We accept |
|---|---|
| Schema in TypeScript, shared inferred types (with Zod via `drizzle-zod` at API boundaries) | Drizzle is younger than Prisma; we pin versions and keep usage mainstream |
| SQL-transparent queries, easy RLS and raw SQL | Relational query API is less "magical"; some joins are written explicitly |
| No native engine binary; fast cold start for workers | Migration generation must be reviewed by a human (RLS and partitions are hand-written) |

## Consequences

- `apps/api/src/db/schema/<module>.ts` per module; `apps/api/drizzle/` holds generated plus hand-written migrations, applied in CI against an ephemeral PostgreSQL.
- Integration tests assert RLS: queries under tenant A must return zero rows of tenant B, even with a deliberately missing `where tenant_id` clause ([25](../25-testing-strategy.md)).
- API contracts remain Zod-first ([DG-ADR-002](DG-ADR-002-backend-architecture.md)). DB types never leak directly into public API types.
