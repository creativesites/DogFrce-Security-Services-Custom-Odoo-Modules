# Contributing to DogForce Security Suite

Thank you for contributing. This guide defines how we work in Git, what we expect in pull requests, coding conventions, and when a task is considered done.

For local setup, see [INSTALL.md](INSTALL.md). For system design, see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Git workflow

We use a **trunk-based workflow** with short-lived branches and pull requests into `main`.

```text
main ─────────────────────────────────────────────▶ (always deployable)
  │
  ├── feature/roster-validation
  ├── bugfix/attendance-batch-field-name
  └── docs/install-guide
```

### Branch rules

1. **`main` is protected** — do not push directly. Open a pull request.
2. **Branch from latest `main`** before starting work:

   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/your-task-name
   ```

3. **Keep branches small and focused** — one logical change per PR (one module feature, one bug fix, or one doc update).
4. **Rebase or merge `main` frequently** to avoid large conflicts.
5. **Delete branches** after the PR is merged.

### Branch naming conventions

Use lowercase kebab-case after the prefix.

| Prefix | Use when | Example |
|--------|----------|---------|
| `feature/` | New capability or enhancement | `feature/mobile-overtime-approval` |
| `bugfix/` | Defect fix | `bugfix/payslip-ssc-cap-calculation` |
| `hotfix/` | Urgent production fix (same naming rules, fast-track review) | `hotfix/invoice-vat-rounding` |
| `refactor/` | Behaviour-preserving code change | `refactor/attendance-compute-fields` |
| `test/` | Test-only additions or fixes | `test/fleet-shuttle-manifest` |
| `docs/` | Documentation-only changes | `docs/contributing-guide` |
| `chore/` | Tooling, dependencies, CI, scripts | `chore/seed-db-script` |

**Rules:**

- Use descriptive names — `feature/roster` is too vague; `feature/roster-eligibility-constraints` is better.
- Match the primary module when possible — e.g. `feature/security_billing-vat-breakdown`.
- Do not include issue numbers in branch names; link issues in the PR instead.

### Commit messages

Write clear, imperative subject lines:

```text
Add overtime approval endpoint for mobile managers

Fix attendance batch domain using attendance_batch_id

Update INSTALL.md with seed-db workflow
```

Guidelines:

- Subject line ≤ 72 characters
- Optional body explaining **why**, not just what
- Reference issues as `Fixes #123` or `Refs #123` in the body or PR description

### Pull requests

