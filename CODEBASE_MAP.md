# Codebase Map

A guided tour of the DogForce Security Suite repository — what each folder contains, why it exists, and where to look when making a change.

For setup instructions see [INSTALL.md](INSTALL.md). For module dependencies and data flow see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Repository overview

```text
DogFrce Security Services Custom Odoo Modules/
├── custom_addons/       # Odoo Security Suite modules (backend business logic)
├── mobile/              # DogForce Mobile app (Expo / React Native)
├── deploy/              # Docker Compose stack definition
├── docs/                # Project plans, specs, and legacy guides
├── scripts/             # Local dev helper shell scripts
├── .github/             # GitHub PR template and future CI config
├── .local/              # Generated runtime data (gitignored)
├── README.md            # Project overview
├── INSTALL.md           # Setup and seeding guide
├── ARCHITECTURE.md      # System design
├── CONTRIBUTING.md      # Git workflow and coding standards
├── CODEBASE_MAP.md      # This file
└── .env.example         # Environment variable template
```

---

## Top-level folders

### `custom_addons/`

**Purpose:** All custom Odoo 19 modules for the Security Suite. This is the core backend — business models, views, security rules, reports, and the mobile REST API.

Mounted into the Odoo Docker container at `/mnt/extra-addons`. Each subdirectory is one installable Odoo module.

| Module | Purpose |
|--------|---------|
| `security_base` | Guard profiles, grades, certifications, security user groups |
| `security_operations` | Clients, sites, posts, shift templates, roster planning |
| `security_shift_planner` | Constraint-satisfaction guard scoring engine, roster suggestions, Roster Board OWL client action |
| `security_attendance` | Posting sheets and scheduled-vs-actual attendance |
| `security_leave` | Leave types, balances, requests |
| `security_l10n_na` | Namibia payroll — PAYE brackets, SSC rates, public holidays, payslip PDF |
| `security_payroll_core` | Payroll periods, payslips, statutory calculations |
| `security_loans` | Employee loans and payroll deductions |
| `security_discipline` | Behavioral incidents and reliability impact |
| `security_billing` | Client contracts, billing plans, invoices |
| `security_accounting_controls` | Client payments and ageing |
| `security_client_reports` | Client-facing service/attendance reports |
| `security_reporting` | Pivot and graph dashboards (views only) |
| `security_documents` | Guard document tracking and expiry |
| `security_equipment` | Uniforms, radios, allocations, damage deductions |
| `security_fleet` | Vehicles, shuttle routes, fuel, inspections |
| `security_mobile` | REST JSON API controllers for the mobile app |
| `security_ai_engine` | Multi-provider AI facade (Claude / OpenAI / Gemini); anomaly detection, risk profiling, billing audit, roster optimizer |
| `security_notifications` | Internal notification model with daily crons for document expiry and overdue invoice alerts |
| `security_demo_data` | Post-install hook that seeds Namibian demo records |
| `security_dogforce_migration` | CSV import tools for migrating guards, clients, leave balances, and loans |
| `security_l10n_zm` | Zambia payroll — NAPSA, NHIMA, WCF levy, PAYE brackets, ZM payslip PDF override |
| `security_zra_invoice` | ZRA Smart Invoice — VSDC API integration, fiscal signing, bulk wizard, submission log, retry with exponential backoff |
| `security_help` | In-app Help Centre — country-aware categories and articles (OWL client action, full-text search) |
| `security_suite` | Meta-module that installs the complete Security Suite in one step |
| `security_demo_site` | Demo site login panel and demo account management |

#### Standard Odoo module layout

Every module under `custom_addons/<module_name>/` follows the same internal structure:

