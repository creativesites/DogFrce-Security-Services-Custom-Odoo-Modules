# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records for the DogForce Security Suite — significant technical choices, the context that drove them, and their consequences.

ADRs follow the format described in [ADR-0001](0001-use-architecture-decision-records.md).

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-use-architecture-decision-records.md) | Use Architecture Decision Records | Accepted |
| [0002](0002-odoo-community-over-enterprise.md) | Build on Odoo Community, not Enterprise | Accepted |
| [0003](0003-odoo-19-target-version.md) | Target Odoo 19 Community | Accepted |
| [0004](0004-modular-monolith-layered-modules.md) | Modular monolith with layered Odoo modules | Accepted |
| [0005](0005-country-neutral-core-localization-pack.md) | Country-neutral core + localization pack | Accepted |
| [0006](0006-custom-payroll-engine.md) | Custom payroll engine in security_payroll_core | Accepted |
| [0007](0007-custom-billing-without-accounting-app.md) | Custom billing model without Odoo Accounting | Accepted |
| [0008](0008-odoo-session-auth-for-mobile.md) | Odoo session authentication for mobile | Accepted |
| [0009](0009-thin-mobile-client-rest-api.md) | Thin Expo mobile client with REST API layer | Accepted |
| [0010](0010-docker-compose-runtime.md) | Docker Compose for dev and deployment | Accepted |
| [0011](0011-configuration-over-code.md) | Configuration over code for business rules | Accepted |
| [0012](0012-manual-roster-before-auto-roster.md) | Manual roster MVP before auto-rostering | Accepted |
| [0013](0013-model-inherit-cross-module-integration.md) | Model extension for cross-module integration | Accepted |
| [0014](0014-isolated-demo-data-module.md) | Isolated demo data in security_demo_data | Accepted |
| [0015](0015-test-driven-payroll-statutory-logic.md) | Test-driven payroll and statutory logic | Accepted |

## Related documentation

- [ARCHITECTURE.md](../../ARCHITECTURE.md) — system design overview
- [docs/PROJECT_PLAN.md](../PROJECT_PLAN.md) — original architecture principles
- [DEPLOYMENT.md](../../DEPLOYMENT.md) — how ADR choices affect deployment

## Adding a new ADR

1. Copy the template from [0001](0001-use-architecture-decision-records.md)
2. Number sequentially (`0015`, `0016`, …)
3. Set status: `Proposed` → `Accepted` → `Deprecated` / `Superseded`
4. Update this index
5. Link from PR description when the decision is made
