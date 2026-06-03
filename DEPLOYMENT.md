# Deployment Guide

How the DogForce Security Suite is built, tested, deployed to staging and production, and rolled back when something goes wrong.

For local setup see [INSTALL.md](INSTALL.md). For tests run in CI see [TESTING.md](TESTING.md).

---

## Current status

| Capability | Status |
|------------|--------|
| Local Docker dev stack | **Implemented** — `deploy/docker-compose.yml`, `scripts/start.sh` |
| Staging environment | **Not provisioned** — procedure defined below |
| Production environment | **Not provisioned** — DogForce currently on Odoo Enterprise separately |
| GitHub Actions CI | **Starter workflow added** — `.github/workflows/ci.yml` |
| Automated CD to staging/production | **Not implemented** — manual deploy steps below |
| Database backup script | **Implemented** — `scripts/backup-db.sh` |
| Database restore script | **Manual procedure** — documented below |

This guide describes the **target operating model** and what is available today. Treat staging deployment as the first milestone before production cutover.

---

## Environment overview

```text
┌─────────────┐     push/PR      ┌─────────────┐    merge to main    ┌─────────────┐
│  Developer  │ ───────────────▶ │  GitHub CI  │ ─────────────────▶  │   Staging   │
│  localhost  │                  │   Actions   │   manual promote    │   server    │
└─────────────┘                  └─────────────┘                     └──────┬──────┘
                                                                            │
                                                                   signed-off release
                                                                            ▼
                                                                     ┌─────────────┐
                                                                     │ Production  │
                                                                     │  (DogForce) │
                                                                     └─────────────┘
```

### Environment comparison

| | **Local (dev)** | **Staging** | **Production** |
|---|-----------------|-------------|----------------|
| **Purpose** | Module development, demos | Pre-release validation, UAT, payroll sign-off | Live DogForce operations |
| **Odoo edition** | Community 19 (Docker) | Community 19 (Docker or VM) | Community 19 or Enterprise (client decision) |
| **Database** | `dogforce_dev` | `dogforce_staging` | `dogforce_prod` |
| **Demo data** | `security_demo_data` installed | Optional subset or anonymised copy | **Never** install demo data |
| **Compose project** | `dogforce-odoo-dev` | `dogforce-odoo-staging` | `dogforce-odoo-prod` |
| **Secrets** | `.env` (local, gitignored) | Server env / secrets manager | Server env / secrets manager |
| **Backups** | Ad hoc via `backup-db.sh` | Daily automated + pre-deploy | Daily automated + pre-deploy |
| **Mobile app** | Expo dev / internal build | Internal TestFlight / APK track | App Store / Play Store or MDM |
| **Access** | Developers | Dev team + DogForce UAT users | DogForce staff only |

### Environment variables by tier

Copy `.env.example` and adjust per environment:

| Variable | Local | Staging | Production |
|----------|-------|---------|------------|
| `COMPOSE_PROJECT_NAME` | `dogforce-odoo-dev` | `dogforce-odoo-staging` | `dogforce-odoo-prod` |
| `ODOO_VERSION` | `19.0` | `19.0` (pin minor tag when stabilised) | Same as staging |
| `ODOO_DB` | `dogforce_dev` | `dogforce_staging` | `dogforce_prod` |
| `ODOO_ADMIN_PASSWORD` | `admin` | Strong random | Strong random, restricted |
| `POSTGRES_PASSWORD` | `odoo` | Strong random | Strong random, restricted |
| `ODOO_PORT` | `8069` | `8069` or behind reverse proxy | `443` via TLS proxy |
| `proxy_mode` in odoo.conf | `False` | `True` | `True` |

Production `odoo.conf` should also set:

```ini
list_db = False
without_demo = True
proxy_mode = True
```

Generate production config from the same pattern as `scripts/start.sh`, with hardening applied on the server.

---

## CI/CD pipeline (GitHub Actions)

### Pipeline stages

