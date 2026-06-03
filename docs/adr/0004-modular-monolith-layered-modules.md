# ADR-0004: Modular Monolith with Layered Odoo Modules

**Date:** 2026-05-26  
**Status:** Accepted

## Context

The Security Suite must cover guard profiles, operations, attendance, leave, payroll, billing, fleet, equipment, documents, reporting, and mobile API. Options included:

- **Single large module** — simple install, but unmaintainable and non-reusable
- **Microservices** — independent deploy units, but massive operational overhead for a single security company
- **Layered Odoo modules** — vertical slices with explicit `depends` chains, one PostgreSQL database, one Odoo process

DogForce is a single-tenant deployment. Operational complexity does not justify distributed services.

## Decision

Implement a **modular monolith**: many Odoo modules in `custom_addons/`, each owning one business capability, connected by a **directed dependency graph** (no circular dependencies).

Core chain:

```text
security_base → security_operations → security_attendance → security_leave
  → security_l10n_na → security_payroll_core → …
```

Parallel branches attach at appropriate layers (equipment, fleet, mobile, documents).

## Consequences

### Positive

- Install only what a deployment needs; demo and mobile are optional branches
- Clear ownership boundaries per module; PRs stay scoped
- Single database transaction spans roster → attendance → payroll — no distributed consistency problems
- Standard Odoo upgrade path (`-u module`) per slice

### Negative

- Dependency order must be respected on install; wrong order fails loudly but requires documentation
- Deep chains mean a payroll bug may require understanding upstream attendance models
- All modules share Odoo process limits (memory, worker count) — no independent scaling

### Neutral

- Documented in [ARCHITECTURE.md](../../ARCHITECTURE.md) with Mermaid dependency graph
- `security_reporting` is view-only — depends on downstream modules for data, adds no models
