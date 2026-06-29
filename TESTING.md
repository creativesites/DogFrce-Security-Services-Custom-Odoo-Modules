# Testing Guide

How to run automated and manual tests for the DogForce Security Suite — Odoo backend modules, mobile API, and the Expo mobile app.

For local setup, see [INSTALL.md](INSTALL.md). For API smoke-test payloads, see [API.md](API.md).

---

## Overview

| Layer | Test type | Tooling | Status |
|-------|-----------|---------|--------|
| Odoo models | Unit / integration | Odoo `TransactionCase` | **7 test files** across 5 modules |
| Odoo HTTP API | Integration | Odoo `HttpCase` (recommended) | Not yet implemented |
| Mobile TypeScript | Static analysis | `tsc` | Available |
| Mobile UI | Unit | Jest / React Native Testing Library | Not yet configured |
| Mobile + Odoo | End-to-end | Manual / Expo Go; Detox or Maestro (planned) | Manual only |
| CI | All | GitHub Actions | Not yet configured |

### Modules with automated tests today

| Module | Test file | What is covered |
|--------|-----------|-----------------|
| `security_payroll_core` | `tests/test_payroll.py` | PAYE brackets, SSC cap, payslip totals, period workflow |
| `security_payroll_core` | `tests/test_payroll_pipeline.py` | End-to-end pipeline: generate → compute → confirm; one payslip per guard |
| `security_payroll_core` | `tests/test_anomaly_detection.py` | AWOL threshold, late arrival threshold, unpaid ratio flag, missing checkout flag |
| `security_attendance` | `tests/test_attendance_scenarios.py` | Present/AWOL/late scenarios, night shift hours, Sunday shift flag |
| `security_equipment` | `tests/test_equipment.py` | Allocations, damage claims, payroll deduction injection |
| `security_fleet` | `tests/test_fleet.py` | Inspections, shuttle runs, passenger manifests, odometer, fuel logs |
| `security_l10n_zm` | `tests/test_zm_payroll.py` | NAPSA cap/no-cap, NHIMA, PAYE deductibility (NAPSA pre-tax), WCF floor, combined statutory scenario |

---

## Prerequisites

1. Docker stack running:

   ```bash
   ./scripts/start.sh
   ```

2. Use a **dedicated test database** (recommended) so test runs do not modify dev data:

   ```bash
   export TEST_DB=dogforce_test   # optional; defaults to ${ODOO_DB}_test
   ```

3. For mobile checks:

   ```bash
   cd mobile && npm install
   ```

---

## Unit tests (Odoo models)

Odoo unit tests live in each module's `tests/` folder. They inherit from `TransactionCase`, which wraps each test in a database transaction that is rolled back on completion.

### File layout

```text
custom_addons/security_payroll_core/
├── tests/
│   ├── __init__.py          # from . import test_payroll
│   └── test_payroll.py      # class TestSecurityPayroll(TransactionCase)
```

**Conventions:**

- Test class: `class Test<ModuleName>(TransactionCase)`
- Test methods: must start with `test_` (e.g. `test_01_low_income_payslip_calculations`)
- Use `setUp()` to create fixtures (employees, rule sets, records)
- Assert with `self.assertEqual`, `self.assertRaises(ValidationError)`, etc.

### Run one module

```bash
./scripts/run-tests.sh security_payroll_core
```

Or directly via Docker:

```bash
docker compose -f deploy/docker-compose.yml exec odoo odoo \
  -c /etc/odoo/odoo.conf \
  -d dogforce_test \
  --test-enable \
  --stop-after-init \
  -i security_payroll_core \
  --log-level=test:INFO
```

### Run all modules with tests

```bash
./scripts/run-tests.sh security_payroll_core,security_attendance,security_equipment,security_fleet,security_l10n_zm
```

### Run tests after upgrading (module already installed)

Replace `-i` (install) with `-u` (upgrade):

```bash
docker compose -f deploy/docker-compose.yml exec odoo odoo \
  -c /etc/odoo/odoo.conf \
  -d dogforce_dev \
  --test-enable \
  --stop-after-init \
  -u security_payroll_core \
  --log-level=test:INFO
```

### Run a single test method (tag filtering)

Odoo supports `--test-tags` to filter by module, class, or method:

```bash
docker compose -f deploy/docker-compose.yml exec odoo odoo \
  -c /etc/odoo/odoo.conf \
  -d dogforce_test \
  --test-enable \
  --stop-after-init \
  -u security_payroll_core \
  --test-tags /security_payroll_core:TestSecurityPayroll.test_01_low_income_payslip_calculations \
  --log-level=test:INFO
```

Tag format: `/module_name:ClassName.method_name`

### Reading test output

Successful run ends with:

```text
odoo.tests.result: 0 failed, 0 error(s) of N tests
```

Failures show the assertion traceback in container logs:

```bash
./scripts/logs.sh
```