```text
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│  Trigger │──▶│   Lint   │──▶│   Test   │──▶│  Build   │──▶│  Deploy  │
│ PR/push  │   │  (future)│   │   Odoo   │   │  artifact│   │ (manual) │
└──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
                                    │                              │
                                    ▼                              ▼
                              mobile ts:check                 staging only
```

| Stage | Trigger | What runs | Blocks merge |
|-------|---------|-----------|--------------|
| **CI — test** | PR and push to `main` | Odoo module tests + mobile type check | Yes (when required checks enabled) |
| **CD — staging** | Manual workflow or tag `staging-*` | SSH deploy to staging server | N/A |
| **CD — production** | Manual workflow + approval gate | SSH deploy to production | Requires sign-off |

Workflow file: [.github/workflows/ci.yml](.github/workflows/ci.yml)

### What CI runs today

On every pull request and push to `main`:

1. Start PostgreSQL 16 and Odoo 19 via Docker Compose
2. Install Security Suite test modules
3. Run `./scripts/run-tests.sh`
4. Run `cd mobile && npm run ts:check`

### Enabling branch protection

In GitHub repository settings → **Branches** → `main`:

1. Require status check: **CI**
2. Require pull request reviews
3. Do not allow bypassing for administrators (recommended for production-bound repo)

### CD — deploying from CI (manual promote)

Automated deployment to staging/production is **not wired yet**. Recommended approach:

1. CI passes on `main`
2. Maintainer triggers **Deploy Staging** workflow (or runs server script)
3. DogForce UAT on staging
4. Maintainer triggers **Deploy Production** with release tag (e.g. `v19.0.1`)

Future workflows would live in `.github/workflows/deploy-staging.yml` and `deploy-production.yml`, using GitHub **Environments** with required reviewers for production.

---

## Deployment procedure

### Pre-deploy checklist

- [ ] CI green on the commit being deployed
- [ ] [TESTING.md](TESTING.md) manual checks completed for this release
- [ ] Database backup taken (staging and production)
- [ ] Release notes / module upgrade notes prepared
- [ ] Payroll or statutory changes signed off by DogForce finance (production only)
- [ ] Maintenance window communicated (production only)

### 1. Local / developer deploy

Already documented in [INSTALL.md](INSTALL.md):

```bash
./scripts/start.sh
./scripts/seed-db.sh          # dev only
```

### 2. Staging deploy

**First-time staging setup:**

```bash
# On staging server
git clone <repository-url> /opt/dogforce-odoo
cd /opt/dogforce-odoo
cp .env.example .env          # edit for staging values
./scripts/start.sh

# Install modules (no demo data in staging unless UAT needs it)
docker compose -f deploy/docker-compose.yml exec odoo odoo \
  -c /etc/odoo/odoo.conf \
  -d dogforce_staging \
  -i security_base,security_operations,security_attendance,security_leave,security_l10n_na,security_payroll_core,security_loans,security_discipline,security_billing,security_accounting_controls,security_client_reports,security_equipment,security_fleet,security_mobile,security_reporting \
  --stop-after-init
```

**Routine staging update:**

```bash
cd /opt/dogforce-odoo

# 1. Backup
./scripts/backup-db.sh

# 2. Pull release
git fetch origin
git checkout main
git pull origin main

# 3. Restart stack (picks up code + regenerates odoo.conf)
./scripts/stop.sh
./scripts/start.sh

# 4. Upgrade changed modules (replace list with modules touched in release)
docker compose -f deploy/docker-compose.yml exec odoo odoo \
  -c /etc/odoo/odoo.conf \
  -d dogforce_staging \
  -u security_payroll_core,security_attendance \
  --stop-after-init

# 5. Smoke test
curl -f http://localhost:8069/web/health || curl -f http://localhost:8069/
```

Verify: login, posting sheet, payslip generation, mobile API endpoint (see [API.md](API.md)).

### 3. Production deploy

Production follows the same steps as staging with these additions:

| Step | Production requirement |
|------|------------------------|
| Backup | Mandatory; store off-server (S3, NAS, etc.) |
| Timing | Off-peak window; notify supervisors if mobile API affected |
| Demo data | Do **not** install `security_demo_data` |
| Module upgrade | Upgrade only modules in the release; never `-i` on live DB unless new module |
| Verification | DogForce payroll officer signs off payslip test run |
| Mobile | Publish app build only after backend is live and verified |

