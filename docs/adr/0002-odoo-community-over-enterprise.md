# ADR-0002: Build on Odoo Community, Not Enterprise

**Date:** 2026-05-26  
**Status:** Accepted

## Context

DogForce Security Services currently runs **Odoo Enterprise** in production. The functional specification requires payroll, invoicing, bank reconciliation, approvals, and reporting — areas where Enterprise provides mature apps (Payroll, Accounting, Planning, Sign).

The project has two goals:

1. Deliver a working system for DogForce (Namibia)
2. Produce a **reusable Security Suite** licensable and adaptable to other countries without Enterprise lock-in

Enterprise licensing cost, vendor dependency, and the inability to redistribute proprietary modules conflict with the reusable-suite goal. Building directly on Enterprise payroll/accounting also couples security-domain logic to apps that may differ between Community and Enterprise.

## Decision

Develop the Security Suite on **Odoo Community Edition**. Do not declare dependencies on Enterprise-only modules in reusable core modules. Treat Enterprise as a **deployment option** for DogForce production, with integration points isolated for later (e.g. bridge to `account.move`, Enterprise Payroll adapter).

Pre-engagement development in this repository intentionally uses Community via Docker (`odoo:19.0`).

## Consequences

### Positive

- Reusable modules can be shared, demoed, and sold without Enterprise licenses
- Security-domain logic (roster, attendance, guard profiles) stays independent of accounting/payroll app editions
- Clear forcing function to own Namibia payroll and billing rules in custom code with tests

### Negative

- Must build or integrate Community/OCA equivalents for payroll, GL, bank reconciliation, 2FA, and advanced approvals
- DogForce production cutover may require a **Community → Enterprise migration path** or parallel run if they retain Enterprise
- Some specification items (bank statement import, full reconciliation audit) are deferred or simplified

### Neutral

- README and DEPLOYMENT.md document the Enterprise vs Community split explicitly
- Owner KPI endpoint optionally reads `account.move` if Accounting is installed — optional, not required
