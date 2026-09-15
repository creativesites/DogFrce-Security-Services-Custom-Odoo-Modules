# DG-ADR-015 — Relationship to Existing DeployGuard ERP ADRs

- **Status:** Proposed
- **Date:** 2026-09-15
- **Related:** [`docs/adr/`](../../adr/) (0001–0015), [DG-ADR-002](DG-ADR-002-backend-architecture.md), [DG-ADR-007](DG-ADR-007-authentication.md), [DG-ADR-019](DG-ADR-019-product-naming.md)

## Context

This repository already contains 15 accepted ADRs for the Odoo-based system. Some appear to contradict the DeployGuard Platform plan (C-1 in [32](../32-open-questions.md)):

- ADR-0004: modular monolith, "no microservices / no event bus";
- ADR-0008: Odoo session auth, separate auth service rejected;
- ADR-0009: thin clients.

Without an explicit statement, future contributors would not know which rules govern which codebase.

## Decision

1. **Scope.** The `docs/adr/0001–0015` ADRs govern **DeployGuard ERP** (the Odoo `security_*` addons, DeployGuard Mobile and their deployment). **DG-ADRs** govern **DeployGuard Platform** (backend, desktop, web) and the **bridge addons** where they touch Platform contracts.
2. **No existing ADR is superseded.** Several are extended or explicitly scoped, as tabulated below.
3. **Namespace.** DG-ADRs live in `docs/deployguard/adr/` with the `DG-` prefix, so the two sequences never collide.

| Existing ADR | Effect on the Platform | Status |
|---|---|---|
| 0001 Use ADRs | Adopted; DG-ADRs follow the same practice with Context / Decision / Alternatives / Tradeoffs / Consequences. | Applies |
| 0002 Odoo Community over Enterprise | ERP decision. The Platform only needs Odoo 19 JSON-2 and the bridge addons, which work on Community. | Applies to ERP |
| 0003 Odoo 19 target | The Platform requires Odoo 19+ (A-5). | Applies |
| 0004 Modular monolith, single-tenant | Governs ERP. The Platform is **also a modular monolith** (DG-ADR-002), in a separate product layer with multi-tenancy (DG-ADR-008). "No event bus" governs ERP; the Platform's PostgreSQL event log is internal to the Platform monolith (DG-ADR-009), not a distributed bus. | Scoped |
| 0005 Country-neutral core + localisation packs | Adopted as a principle: tenant configuration packs, no country logic in core modules. | Extended |
| 0006 Custom payroll | ERP only; the Platform never computes payroll. | Not applicable |
| 0007 Custom billing without Accounting | ERP only; already superseded in practice by the Aug-2026 accounting decision (C-9). | Not applicable |
| 0008 Odoo session auth for mobile | **Extended** by DG-ADR-007: Odoo credentials remain the identity source for all tenant users. The Platform issues its own device-bound tokens only after verifying an Odoo-signed assertion. Mobile migrates to the bridge flow in V2. | Extended |
| 0009 Thin Expo client | Applies to mobile and equally to the desktop/web apps: no business rules in clients. Business rules live in the Platform backend (`packages/domain` executed server-side). | Applies |
| 0010 Docker Compose | ERP deployment. The Platform uses containers (compose for local development) with its own hosting decision (DG-ADR-013). | Scoped |
| 0011 Configuration over code | Adopted for tenant differences (NFR-11). | Extended |
| 0012 Manual roster before auto | ERP only. | Not applicable |
| 0013 `_inherit` integration | Bridge addons follow it: they extend ERP models through `_inherit` and auto-install glue addons (DG-ADR-018). | Applies to bridges |
| 0014 Isolated demo data | Adopted: Platform demo tenants are separate tenants with synthetic data, never mixed with production tenants. | Extended |
| 0015 Test-driven payroll | Adopted in spirit: scoring, expected-work and exception rules are test-driven with fixtures (DG-ADR-009, [25](../25-testing-strategy.md)). | Extended |

## Alternatives

- **Supersede ADR-0004/0008/0009:** misleading; they remain correct for the ERP.
- **Renumber everything into one sequence:** churns links in existing docs and commits.
- **Keep Platform decisions undocumented relative to the ERP:** guarantees confusion.

## Tradeoffs

Two ADR sequences to read. This is mitigated by [33-adr-index](../33-adr-index.md) linking both, and by this scoping table.

## Consequences

- `docs/adr/README.md` should gain a one-line pointer to `docs/deployguard/adr/` (housekeeping task, not done in this planning pass).
- Any future ERP ADR that affects bridge contracts must reference the relevant DG-ADR, and vice versa.
