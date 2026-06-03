# ADR-0003: Target Odoo 19 Community

**Date:** 2026-05-26  
**Status:** Accepted

## Context

Odoo 18 and 19 are both supported Community versions. Odoo 19 (September 2025) offers a longer support window (planned until September 2028). Odoo 18 may have more mature OCA modules for some accounting/payroll gaps.

DogForce's production Enterprise version was assumed to be on the latest major release. Module manifests, security groups (privilege-based groups in Odoo 19), and Docker defaults need a single target version to avoid compatibility drift.

## Decision

Standardize development on **Odoo 19.0 Community**:

- Docker image: `odoo:19.0` (`deploy/docker-compose.yml`)
- Module version prefix: `19.0.x.y.z` in all `__manifest__.py` files
- Default `.env`: `ODOO_VERSION=19.0`

Re-evaluate only if a blocking OCA module gap appears during the DogForce delivery spike documented in [docs/PROJECT_PLAN.md](../PROJECT_PLAN.md).

## Consequences

### Positive

- Longest planned support horizon among current majors
- Aligns with DogForce Enterprise assumption and reduces upgrade surprise at cutover
- Odoo 19 group/privilege model used in `security_base/security/security_groups.xml`

### Negative

- Fewer third-party Community modules may target 19.0 vs 18.0 at time of writing
- Developers must use Docker 19 — local Odoo installs on other versions will diverge

### Neutral

- Version is configurable via `.env` without code changes
- CI workflow (`.github/workflows/ci.yml`) pins `19.0` implicitly through `.env.example`
