# 15 — Multi-Tenancy

> Status: Draft · Owner: Platform architecture · Decision: [DG-ADR-008](adr/DG-ADR-008-multi-tenancy.md)

---

## 1. Tenant model

A **tenant** is one security company using DeployGuard OS. DogForce is tenant #1 and gets **no special code paths** (NFR-11).

| Concept | Scope |
|---|---|
| Tenant | Company: users, sites, content, rules, connection, AI budget |
| Odoo connection | One per tenant in MVP; the model allows several (e.g. a group with two ERP databases) |
| Sites / teams | Within a tenant; sites are ERP projections, teams are Platform-owned |
| Users | Belong to exactly one tenant (a person working for two customers gets two accounts) |
| Platform staff | Outside tenants; access is explicit and audited |

## 2. Lifecycle

| Stage | Steps |
|---|---|
| **Create** | Platform admin creates tenant (name, company code, locale, timezone, currency), seeds catalogue roles, default exception rules, default templates and the standard "Using DeployGuard ERP" course pack |
| **Connect** | Install bridge addons, exchange keys, run connection test, initial sync ([12](12-odoo-integration.md) §2) |
| **Configure** | Roles and scopes, reporting lines, expected-work definitions, notification policies, branding font, AI toggles |
| **Onboard users** | Enable DeployGuard access per Odoo user; users sign in and links are created |
| **Operate** | Normal use; health monitoring; quotas |
| **Suspend** | Sign-in blocked, jobs paused, data retained (non-payment or customer request) |
| **Offboard** | Full export (JSON + files), then deletion within the agreed window; audit retained per policy |

## 3. Isolation mechanics

Every tenant-owned table:

```sql
ALTER TABLE work_task ADD COLUMN tenant_id uuid NOT NULL;
ALTER TABLE work_task ENABLE ROW LEVEL SECURITY;
ALTER TABLE work_task FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON work_task
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE INDEX ON work_task (tenant_id, due_at) WHERE status IN ('open','in_progress');
```

Request flow:

1. Access token → `tenant_id`, `user_id`.
2. `withTenant(tenantId, actorId, fn)` opens a transaction and runs
   `SET LOCAL app.tenant_id = $1; SET LOCAL app.actor_id = $2;`
3. All repository calls use that transaction handle.
4. The application role is not `BYPASSRLS`; migrations run as a separate owner role.

Guarantees tested in CI ([25](25-testing-strategy.md)):

- every table with `tenant_id` has RLS enabled **and forced**;
- a deliberately unfiltered query under tenant A returns no tenant B rows;
- cross-tenant foreign keys are impossible (composite FKs include `tenant_id`);
- background jobs without tenant context cannot read tenant tables.

**Platform-global tables** (no RLS, platform role only): `tenant`, `platform_staff`, `ai_model_catalog`, `feature_flag_definition`, `template_library` (published default content), `event_type_registry`.

## 4. Tenant configuration (data, never code)

| Area | Examples |
|---|---|
| Identity | Role catalogue overrides, custom roles, MFA policy, session lifetimes |
| Operations | Expected-work definitions, checklist/task templates, verification rules, SLA targets |
| Exceptions | Enabled rules, thresholds, owners, escalation policies, quiet hours |
| Training | Course packs, mandatory assignments per role, pass marks, approver (R-8) |
| Branding | Theme font (mirrors ERP theme), tenant display name, logo for emails/digests |
| Localisation | Locale, timezone, currency, week start, public-holiday source (ERP) |
| Integration | Odoo connection, sync intervals, allowlisted commands |
| AI | Capabilities enabled, provider/model per capability, monthly budget |
| Privacy | Retention overrides, adoption-visibility policy (OQ-13), monitoring-notice version |

Configuration is versioned; changes are audited with before/after digests. A tenant's configuration can be **exported as a pack** and imported into another tenant ([30](30-productization.md)).

## 5. Secrets per tenant

- Envelope encryption: each tenant has a data key, encrypted by a platform master key in the hosting KMS. Ciphertext is stored in `tenant_secret` rows; plaintext exists only in process memory.
- Held per tenant: Odoo integration API key, webhook HMAC secret (current + previous during rotation), bridge public keys (by `kid`), email sender credentials if tenant-specific, AI keys if tenant-supplied.
- Rotation procedures and windows are documented in [16](16-security-architecture.md) §6.
- Secrets never appear in logs, events, AI context, or API responses (write-only fields).

## 6. Per-tenant runtime behaviour

| Aspect | Mechanism |
|---|---|
| Jobs | Every job payload carries `tenant_id`; the worker sets tenant context before touching data |
| Fairness | Per-tenant concurrency caps in pg-boss; a large tenant's nightly scoring cannot starve others |
| Rate limits | API limits per tenant and per user; Odoo adapter limit per connection |
| AI budget | Monthly cost cap per tenant and per capability; exceeding it disables non-critical capabilities and alerts the tenant admin |
| Scheduling | Nightly jobs run in the tenant's timezone (e.g. adoption snapshots after end of day) |
| Search & AI context | Queries always filtered by `tenant_id`; embeddings (V1) are stored per tenant and never retrieved across tenants |

## 7. Platform staff access

- No implicit access to tenant data.
- **Break-glass**: a platform admin requests time-boxed access (default 60 min) with a reason and, where possible, tenant-admin approval. The grant is logged, notified to the tenant admin, and expires automatically ([16](16-security-architecture.md) §5, [23](23-audit-system.md)).
- Support tooling prefers **metadata and health views** (counts, lags, error codes) over content.

## 8. Data portability & erasure

- **Export** (tenant admin or platform admin on request): JSON per entity plus files, streamed to a signed archive; includes derived data but flags it as reproducible.
- **Erasure of a person** (privacy request): Platform-owned personal records are deleted or pseudonymised; events in retained partitions have `actor.id`/`subject.id` pseudonymised; ERP records are out of scope (handled in Odoo).
- **Tenant deletion**: rows are deleted by `tenant_id` in dependency order, files removed from object storage, secrets destroyed in KMS, and a deletion certificate recorded in the platform audit.

## 9. Scale expectations & escape hatch

| Horizon | Expectation |
|---|---|
| Pilot (DogForce) | 1 tenant, ~15–40 users, ~30 sites, ~210 employees projected |
| Year 1 | < 10 tenants, < 1 000 users |
| Year 3 (A-6) | Tens to low hundreds of tenants, < 50 000 users |

If a customer requires physical isolation or a specific residency, deploy a **dedicated cell**: same code and version, separate database, worker pool and storage bucket, selected by tenant routing. No code fork. Not built until a paying requirement exists.
