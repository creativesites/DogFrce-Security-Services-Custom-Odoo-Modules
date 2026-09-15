# DG-ADR-003 — Database

- **Status:** Proposed
- **Date:** 2026-09-15
- **Related:** [14-data-model](../14-data-model.md), [15-multi-tenancy](../15-multi-tenancy.md), [DG-ADR-004](DG-ADR-004-orm.md), [DG-ADR-008](DG-ADR-008-multi-tenancy.md), [DG-ADR-009](DG-ADR-009-event-architecture.md)

## Context

The Platform stores relational, tenant-scoped operational data: users, roles, training, tasks, exceptions and audit. It also stores an append-only event stream used for adoption scoring and replay, JSON payloads from Odoo, and must support full-text search, row-level tenant isolation and point-in-time recovery.

The team already operates PostgreSQL 16 for DeployGuard ERP (production runs 16.14) and has backup tooling built around it (WAL archiving, R2 offsite in `security_backup_vault`).

## Decision

Use **PostgreSQL 16** (managed where the hosting decision allows, OQ-1) as the single primary datastore for the Platform, in its **own database cluster, separate from any tenant's Odoo database**.

Features we rely on:

- **Row-Level Security** for tenant isolation (defence in depth under application checks).
- **JSONB** for event `data`, Odoo payload snapshots and configurable template definitions.
- **Declarative partitioning** (monthly range) for `event`, `audit_log` and `notification_delivery`.
- **Full-text search** (`tsvector`, `pg_trgm`) for the command palette and knowledge base.
- **`FOR UPDATE SKIP LOCKED`** job queue via pg-boss ([DG-ADR-009](DG-ADR-009-event-architecture.md)).
- **Logical backups + PITR** (WAL) with offsite encrypted copies.

IDs are **UUIDv7**, generated in the application (time-ordered, index-friendly, safe to create offline on clients).

## Alternatives

| Option | Why not (now) |
|---|---|
| Reuse each tenant's Odoo PostgreSQL | Couples Platform data to ERP upgrades and backups; impossible to aggregate across tenants; violates data-ownership boundaries. |
| MySQL / MariaDB | No RLS; weaker JSON and partitioning ergonomics; no operational familiarity in the team. |
| MongoDB | Relational integrity is central (assignments, attempts, competencies); a second operational technology with no benefit. |
| PostgreSQL + ClickHouse/Timescale for events | Premature. Expected event volume (A-6) fits partitioned PostgreSQL for years. Revisit when the `event` table exceeds ~500 M rows or analytics queries breach SLOs. |
| PostgreSQL 17 | Acceptable. 16 is chosen for parity with existing tooling and `pg_dump` versions; upgrade to 17+ is a routine operation later. |

## Tradeoffs

| We gain | We accept |
|---|---|
| One datastore to run, back up, secure and reason about | Analytics at very large scale will eventually need an OLAP store |
| RLS-enforced isolation | RLS must be tested explicitly; connection pooling must propagate tenant context per transaction |
| Same technology as DeployGuard ERP | — |

## Consequences

- Every tenant-owned table has `tenant_id uuid not null` and an RLS policy `tenant_id = current_setting('app.tenant_id')::uuid` ([15](../15-multi-tenancy.md) §3).
- The application connects as a non-owner role without `BYPASSRLS`. Migrations run as a separate owner role.
- Transaction-mode connection pooling (e.g. PgBouncer, or the provider's pooler) is compatible because tenant context is set with `SET LOCAL` inside each transaction.
- Retention jobs drop or detach old partitions according to [23](../23-audit-system.md) and OQ-14.
- Restore drills are monthly ([26](../26-deployment-strategy.md)).