| Subfolder / file | Purpose |
|------------------|---------|
| `__manifest__.py` | Module metadata: name, version, dependencies, data files to load |
| `__init__.py` | Python package entry; imports `models`, `controllers`, etc. |
| `models/` | **Business logic layer.** Python model classes (`security.*`), computed fields, constraints, workflow actions (`action_*`) |
| `views/` | **Presentation layer.** XML form, list, search, kanban, and menu definitions |
| `security/` | **Access control.** `ir.model.access.csv` (CRUD per group), optional `security_groups.xml` and record rules |
| `data/` | Seed XML/CSV loaded on install — sequences, default records, localization data |
| `reports/` | QWeb PDF report templates (payslips, invoices, allocation forms) |
| `controllers/` | HTTP JSON endpoints (only in `security_mobile`) — thin API over models |
| `tests/` | Odoo `TransactionCase` unit tests (payroll, equipment, fleet) |
| `hooks.py` | Post-install hooks (only in `security_demo_data`) |

**Where to change what:**

- New field or calculation → `models/`
- New screen or menu → `views/`
- Who can read/write a model → `security/ir.model.access.csv`
- New API endpoint for mobile → `security_mobile/controllers/`
- Printable document → `reports/`

---

### `mobile/`

**Purpose:** The DogForce Mobile companion app for supervisors, site managers, and business owners. A thin client — all business rules live in Odoo; this app handles auth, routing, and UI.

```text
mobile/
├── app/                 # Screens and navigation (Expo Router)
├── src/                 # Shared application code
├── assets/              # App icons, splash screen, favicon
├── app.json             # Expo app configuration
├── package.json         # npm dependencies and scripts
├── tsconfig.json        # TypeScript compiler options
└── babel.config.js      # Babel / Metro bundler config
```

#### `mobile/app/`

**Purpose:** File-based routing and screen components. Each file becomes a route. Route groups in parentheses `(auth)`, `(supervisor)`, etc. organize layouts without affecting the URL.

| Path | Purpose |
|------|---------|
| `_layout.tsx` | Root layout — auth gate, theme provider, role-based redirect |
| `(auth)/login.tsx` | Login screen; authenticates via Odoo JSON-RPC |
| `(supervisor)/` | Field supervisor portal — today's posting sheet, mark presence, history |
| `(supervisor)/index.tsx` | Today's roster / posting sheet list |
| `(supervisor)/mark/[recordId].tsx` | Mark attendance for a single guard record |
| `(supervisor)/history.tsx` | Past posting sheet history |
| `(manager)/` | Site manager portal — multi-site dashboard, overtime approval |
| `(manager)/index.tsx` | All-sites attendance summary |
| `(manager)/site/[siteId].tsx` | Single-site roster detail |
| `(manager)/overtime.tsx` | Pending overtime approvals |
| `(owner)/` | Executive portal — high-level KPIs |
| `(owner)/index.tsx` | Attendance, payroll YTD, invoice KPIs |

Think of `app/` as the **pages layer** — screen composition and navigation only; keep heavy logic in `src/`.

#### `mobile/src/api/`

**Purpose:** HTTP client and Odoo API calls. Equivalent to a **services layer** in other front-end architectures.

| File | Purpose |
|------|---------|
| `client.ts` | Axios instance, base URL, session cookie/header injection, auth expiry handling |
| `auth.ts` | Login/logout via `/web/session/authenticate` and `/web/session/destroy` |
| `supervisor.ts` | Calls to `/api/security/mobile/supervisor/*` |
| `manager.ts` | Calls to `/api/security/mobile/manager/*` |
| `owner.ts` | Calls to `/api/security/mobile/owner/*` |

#### `mobile/src/components/`

**Purpose:** Reusable UI building blocks shared across screens.

| Component | Purpose |
|-----------|---------|
| `CheckInButton.tsx` | Quick check-in / check-out action |
| `GuardCard.tsx` | Guard row on a posting sheet |
| `KpiMetric.tsx` | Single KPI tile (label + value) |
| `SiteKpiCard.tsx` | Site-level summary card for manager dashboard |
| `StatusBadge.tsx` | Attendance status indicator (present, late, absent, etc.) |

#### `mobile/src/stores/`

