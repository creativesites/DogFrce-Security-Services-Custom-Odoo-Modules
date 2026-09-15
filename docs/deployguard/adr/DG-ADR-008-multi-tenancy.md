# DG-ADR-008 — Multi-Tenancy

- **Status:** Proposed
- **Date:** 2026-09-15
- **Related:** [15-multi-tenancy](../15-multi-tenancy.md), [DG-ADR-003](DG-ADR-003-database.md), [DG-ADR-004](DG-ADR-004-orm.md), [30-productization](../30-productization.md)

## Context

DogForce is the first tenant, but the Platform must serve many security companies without code changes. Each tenant has its own:

- DeployGuard ERP (Odoo) database, often on its own server;
- users, sites and roles;
- training catalogue and workflows;
- rules and AI context.

Expected scale is tens to low hundreds of tenants with fewer than 50 000 users in total (A-6), operated by a very small team (A-7). Customers will expect strong isolation, and some may later demand dedicated infrastructure.

On the Odoo side, database-per-tenant remains the model (ADR-0004, licensing plan).

## Decision

**Shared application, shared PostgreSQL database, row-level tenant isolation**, enforced in two layers:

1. **Application layer:** every request resolves a tenant context from the access token. Repositories only run inside `withTenant(tenantId)` ([DG-ADR-004](DG-ADR-004-orm.md)).
2. **Database layer:** PostgreSQL **RLS policies** on every tenant-owned table use `current_setting('app.tenant_id')`. The application role has no `BYPASSRLS`.

Additional decisions:

- **Tenant-owned tables:** `tenant_id NOT NULL`. Composite indexes lead with `tenant_id`. Foreign keys are validated within the tenant; cross-tenant FKs are prevented by including `tenant_id` in composite FKs for core aggregates.
- **Platform-global tables** (no `tenant_id`, no RLS; only platform roles can write): `tenant`, `platform_staff`, `ai_model_catalog`, `feature_flag_definition`, `domain_template_library` (published default content packs).
- **Secrets per tenant** (Odoo API key, webhook HMAC secret, bridge public keys, AI keys if tenant-supplied): envelope-encrypted with a per-tenant data key, wrapped by a platform master key in the hosting provider's KMS or secret manager. Never stored in plaintext columns.
- **Tenant configuration** is data, not code: locale, timezone, currency, theme font, working calendar, role catalogue customisations, exception rule parameters, expected-work definitions, notification policies, AI capability toggles and budgets.
- **Noisy-neighbour controls:** per-tenant rate limits (API and Odoo adapter), per-tenant job concurrency in pg-boss, per-tenant AI budget.
- **Background jobs** always carry `tenant_id` and set tenant context before touching data. Cross-tenant jobs (retention, platform metrics) run under a dedicated platform role, audited.
- **Isolation escape hatch (future):** a "dedicated cell" deployment (same code, separate database and worker pool) for enterprise customers who require it, selected by tenant routing at the edge. Not built until a customer needs it.

## Alternatives

| Option | Assessment |
|---|---|
| **Schema per tenant** | Stronger logical separation, but migrations × N schemas, connection-pool and search-path complexity, harder cross-tenant platform metrics. Little benefit over RLS at this scale. |
| **Database per tenant** | Strongest isolation and simple per-tenant restore, but the heaviest operations (N migrations, N backups, N pools, cross-tenant analytics via federation). Mirrors the Odoo model, whose operational pain we should not duplicate for the Platform. Reserved as the "dedicated cell" option. |
| **Application-only filtering (no RLS)** | One missing `where tenant_id` becomes a data breach. Not acceptable for employee data. |
| **Separate deployment per tenant** | Maximum isolation, unaffordable operationally for a small team. |

## Tradeoffs

| We gain | We accept |
|---|---|
| One migration path, one backup, simple platform analytics | Per-tenant point-in-time restore needs tooling (logical export/import by tenant) instead of a whole-DB restore |
| Defence in depth against query mistakes | RLS adds planning overhead; policies must be tested for every table |
| Cheap onboarding of new tenants (insert rows + configure) | "Noisy neighbour" risk managed with quotas rather than hard isolation |

## Consequences

- CI includes an **RLS conformance test** that fails if any table with `tenant_id` lacks an enabled and forced policy.
- A per-tenant **export/delete** tool is required before the second tenant (data portability, offboarding, privacy requests).
- Tenant routing: `app.<domain>` with the company code at sign-in; custom domains are FUT.
- DogForce is created as a normal tenant. **No DogForce-specific code paths are allowed** (NFR-11); DogForce differences live in the tenant configuration pack ([30](../30-productization.md)).