Look for lines prefixed with `FAIL:` or `ERROR:`.

---

## Integration tests

In this codebase, **integration tests** fall into two categories.

### 1. Odoo multi-model tests (existing)

`TransactionCase` tests that exercise workflows across several models are integration tests in practice. Examples:

| Test | Models involved |
|------|-----------------|
| `test_payroll.py` | attendance → payslip → deductions |
| `test_equipment.py` | equipment allocation → damage → payslip deduction |
| `test_fleet.py` | vehicle → shuttle run → passenger manifest |

Run them the same way as unit tests:

```bash
./scripts/run-tests.sh security_equipment
```

### 2. HTTP API / controller tests (recommended, not yet built)

Mobile REST endpoints in `security_mobile/controllers/` should be tested with Odoo `HttpCase`:

```python
from odoo.tests.common import HttpCase

class TestSupervisorApi(HttpCase):
    def test_today_requires_auth(self):
        response = self.url_open("/api/security/mobile/supervisor/today")
        self.assertIn(response.status_code, (401, 403))

    def test_today_returns_posting_sheet(self):
        self.authenticate("supervisor_user", "password")
        response = self.url_open("/api/security/mobile/supervisor/today")
        body = response.json()
        self.assertTrue(body["success"])
```

Place controller tests in `custom_addons/security_mobile/tests/` and run:

```bash
./scripts/run-tests.sh security_mobile
```

### 3. Manual API integration (curl)

Use the curl examples in [API.md](API.md) against a running stack with `security_mobile` installed:

```bash
# Authenticate
curl -s -c /tmp/odoo-cookies.txt -X POST http://localhost:8069/web/session/authenticate \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"call","params":{"db":"dogforce_dev","login":"admin","password":"admin"}}'

# Call supervisor endpoint
curl -s -b /tmp/odoo-cookies.txt \
  http://localhost:8069/api/security/mobile/supervisor/today | python3 -m json.tool
```

Verify:

- HTTP 200 with `"success": true`
- Correct role returns data; wrong role returns 403
- Invalid `record_id` returns 404

---

## End-to-end tests

Full E2E tests cover the mobile app talking to a live Odoo instance. **No automated E2E runner is configured yet.** Use the manual checklist below until Detox, Maestro, or Playwright is added.

### Manual E2E checklist (supervisor flow)

Prerequisites: `./scripts/start.sh`, `./scripts/seed-db.sh`, `security_mobile` installed, mobile app running.

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | Start Expo: `cd mobile && npm start` | Dev server on port 8081 |
| 2 | Log in as supervisor user | Redirected to supervisor home |
| 3 | View today's posting sheet | Guards and shifts listed |
| 4 | Mark a guard present | Status updates; no error toast |
| 5 | Quick check-in | `check_in` timestamp set |
| 6 | Submit batch | Batch state changes to `captured` |

### Manual E2E checklist (manager flow)

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | Log in as manager | Manager dashboard loads |
| 2 | View multi-site summary | All active sites listed with counts |
| 3 | Open site detail | Roster and overtime pending shown |
| 4 | Approve overtime | `overtime_approved: true` in API response |

### Manual E2E checklist (owner flow)

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | Log in as owner | KPI screen loads |
| 2 | View attendance rate | Numeric KPI displayed |
| 3 | View payroll trend | Last 6 months chart/list |

### Physical device testing

When testing on a phone (not simulator), set `ODOO_BASE_URL` in `mobile/src/api/client.ts` to your machine's LAN IP:

```typescript
export const ODOO_BASE_URL = 'http://192.168.1.10:8069';
```

Ensure Docker port `8069` is reachable from the device.

### Planned automated E2E (future)

