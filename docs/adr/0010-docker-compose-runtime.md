# ADR-0010: Docker Compose for Runtime Packaging

**Date:** 2026-05-26  
**Status:** Accepted

## Context

Developers need a reproducible Odoo + PostgreSQL environment. DogForce staging and production also benefit from the same packaging model. Alternatives:

- **Manual Odoo install** on host Python — fragile, version drift across machines
- **Kubernetes** — overkill for current single-tenant scale
- **Docker Compose** — official Odoo and Postgres images, bind-mount `custom_addons/`

Priority 1 backlog item: "A clean laptop can clone the repo, run one setup command, start Odoo."

## Decision

Use **Docker Compose** as the standard runtime:

- `deploy/docker-compose.yml` — `postgres:16` + `odoo:${ODOO_VERSION}`
- `scripts/start.sh` — generates `.local/odoo.conf` from `.env`, starts stack
- `custom_addons/` bind-mounted to `/mnt/extra-addons`
- Persistent volumes under `.local/postgres` and `.local/odoo`

CI (`.github/workflows/ci.yml`) uses the same Compose file. Staging/production deploy procedures in DEPLOYMENT.md extend this pattern with hardening (TLS proxy, `list_db=False`).

## Consequences

### Positive

- One-command local start; matches CI environment
- Odoo and Postgres versions pinned via image tags
- No host Python/Postgres install required for module development

### Negative

- Docker Desktop required on macOS dev machines
- Bind-mount performance on macOS can be slow for large filestores
- Production still needs reverse proxy, backups, and secrets management outside Compose defaults

### Neutral

- `.env.example` documents all compose variables
- `scripts/backup-db.sh` execs into compose `db` service for `pg_dump`