**Purpose:** Client-side state management with Zustand. Equivalent to a **context/state layer** — holds session-adjacent UI state, not business data from Odoo.

| File | Purpose |
|------|---------|
| `authStore.ts` | Current user profile, role, login/logout state |
| `appStore.ts` | UI state: selected date, search query, selected site, refresh trigger |

Server data is fetched via TanStack Query patterns in screen components (calling `src/api/`).

#### `mobile/src/theme/`

**Purpose:** Visual design tokens — colors, typography, spacing for React Native Paper dark theme.

| File | Purpose |
|------|---------|
| `index.ts` | Theme object consumed by the root layout |

#### `mobile/assets/`

**Purpose:** Static images bundled with the app — icon, splash screen, adaptive icon (Android), favicon (web).

---

### `deploy/`

**Purpose:** Infrastructure-as-code for the local development stack.

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Defines `postgres:16` and `odoo:19.0` services, port mappings, volume mounts |

Custom addons are bind-mounted from `custom_addons/`; Odoo config is generated at runtime by `scripts/start.sh` into `.local/odoo.conf`.

---

### `docs/`

**Purpose:** Planning documents, client specifications, and module guides. Not loaded by Odoo — reference material for developers and stakeholders.

| Document | Purpose |
|----------|---------|
| `PLATFORM_MASTER_PLAN.md` | Comprehensive platform vision, gap analysis, OWL component inventory, sprint sequence |
| `Dogforce_Functional_Specifications.md` | Original client functional specification |
| `security_mobile.md` | Mobile app and REST API implementation plan |
| `adr/` | Architecture Decision Records (ADR-0001 through ADR-0015) |
| `*.docx` | Client proposal and functional specification (binary originals) |

---

### `scripts/`

**Purpose:** Shell scripts for repeatable local development tasks. All scripts source `docker-env.sh` to locate Docker and Compose on macOS or Linux.

| Script | Purpose |
|--------|---------|
| `docker-env.sh` | Resolves `docker` and `docker compose` binary paths |
| `start.sh` | Create `.env`, generate Odoo config, start Docker stack |
| `stop.sh` | Stop containers |
| `logs.sh` | Tail container logs |
| `odoo-shell.sh` | Open bash shell inside Odoo container |
| `backup-db.sh` | `pg_dump` to `.local/backups/` |
| `seed-db.sh` | Install Security Suite modules and load demo data |
| `run-tests.sh` | Run Odoo module tests (`TransactionCase`) |
| `run-coverage.sh` | Run tests with HTML coverage report |
| `scaffold-module.sh` | Run `odoo scaffold` to create a new module skeleton |

---

### `.github/`

**Purpose:** GitHub-specific configuration.

| File | Purpose |
|------|---------|
| `pull_request_template.md` | Default PR description template (summary, test plan, checklist) |

Future CI workflows (Odoo tests, mobile type-check) would live in `.github/workflows/`.

---

### `.local/` (gitignored)

**Purpose:** Generated and persistent local runtime data. Never commit this folder.

| Path | Purpose |
|------|---------|
| `.local/postgres/` | PostgreSQL data volume |
| `.local/odoo/` | Odoo filestore and session data |
| `.local/odoo.conf` | Odoo config generated from `.env` by `start.sh` |
| `.local/backups/` | Database dumps from `backup-db.sh` |

---

## Root-level files

| File | Purpose |
|------|---------|
| `.env.example` | Template for local environment variables (ports, DB name, passwords) |
| `.env` | Your local copy (gitignored) |
| `.gitignore` | Excludes `.local/`, `.env`, `__pycache__`, `node_modules`, etc. |
| `README.md` | Project overview and quick start |
| `INSTALL.md` | Full setup, seeding, and troubleshooting |
| `ARCHITECTURE.md` | System design, data flow, integrations |
| `CONTRIBUTING.md` | Git workflow, coding standards, definition of done |
| `CODEBASE_MAP.md` | This document |