| Tool | Scope | Notes |
|------|-------|-------|
| [Maestro](https://maestro.mobile.dev/) | Mobile UI flows | YAML-based; works with Expo |
| [Detox](https://wix.github.io/Detox/) | Mobile UI flows | Requires bare/prebuild workflow |
| Playwright | Odoo web UI | For back-office workflows |

---

## Mobile app tests

### TypeScript type check (available now)

Static analysis — catches type errors without running the app:

```bash
cd mobile
npm run ts:check
```

This runs `tsc` with no emit. Add to your pre-PR checklist for any `mobile/` change.

### Unit tests (not yet configured)

When Jest is added, the expected setup is:

```bash
cd mobile
npm install --save-dev jest @testing-library/react-native jest-expo
npm test
npm test -- --coverage
```

Recommended test targets:

| File | What to test |
|------|--------------|
| `src/api/client.ts` | Session header injection |
| `src/stores/authStore.ts` | Login state transitions |
| `src/components/StatusBadge.tsx` | Renders correct label per presence value |

---

## Test coverage reports

Coverage tooling is **not pre-installed** in the repo. Use the steps below to generate reports locally.

### Odoo Python coverage

**Quick method — helper script:**

```bash
./scripts/run-coverage.sh security_payroll_core
open .local/coverage/html/index.html
```

**Manual method:**

```bash
# Install coverage in the Odoo container (once per container rebuild)
docker compose -f deploy/docker-compose.yml exec odoo pip install coverage

# Run tests under coverage
docker compose -f deploy/docker-compose.yml exec odoo sh -c "
  coverage run --source=/mnt/extra-addons/security_payroll_core \
    odoo -c /etc/odoo/odoo.conf \
      -d dogforce_test \
      --test-enable \
      --stop-after-init \
      -i security_payroll_core \
      --log-level=test:INFO
"

# Terminal summary
docker compose -f deploy/docker-compose.yml exec odoo coverage report

# HTML report (inside container)
docker compose -f deploy/docker-compose.yml exec odoo \
  coverage html -d /var/lib/odoo/coverage_html

# Copy report to host
docker compose -f deploy/docker-compose.yml cp \
  dogforce-odoo-dev-odoo:/var/lib/odoo/coverage_html \
  .local/coverage/html
```

Open `.local/coverage/html/index.html` in a browser. Green lines are covered; red lines need tests.

**Cover multiple modules** — run separately per module:

```bash
./scripts/run-coverage.sh security_equipment
./scripts/run-coverage.sh security_fleet
```

`.local/coverage/` is gitignored.

### Mobile TypeScript coverage (when Jest is added)

```bash
cd mobile
npm test -- --coverage
open coverage/lcov-report/index.html
```

Expected output directory: `mobile/coverage/lcov-report/index.html`

---

## Writing new tests

### When tests are required

Per [CONTRIBUTING.md](CONTRIBUTING.md):

| Change type | Test requirement |
|-------------|------------------|
| Payroll / statutory logic | **Required** — `TransactionCase` with edge cases |
| Equipment / fleet workflows | **Required** — follow existing test files |
| New model with constraints | Recommended — at least one validation test |
| Mobile API endpoint | Recommended — `HttpCase` when module tests exist |
| UI-only mobile change | Manual E2E checklist until automated runner exists |
| Documentation | No automated tests |

### Scaffold a new test file

```text
custom_addons/<module>/tests/
├── __init__.py
└── test_<domain>.py
```

`__init__.py`:

```python
from . import test_<domain>
```

Example test skeleton:

```python
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestMyFeature(TransactionCase):

    def setUp(self):
        super().setUp()
        self.record = self.env["my.model"].create({"name": "Test"})

    def test_01_create_record(self):
        self.assertEqual(self.record.name, "Test")

    def test_02_validation_raises(self):
        with self.assertRaises(ValidationError):
            self.env["my.model"].create({"name": False})
```

Run after adding:

```bash
./scripts/run-tests.sh <module_name>
```

---

## Recommended test scenarios (backlog)

High-priority gaps remaining:

| Module | Scenarios to automate |
|--------|----------------------|
| `security_l10n_na` | PAYE bracket boundaries, SSC cap, Sunday/holiday premium, shift split at midnight |
| `security_l10n_zm` | 2026 budget bracket update validation (2025 brackets verified; 2026 rule set marked pending budget confirmation) |
| `security_operations` | Roster eligibility (grade, cert, disqualification, rest rules) |
| `security_mobile` | Auth, role enforcement, mark/checkin/submit happy paths |
| `security_loans` | Deduction schedule on payslip |
| `security_discipline` | Incident → reliability + payslip deduction |
| `security_zra_invoice` | VSDC submission success/rejection, cancellation payload, retry backoff logic |

---

## CI (GitHub Actions)

Workflow: [.github/workflows/ci.yml](.github/workflows/ci.yml)

On every PR and push to `main`:

1. Start Docker Compose (PostgreSQL + Odoo)
2. Run `./scripts/run-tests.sh`
3. Run `cd mobile && npm run ts:check`

See [DEPLOYMENT.md](DEPLOYMENT.md) for staging/production deploy and branch protection setup.

---

## Quick reference

| Task | Command |
|------|---------|
| Run all Odoo tests | `./scripts/run-tests.sh` |
| Run one module | `./scripts/run-tests.sh security_payroll_core` |
| Odoo coverage report | `./scripts/run-coverage.sh security_payroll_core` |
| Open coverage HTML | `open .local/coverage/html/index.html` |
| Mobile type check | `cd mobile && npm run ts:check` |
| API smoke test | See [API.md](API.md) curl examples |
| Shell into Odoo container | `./scripts/odoo-shell.sh` |
| View test logs | `./scripts/logs.sh` |

---

## Related documentation

| Document | Description |
|----------|-------------|
| [CONTRIBUTING.md](CONTRIBUTING.md) | Definition of done and test requirements for PRs |
| [API.md](API.md) | Manual API integration test payloads |
| [INSTALL.md](INSTALL.md) | Database seeding for E2E prerequisites |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Module dependencies for integration test setup |