1. Push your branch and open a PR against `main`.
2. Fill in the [pull request template](.github/pull_request_template.md).
3. Request review from a maintainer.
4. Address feedback with additional commits or a squash before merge (team preference: **squash merge** for feature branches to keep `main` history clean).
5. Ensure CI checks pass once configured (see [Checks before opening a PR](#checks-before-opening-a-pr)).

---

## Pull request template

Every PR should use the template at [.github/pull_request_template.md](.github/pull_request_template.md). At minimum, include:

| Section | Required |
|---------|----------|
| **Summary** | Yes — what changed and why |
| **Type of change** | Yes |
| **Modules affected** | Yes for code changes |
| **Test plan** | Yes — steps or commands a reviewer can run |
| **Checklist** | Yes — confirm access rules, tests, no secrets |

Copy-paste minimum for small fixes:

```markdown
## Summary
Fix field name in mobile supervisor endpoint so posting sheet query returns records.

## Type of change
- [x] Bug fix

## Modules affected
- security_mobile

## Test plan
- [x] `./scripts/start.sh`
- [x] Install `security_mobile`, call `GET /api/security/mobile/supervisor/today` as supervisor user

## Checklist
- [x] Branch name follows convention
- [x] Scope limited to the task
- [x] No secrets committed
```

---

## Coding style guide

There is no repo-wide CI linter yet. Follow the conventions below and run the available local checks before opening a PR.

### Python — Odoo modules (`custom_addons/`)

Follow [Odoo coding guidelines](https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html) and patterns already used in this codebase.

| Topic | Convention |
|-------|------------|
| **Indentation** | 4 spaces, no tabs |
| **Line length** | Soft limit 100 characters |
| **Imports** | `from odoo import api, fields, models` — stdlib, then Odoo, then local |
| **Model names** | `security.<snake_case>` e.g. `security.roster.slot` |
| **Python files** | `security_<domain>.py` matching the model domain |
| **Class names** | PascalCase, e.g. `SecurityRosterSlot` |
| **Field names** | `snake_case`; prefix extensions with module domain e.g. `security_grade_id` |
| **Methods** | `snake_case`; workflow actions prefixed with `action_` e.g. `action_generate_payslips` |
| **Compute methods** | `_compute_<field_name>` with explicit `@api.depends` |
| **Constraints** | `_check_<rule>` with `@api.constrains` |
| **Security** | Every new model needs entries in `security/ir.model.access.csv` |
| **XML IDs** | `<module_name>.<record_name>` e.g. `security_base.grade_a` |
| **Manifest** | Version `19.0.x.y.z`; declare all `depends`; list XML/CSV in `data` |

**Odoo-specific rules:**

- Prefer `_inherit` over duplicating models.
- Keep business logic in Python models, not in XML or controllers.
- Use `tracking=True` on fields that supervisors/HR need to audit.
- Raise `ValidationError` / `UserError` for user-facing failures.
- Country-specific logic belongs in `security_l10n_na`, not core modules.

**Recommended local tools (optional, not yet enforced in CI):**

| Tool | Purpose |
|------|---------|
| [pylint-odoo](https://github.com/OCA/pylint-odoo) | Odoo-aware Python linting |
| [ruff](https://docs.astral.sh/ruff/) | Fast Python lint + format (PEP 8) |
| [black](https://black.readthedocs.io/) | Python formatting (88-char line length) |

Example local run inside the Odoo container:

```bash
./scripts/odoo-shell.sh
python3 -m py_compile /mnt/extra-addons/security_attendance/models/security_attendance.py
```

### XML — views, menus, security, reports

| Topic | Convention |
|-------|------------|
| **Indentation** | 4 spaces |
| **Record IDs** | Descriptive snake_case prefixed by module |
| **View order** | Form, list/tree, search, then actions/menus |
| **Menus** | Define in `*_menu.xml`; keep hierarchy shallow |
| **Reports** | QWeb templates in `reports/`; link from model print action |

Validate XML loads by upgrading the module:

```bash
docker compose -f deploy/docker-compose.yml exec odoo odoo \
  -c /etc/odoo/odoo.conf -d dogforce_dev -u <module_name> --stop-after-init
```

### TypeScript — mobile app (`mobile/`)

| Topic | Convention |
|-------|------------|
| **Indentation** | 2 spaces |
| **Quotes** | Single quotes for strings |
| **Semicolons** | Yes |
| **Naming** | `camelCase` for variables/functions; `PascalCase` for components and types |
| **Files** | Components in `src/components/`; API clients in `src/api/` |
| **Routes** | Expo Router file-based routes under `app/` |
| **State** | Zustand stores in `src/stores/` |
| **API responses** | Use typed interfaces; handle `{ success, data | error }` envelope from Odoo |

**Available checks today:**

```bash
cd mobile
npm run ts:check    # TypeScript compiler — no emit
```

**Recommended local tools (optional, not yet in repo):**

| Tool | Purpose |
|------|---------|
| ESLint | Lint rules for React Native / Expo |
| Prettier | Consistent TS/TSX formatting |

### Shell scripts (`scripts/`)

- Use `#!/bin/sh` with `set -eu`
- Source `docker-env.sh` for Docker/Compose paths
- Read configuration from `.env`, never hardcode secrets

### What we do not commit

- `.env` or credentials
- `.local/` runtime data
- IDE-specific files (already in `.gitignore`)
- Unrelated formatting-only changes mixed into feature PRs

---

## Checks before opening a PR

Run what applies to your change:

### Odoo backend

```bash
./scripts/start.sh

# Fresh install or upgrade of changed modules
./scripts/seed-db.sh   # or targeted -u <module>

# Module tests (when they exist for your area)
./scripts/odoo-shell.sh
odoo -d dogforce_dev --test-enable -i security_payroll_core --stop-after-init
```

### Mobile app

```bash
cd mobile
npm install
npm run ts:check
npm start   # manual smoke test against local Odoo
```

### Documentation

If you change setup, architecture, or API behaviour, update the relevant doc:

- [INSTALL.md](INSTALL.md) — setup or env changes
- [ARCHITECTURE.md](ARCHITECTURE.md) — design or data-flow changes
- [docs/security_mobile.md](docs/security_mobile.md) — mobile API changes

---

## Definition of done

A task is **done** when it meets the criteria below. Use this for your own checklist and PR review.

### All tasks

- [ ] Acceptance criteria from the issue/backlog item are met
- [ ] Code is on a correctly named branch and merged via PR to `main`
- [ ] PR template is complete with a reproducible test plan
- [ ] Change is scoped — no drive-by refactors or unrelated files
- [ ] `./scripts/start.sh` works; affected modules install or upgrade without traceback
- [ ] No secrets, debug prints, or commented-out dead code left behind
- [ ] Another developer could verify the change using only the PR test plan

### Odoo module changes

- [ ] `__manifest__.py` updated (`depends`, `data`, version bump if releasing)
- [ ] `security/ir.model.access.csv` updated for new models or permission changes
- [ ] Security groups / record rules updated if visibility changed
- [ ] Menu and views added for user-facing features
- [ ] Business logic lives in models; controllers only for HTTP/API boundaries
- [ ] Module installs cleanly on a fresh database (`./scripts/seed-db.sh`) or documents manual steps

### Payroll, statutory, or financial logic

- [ ] Automated tests added or updated in `tests/` using `TransactionCase`
- [ ] Tests cover happy path and at least one edge case (caps, brackets, zero hours, etc.)
- [ ] Rates and rules remain **configuration records**, not hardcoded constants (unless test fixtures)
- [ ] Test command and results noted in the PR

### Mobile / API changes

- [ ] `security_mobile` endpoint documented in PR or `docs/security_mobile.md`
- [ ] Group-based access enforced (`@require_group`)
- [ ] JSON response uses `{ success, data | error }` envelope
- [ ] `npm run ts:check` passes
- [ ] Tested against local Odoo with `security_mobile` installed

### Bug fixes

- [ ] Root cause addressed, not only symptoms
- [ ] Regression test added when feasible
- [ ] Branch named `bugfix/<short-description>`

### Documentation tasks

- [ ] Links between README, INSTALL, ARCHITECTURE, and CONTRIBUTING stay consistent
- [ ] Commands copy-paste and match actual scripts in `scripts/`

---

## Module ownership quick reference

When unsure where code belongs:

| Change type | Module |
|-------------|--------|
| Guard profiles, grades, groups | `security_base` |
| Sites, posts, rosters | `security_operations` |
| Posting sheets, attendance metrics | `security_attendance` |
| Leave balances and requests | `security_leave` |
| Namibia PAYE/SSC/holidays | `security_l10n_na` |
| Payslips and payroll periods | `security_payroll_core` |
| Client invoices | `security_billing` |
| Mobile REST API | `security_mobile` |
| Demo/sample data | `security_demo_data` |

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full dependency graph.

---

## Getting help

- **Setup issues** — [INSTALL.md](INSTALL.md) troubleshooting section
- **Scope / design questions** — [docs/PLATFORM_MASTER_PLAN.md](docs/PLATFORM_MASTER_PLAN.md) and [ARCHITECTURE.md](ARCHITECTURE.md)
- **Mobile API** — [docs/security_mobile.md](docs/security_mobile.md)

When opening a PR, tag the relevant module in the title, e.g. `security_payroll_core: add Sunday premium split across midnight`.
