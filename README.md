# DogForce Security Suite

A reusable **Odoo-based operations platform** for private security companies. The suite covers guard profiles, roster planning, attendance, leave, Namibia payroll, client billing, fleet, equipment, and a companion mobile app for field supervisors and managers.

The first deployment target is **DogForce Security Services** (Namibia). The codebase is designed so country-specific rules stay in localization packs and the core modules can be adapted for Zambia and other markets without rewriting operational logic.

---

## Core Value Proposition

| Problem | How the suite addresses it |
|---------|---------------------------|
| Guard qualification tracking is scattered across spreadsheets | Central guard profiles with grades, certifications, attributes, reliability scores, and disqualification rules |
| Rosters are hard to validate against contract requirements | Structured client → site → post → shift → roster model with eligibility constraints and override audit trails |
| Payroll depends on accurate scheduled-vs-actual attendance | Posting sheets link roster slots to check-in/out records, late/early metrics, and overtime approval |
| Namibia statutory payroll is complex | Configurable PAYE brackets, SSC rates, public holidays, and shift premiums in a dedicated localization module |
| Supervisors need field tools, not only the Odoo web UI | Expo mobile app with role-based dashboards connected to a custom JSON API on Odoo |
| One-off client customizations create unmaintainable forks | Country-neutral core modules, Namibia pack (`security_l10n_na`), and planned client migration module |

---

## High-Level Tech Stack

| Layer | Technology |
|-------|------------|
| ERP platform | **Odoo 19 Community** (Python, PostgreSQL, QWeb) |
| Database | **PostgreSQL 16** |
| Local runtime | **Docker Compose** (official `odoo` + `postgres` images) |
| Custom business logic | 22 Odoo modules in `custom_addons/` |
| Mobile app | **Expo 51** / **React Native 0.74** / **TypeScript** |
| Mobile state & data | Zustand, TanStack Query, Axios, Expo Secure Store |
| Mobile UI | React Native Paper (dark theme), Expo Router |

> **Note:** DogForce currently runs **Odoo Enterprise** in production. This repository intentionally targets **Community Edition** for pre-engagement development so reusable security-domain modules can be built without Enterprise licensing assumptions. Enterprise integration points (Accounting, Planning, Approvals) are isolated for later.

---

## Repository Layout

```text
.
├── custom_addons/          # Odoo Security Suite modules (22 modules)
├── mobile/                 # DogForce Mobile app (Expo / React Native)
├── deploy/                 # Docker Compose definition
├── docs/                   # Project plans, guides, and specifications
├── scripts/                # Local dev helpers (start, stop, backup, shell)
└── .local/                 # Generated config and persistent Docker data (gitignored)
```

---

## Quick Start

```bash
cp .env.example .env          # optional — start.sh creates .env if missing
./scripts/start.sh
./scripts/seed-db.sh          # install modules + Namibian demo data
```

Open **http://localhost:8069** and log in with database `dogforce_dev`, login `admin`, password `admin`.

For full prerequisites, environment variables, mobile setup, and troubleshooting, see **[INSTALL.md](INSTALL.md)**.

---

## Daily Development Commands

| Command | Purpose |
|---------|---------|
| `./scripts/start.sh` | Bootstrap `.env`, generate Odoo config, start Docker stack |
| `./scripts/stop.sh` | Stop containers |
| `./scripts/logs.sh` | Tail Odoo and PostgreSQL logs |
| `./scripts/odoo-shell.sh` | Open a shell inside the Odoo container |
| `./scripts/backup-db.sh` | Dump PostgreSQL to `.local/backups/` |
| `./scripts/scaffold-module.sh <name>` | Scaffold a new module in `custom_addons/` |

### Run module tests

See **[TESTING.md](TESTING.md)** for the full guide. Quick start:

```bash
./scripts/run-tests.sh
./scripts/run-coverage.sh security_payroll_core
open .local/coverage/html/index.html
```

Modules with automated tests: `security_payroll_core`, `security_equipment`, `security_fleet`.

---

## Module Overview

| Module | Purpose |
|--------|---------|
| `security_base` | Guard master data, employee extensions, security user groups |
| `security_operations` | Clients, sites, posts, shift templates, roster planning |
| `security_attendance` | Posting sheets, scheduled-vs-actual attendance metrics |
| `security_leave` | Leave types, balances, requests |
| `security_l10n_na` | Namibia payroll rules, tax brackets, public holidays |
| `security_payroll_core` | Payroll periods, payslips, statutory calculations |
| `security_loans` | Employee loans and payroll deductions |
| `security_discipline` | Behavioral incidents and reliability impact |
| `security_billing` | Client contracts, billing plans, invoices |
| `security_accounting_controls` | Client payments, ageing, reconciliation status |
| `security_client_reports` | Client-facing service/attendance reports |
| `security_reporting` | Pivot and graph dashboards |
| `security_documents` | Guard document tracking and expiry |
| `security_equipment` | Uniforms, radios, allocations, damage deductions |
| `security_fleet` | Vehicles, shuttle routes, fuel, inspections |
| `security_mobile` | REST JSON API for the mobile app |
| `security_ai_engine` | AI features — anomaly detection, risk profiling, billing audit, roster optimizer |
| `security_notifications` | Internal alert system for expiry and overdue events |
| `security_demo_data` | Namibian demo dataset (post-install hook) |
| `security_shift_planner` | Guard scoring engine and Roster Board OWL |
| `security_dogforce_migration` | CSV data migration tools for go-live |

For dependency relationships and data flows, see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Version Strategy

`.env.example` defaults to `ODOO_VERSION=19.0`, aligned with Odoo 19's planned support window (September 2025 – September 2028). If DogForce confirms a different major version or Community module availability differs, update `.env` before module development.

**Important constraint:** Do not assume Community and Enterprise behave identically for payroll, accounting, or reconciliation. Build reusable security-domain logic first; isolate Enterprise integration points later.

---

## Documentation

| Document | Description |
|----------|-------------|
| [INSTALL.md](INSTALL.md) | Prerequisites, environment setup, database seeding, and troubleshooting |
| [DEPLOYMENT.md](DEPLOYMENT.md) | CI/CD pipeline, staging vs production, rollback procedures |
| [API.md](API.md) | REST API reference — endpoints, payloads, auth, and error codes |
| [TESTING.md](TESTING.md) | Unit, integration, and E2E testing; coverage reports |
| [CODEBASE_MAP.md](CODEBASE_MAP.md) | Folder structure guide — where code lives and what each directory does |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Git workflow, coding standards, PR process, and definition of done |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, module interactions, data flow, and design patterns |
| [docs/adr/README.md](docs/adr/README.md) | Architecture Decision Records — context and consequences of key choices |
| [KNOWN_ISSUES.md](KNOWN_ISSUES.md) | Current limitations, bugs, and technical debt |
| [docs/security_mobile.md](docs/security_mobile.md) | Mobile app and API implementation plan |

---

## License

Custom modules are authored under **LGPL-3** unless otherwise noted in individual module manifests.
