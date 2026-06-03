# ADR-0001: Use Architecture Decision Records

**Date:** 2026-05-30  
**Status:** Accepted

## Context

The DogForce Security Suite spans 17 Odoo modules, a mobile app, Docker deployment, and Namibia-specific localization. Architectural choices (Community vs Enterprise, custom payroll, mobile auth) affect every contributor and the DogForce go-live. Without written records, decisions are buried in chat, PR comments, or tribal knowledge and get re-litigated.

## Decision

We will document significant architectural decisions as Markdown files in `docs/adr/`, numbered sequentially, each with **Context**, **Decision**, and **Consequences** sections.

## Consequences

### Positive

- New contributors understand *why* the codebase is structured as it is
- Future refactors can explicitly supersede an ADR rather than silently changing direction
- Client and audit conversations can reference stable decision documents

### Negative

- ADRs require maintenance when decisions change; stale ADRs are worse than none
- Not every small choice warrants an ADR — judgment is required

### Neutral

- ADRs complement but do not replace [ARCHITECTURE.md](../../ARCHITECTURE.md) (system view) and [docs/PROJECT_PLAN.md](../PROJECT_PLAN.md) (delivery plan)
