# 33 — ADR Index

> Status: Living · Owner: Platform architecture
>
> Two sequences exist. `docs/adr/0001–0015` govern **DeployGuard ERP** (Odoo). `docs/deployguard/adr/DG-ADR-*` govern **DeployGuard Platform** and the bridge contracts. [DG-ADR-015](adr/DG-ADR-015-relationship-to-odoo-adrs.md) explains how they relate; no existing ERP ADR is superseded.

---

## 1. Platform ADRs

| ID | Title | Status | Decision in one line |
|---|---|---|---|
| [DG-ADR-001](adr/DG-ADR-001-desktop-framework.md) | Desktop framework | Proposed | Tauri v2 + Rust + React/TS; Rust layer stays thin; Electron is the documented fallback |
| [DG-ADR-002](adr/DG-ADR-002-backend-architecture.md) | Backend architecture | Proposed | Separate TypeScript modular monolith (Fastify + Zod → OpenAPI), `server` + `worker` from one codebase |
| [DG-ADR-003](adr/DG-ADR-003-database.md) | Database | Proposed | PostgreSQL 16 as the single datastore: RLS, JSONB, partitioning, FTS, PITR |
| [DG-ADR-004](adr/DG-ADR-004-orm.md) | ORM / data access | Proposed | Drizzle + raw SQL for policies and partitions; all access through `withTenant()` |
| [DG-ADR-005](adr/DG-ADR-005-monorepo.md) | Repository strategy | Proposed | New `deployguard-platform` pnpm/Turborepo monorepo; bridge addons stay in the ERP repo; ≤ 8 packages |
| [DG-ADR-006](adr/DG-ADR-006-odoo-integration.md) | Odoo integration | Proposed | Hybrid push (signed webhooks) + pull (watermarked polling) over JSON-2 with a facade model |
| [DG-ADR-007](adr/DG-ADR-007-authentication.md) | Authentication & single login | **Accepted in principle (R-7)** | One login using Odoo credentials + TOTP; signed assertion → Platform device-bound tokens; brokered SSO tickets to open Odoo |
| [DG-ADR-008](adr/DG-ADR-008-multi-tenancy.md) | Multi-tenancy | Proposed | Shared database, `tenant_id` + forced RLS; dedicated cells reserved for later |
| [DG-ADR-009](adr/DG-ADR-009-event-architecture.md) | Event architecture | Proposed | PostgreSQL event log + transactional outbox + pg-boss; no Kafka; replayable |
| [DG-ADR-010](adr/DG-ADR-010-ai-architecture.md) | AI architecture | Proposed (default **Accepted, R-4**) | `AIProvider` abstraction, **Gemini default**, capability registry, controlled context, citation validation, human approval |
| [DG-ADR-011](adr/DG-ADR-011-offline-architecture.md) | Offline architecture | Proposed | Desktop-only minimum offline set; command outbox with conflict rules; never fake success |
| [DG-ADR-012](adr/DG-ADR-012-notifications.md) | Notifications | Proposed | One notifications module, policy engine, channel adapters; official WhatsApp API later, not Baileys |
| [DG-ADR-013](adr/DG-ADR-013-deployment.md) | Deployment & hosting | Proposed (pending OQ-1/11) | Containers + managed PostgreSQL in a South African region, separate from the ERP host; Terraform; signed desktop channels |
| [DG-ADR-014](adr/DG-ADR-014-observability.md) | Observability | Proposed | OpenTelemetry + Sentry, privacy-scrubbed; domain SLIs; reference codes for support |
| [DG-ADR-015](adr/DG-ADR-015-relationship-to-odoo-adrs.md) | Relationship to ERP ADRs | Proposed | Scopes each existing ADR; ADR-0008 extended, none superseded |
| [DG-ADR-016](adr/DG-ADR-016-web-framework.md) | Web framework | Proposed | Vite + React SPA (TanStack Router/Query) shared with Tauri; Next.js only for marketing |
| [DG-ADR-017](adr/DG-ADR-017-design-system-and-shell-parity.md) | Design system & shell parity | **Accepted in principle (R-3)** | Verbatim token port with CI drift check; React port of `security_shell`; lint-enforced hard rules |
| [DG-ADR-018](adr/DG-ADR-018-odoo-bridge-addons.md) | Odoo bridge addons | **Accepted in principle (R-2)** | `security_deployguard_bridge` core + auto-install domain bridges; outbox; facade; bus subscriber registry (fixes D-4) |
| [DG-ADR-019](adr/DG-ADR-019-product-naming.md) | Product naming & boundaries | Proposed (OQ-2) | DeployGuard OS = family; ERP = Odoo suite; Platform = backend + desktop + web |

## 2. Existing ERP ADRs and their effect here

| ERP ADR | Effect on the Platform |
|---|---|
| 0001 Use ADRs | Adopted |
| 0002 Community over Enterprise | ERP-scoped; Platform works with either |
| 0003 Odoo 19 target | Applies (Platform requires Odoo 19+) |
| 0004 Modular monolith, single-tenant | ERP-scoped; Platform is its own monolith with multi-tenancy |
| 0005 Country-neutral core + localisation packs | Extended as tenant configuration packs |
| 0006 Custom payroll · 0007 Custom billing · 0012 Manual roster | Not applicable |
| **0008 Odoo session auth for mobile** | **Extended** by DG-ADR-007 (Odoo remains the identity source) |
| 0009 Thin Expo client | Applies to all Platform clients |
| 0010 Docker Compose | ERP-scoped; Platform hosting in DG-ADR-013 |
| 0011 Configuration over code | Extended (NFR-11) |
| 0013 `_inherit` integration | Applies to bridge addons |
| 0014 Isolated demo data | Extended to demo tenants |
| 0015 Test-driven payroll | Extended to rules and scoring |

## 3. Writing a new DG-ADR

1. Copy the section structure: **Context · Decision · Alternatives · Tradeoffs · Consequences** (plus Status, Date, Related).
2. Number sequentially (`DG-ADR-020…`), filename `DG-ADR-0NN-short-slug.md`.
3. Record the *reason*, not only the choice; include a revisit trigger where relevant.
4. Add a row to §1 and link it from affected documents.
5. Status values: `Proposed` → `Accepted` → (`Superseded by DG-ADR-0NN` | `Deprecated`). A product decision recorded in [32](32-open-questions.md) §1 makes an ADR "Accepted in principle" even while mechanics remain proposed.
