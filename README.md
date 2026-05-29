# Dogforce Security Suite

This repository is the pre-contract development workspace for a reusable Odoo Security Suite targeting security companies, starting with Namibia and later Zambia and other markets.

## Current Goal

Set up a reproducible local **Odoo Community** development environment so custom modules can be built before the Dogforce engagement begins.

Dogforce currently uses **Odoo Enterprise**, but this repo intentionally starts on **Community** for pre-project module development and environment preparation.

## Local Development Stack

- Odoo Community via Docker
- PostgreSQL via Docker
- Custom modules in `custom_addons/`
- Persistent local data in `.local/`

## Prerequisites

Install Docker Desktop for Apple Silicon macOS:

- Docker Desktop: https://www.docker.com/products/docker-desktop/

After installing, confirm:

```bash
docker --version
docker compose version
```

## First-Time Setup

1. Copy the environment file:

```bash
cp .env.example .env
```

2. Start the stack:

```bash
./scripts/start.sh
```

3. Open Odoo:

```text
http://localhost:8069
```

4. Create the database named in `ODOO_DB`, using the master password from `.env`.

## Daily Commands

Start:

```bash
./scripts/start.sh
```

Stop:

```bash
./scripts/stop.sh
```

View logs:

```bash
./scripts/logs.sh
```

Open an Odoo shell in the container:

```bash
./scripts/odoo-shell.sh
```

Scaffold a new custom module:

```bash
./scripts/scaffold-module.sh security_base
```

Back up the development database:

```bash
./scripts/backup-db.sh
```

## Repository Layout

```text
.
├── custom_addons/
├── deploy/
├── docs/
├── scripts/
└── .local/
```

## Version Strategy

`.env.example` defaults to `ODOO_VERSION=19.0`.

That matches your current assumption about Dogforce Enterprise being on the latest major version. If Dogforce later confirms a different major version, update `.env` before serious module development.

## Important Constraint

Do not build payroll, accounting, or reconciliation logic on the assumption that Community and Enterprise are identical. Build reusable security-domain modules first, and isolate Enterprise integration points later.