```bash
# Production upgrade (modules already installed — use -u not -i)
docker compose -f deploy/docker-compose.yml exec odoo odoo \
  -c /etc/odoo/odoo.conf \
  -d dogforce_prod \
  -u security_payroll_core \
  --stop-after-init
```

### 4. Mobile app deploy

Mobile is deployed separately from Odoo:

| Environment | Channel |
|-------------|---------|
| Staging | Expo internal distribution / TestFlight internal / APK sideload |
| Production | App Store / Google Play / MDM |

Before publishing a mobile build:

1. Backend deployed and API smoke-tested
2. Update `ODOO_BASE_URL` in `mobile/src/api/client.ts` or use build-time env (EAS)
3. Run `npm run ts:check`
4. Tag mobile release matching backend tag where possible

### 5. Post-deploy verification

| Check | Command / action |
|-------|------------------|
| Odoo health | Load web UI, login |
| Module versions | Settings → Apps → verify upgraded modules |
| Payroll smoke | Generate test payslip on staging; compare to manual calc |
| Mobile API | `curl` supervisor today endpoint ([API.md](API.md)) |
| Logs | `./scripts/logs.sh` — no tracebacks |
| Backups | Confirm post-deploy backup scheduled |

---

## Rollback procedure

Rollback strategy depends on what failed: **application code**, **database schema/data**, or **mobile client**.

### Decision matrix

| Symptom | Likely cause | Rollback action |
|---------|--------------|-----------------|
| Traceback on module upgrade | Bad Python/XML in release | Code rollback + module downgrade |
| Wrong payroll figures | Logic or config error | DB restore to pre-deploy backup |
| Mobile cannot connect | API breaking change | Revert mobile build or hotfix backend |
| Performance degradation | DB migration / index | DB restore or DBA intervention |

**Golden rule:** always take a backup immediately before deploy. Rollback without a backup may be impossible without data loss.

---

### Rollback A — Application code (Odoo modules)

Use when the database is healthy but the new code is defective.

```bash
cd /opt/dogforce-odoo

# 1. Stop stack
./scripts/stop.sh

# 2. Checkout previous release
git fetch --tags
git checkout v19.0.0          # last known good tag or commit SHA

# 3. Restart
./scripts/start.sh

# 4. Downgrade modules if schema changed (same module list as upgrade)
docker compose -f deploy/docker-compose.yml exec odoo odoo \
  -c /etc/odoo/odoo.conf \
  -d dogforce_prod \
  -u security_payroll_core \
  --stop-after-init
```

Verify logs and smoke tests. Tag the bad release as **do not deploy** in release notes.

> **Note:** Odoo module downgrades are not always automatic. If upgrade ran irreversible SQL/data migrations, use **Rollback B** (database restore) instead.

---

### Rollback B — Database restore

Use when upgrade corrupted data, payroll ran with wrong logic, or module downgrade is unsafe.

```bash
cd /opt/dogforce-odoo

# 1. Stop Odoo (keep PostgreSQL running)
docker compose -f deploy/docker-compose.yml stop odoo

# 2. Identify pre-deploy backup
ls -lt .local/backups/

# 3. Restore (replace filename and credentials)
docker compose -f deploy/docker-compose.yml exec -T db \
  psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS dogforce_prod;"
docker compose -f deploy/docker-compose.yml exec -T db \
  psql -U odoo -d postgres -c "CREATE DATABASE dogforce_prod;"

cat .local/backups/dogforce_prod_YYYYMMDD_HHMMSS.sql | \
  docker compose -f deploy/docker-compose.yml exec -T db \
  psql -U odoo -d dogforce_prod

# 4. Checkout matching code version
git checkout v19.0.0

# 5. Start stack
./scripts/start.sh
```

**Production:** restore from off-server backup copy, not only local `.local/backups/`.

Post-restore:

- Verify record counts and latest payslip period
- Notify users if any transactions during failed deploy window are lost
- Document incident and root cause

---

### Rollback C — Docker image pin

Use when the official `odoo:19.0` image updated and broke compatibility.

```bash
# Pin exact digest or minor tag in .env
ODOO_VERSION=19.0-20250530

./scripts/stop.sh
docker compose -f deploy/docker-compose.yml pull odoo
./scripts/start.sh
```

Keep a record of working image digests per environment.

---

### Rollback D — Mobile app

| Channel | Rollback |
|---------|----------|
| Expo / internal | Redistribute previous build artefact |
| TestFlight / Play internal | Promote previous build in store console |
| Production stores | Submit previous version review or use store rollback if available |

Mobile can be rolled back independently if the backend remains backward compatible. If backend was rolled back, deploy the matching mobile build version.

---

### Rollback checklist

- [ ] Incident logged with deploy commit SHA and timestamp
- [ ] Pre-deploy backup identified and verified restorable
- [ ] Rollback type chosen (A/B/C/D)
- [ ] Stack restarted and smoke tests pass
- [ ] DogForce notified if production data or payroll affected
- [ ] Post-mortem scheduled before re-attempting deploy

---

## Backups and retention

### Automated backup (recommended for staging/production)

Cron on the server (daily at 02:00):

```cron
0 2 * * * cd /opt/dogforce-odoo && ./scripts/backup-db.sh && find .local/backups -mtime +30 -delete
```

Copy backups off-server:

```bash
aws s3 cp .local/backups/ s3://dogforce-backups/odoo/ --recursive --exclude "*" --include "*.sql"
```

### What to backup

| Asset | Method | Retention |
|-------|--------|-----------|
| PostgreSQL database | `pg_dump` via `backup-db.sh` | 30 days daily; 12 monthly |
| Odoo filestore | `.local/odoo/` or `/var/lib/odoo` volume | Same as DB |
| `.env` / secrets | Secrets manager export | Versioned |
| Mobile builds | CI artefacts / EAS | Per release |

Database and filestore must be restored together for attachment consistency.

---

## Release tagging

Use semantic tags aligned with Odoo module versions:

```text
v19.0.1   — first staging release
v19.0.2   — payroll fix
v19.1.0   — new module (minor)
```

Tag after CI passes on `main`:

```bash
git tag -a v19.0.1 -m "Staging release: payroll SSC cap fix"
git push origin v19.0.1
```

Production deploys should only use tagged releases, not floating `main`.

---

## Security and hardening (production)

| Item | Recommendation |
|------|----------------|
| TLS | Terminate HTTPS at nginx/Traefik/Caddy in front of Odoo |
| `list_db` | `False` on production |
| Master password | Strong; not shared with app users |
| PostgreSQL | Not exposed publicly; internal Docker network only |
| SSH | Key-based auth; deploy user with limited sudo |
| Secrets | GitHub Environments / Vault — never commit `.env` |
| Mobile API | Session timeout; HTTPS only in production |
| 2FA | Required for accounting roles (backlog — policy or Enterprise) |

---

## Infrastructure options

| Option | Best for | Notes |
|--------|----------|-------|
| **Docker Compose on VM** | Staging, small production | Matches this repo; lowest friction |
| **Managed VPS** (DigitalOcean, Hetzner, AWS EC2) | Production | Add reverse proxy + backups |
| **Odoo.sh / managed Odoo** | Enterprise clients | Custom addons via git; different deploy model |
| **Kubernetes** | Large multi-tenant | Overkill for single DogForce instance today |

---

## Related documentation

| Document | Description |
|----------|-------------|
| [INSTALL.md](INSTALL.md) | Local environment setup |
| [TESTING.md](TESTING.md) | Tests run in CI and before deploy |
| [API.md](API.md) | Post-deploy mobile API smoke tests |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System components being deployed |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Release and PR process |
| [docs/PLATFORM_MASTER_PLAN.md](docs/PLATFORM_MASTER_PLAN.md) | Sprint sequence, module gaps, go-live checklist |