---

## Find code by concern

Use this table when you know **what** you need to change but not **where**:

| I need to… | Look in… |
|------------|----------|
| Add a guard field | `custom_addons/security_base/models/hr_employee.py` |
| Change roster validation rules | `custom_addons/security_operations/models/` |
| Fix attendance hour calculation | `custom_addons/security_attendance/models/` |
| Adjust PAYE or SSC rates | `custom_addons/security_l10n_na/data/` or `models/` |
| Change payslip computation | `custom_addons/security_payroll_core/models/` |
| Add a mobile API endpoint | `custom_addons/security_mobile/controllers/` |
| Change a mobile screen | `mobile/app/(role)/` |
| Change how mobile talks to Odoo | `mobile/src/api/` |
| Add a reusable mobile widget | `mobile/src/components/` |
| Add demo guards or sites | `custom_addons/security_demo_data/hooks.py` |
| Change Docker ports or images | `deploy/docker-compose.yml` and `.env` |
| Add a printable PDF | `custom_addons/<module>/reports/` |
| Add automated tests | `custom_addons/<module>/tests/` |
| Update project planning docs | `docs/` |
| Tune AI provider or feature toggles | `custom_addons/security_ai_engine/models/security_ai_config.py` |
| Add a new AI feature | `custom_addons/security_ai_engine/models/security_ai_features.py` |
| Import historical data from CSV | `custom_addons/security_dogforce_migration/models/security_migration.py` |
| Add an internal notification | `custom_addons/security_notifications/models/security_notifications.py` |
| Change guard roster scoring logic | `custom_addons/security_shift_planner/models/security_shift_planner.py` |
| Adjust Zambia PAYE brackets or NAPSA/NHIMA rates | `custom_addons/security_l10n_zm/data/security_l10n_zm_data.xml` |
| Change Zambia payslip computation | `custom_addons/security_l10n_zm/models/security_l10n_zm.py` |
| Update WCF risk class or rate | `custom_addons/security_l10n_zm/models/security_l10n_zm.py` (WCF fields on employee form) |
| Debug ZRA Smart Invoice submission | `custom_addons/security_zra_invoice/models/security_billing_zra.py` |
| Change ZRA retry backoff schedule | `custom_addons/security_zra_invoice/models/security_zra_submission.py` |
| Submit ZRA invoices in bulk | `custom_addons/security_zra_invoice/models/security_zra_bulk_wizard.py` |
| Add a Help Centre article | `custom_addons/security_help/data/help_content.xml` |
| Change Help Centre OWL portal | `custom_addons/security_help/static/src/js/help_portal.js` |

---

## Mental model: two applications, one platform

```text
                    ┌─────────────────────────────────┐
                    │         custom_addons/          │
                    │   (Odoo — source of truth)      │
                    │                                 │
                    │  models/  views/  security/     │
                    │  controllers/ (security_mobile) │
                    └───────────────┬─────────────────┘
                                    │ HTTP / JSON-RPC
                    ┌───────────────▼─────────────────┐
                    │           mobile/               │
                    │   (Expo — presentation only)    │
                    │                                 │
                    │  app/  src/api/  src/components/│
                    │  src/stores/  src/theme/        │
                    └─────────────────────────────────┘
```

The Odoo web UI (standard Odoo frontend, not in this repo) and the mobile app are both clients of the same backend modules. Business logic should only be added to `custom_addons/*/models/`, never duplicated in `mobile/`.

---

## Related documentation

| Document | When to read it |
|----------|-----------------|
| [INSTALL.md](INSTALL.md) | First-time setup or database seeding |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Module dependencies, data flow, design patterns |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Branch naming, PR process, coding style |
| [docs/security_mobile.md](docs/security_mobile.md) | Mobile API implementation plan |
| [API.md](API.md) | REST API reference — endpoints, payloads, auth, error codes |
| [TESTING.md](TESTING.md) | Unit, integration, E2E testing, and coverage |
