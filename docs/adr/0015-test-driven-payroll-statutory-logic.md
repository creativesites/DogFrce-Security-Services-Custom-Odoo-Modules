# ADR-0015: Test-Driven Payroll and Statutory Logic

**Date:** 2026-05-27  
**Status:** Accepted

## Context

Payroll errors have legal and financial consequences: incorrect PAYE, SSC, or premium calculations affect guard pay and DogForce compliance filings. Manual spreadsheet verification does not scale across releases.

Odoo provides `TransactionCase` for in-database tests with automatic rollback. PROJECT_PLAN.md principle #6: every tax, SSC, premium, and deduction rule needs automated tests.

Most modules in the suite have **no tests yet**; payroll is the highest-risk surface.

## Decision

Treat **payroll and statutory logic as test-driven**:

- Mandatory `TransactionCase` tests for `security_payroll_core` before merging payroll changes
- Cover happy paths and edge cases: low/high income, SSC cap, bracket boundaries, period workflow
- Extend pattern to equipment/fleet where payroll deductions are affected
- CI runs `./scripts/run-tests.sh` on every PR (payroll, equipment, fleet)

CONTRIBUTING.md definition of done requires tests for payroll/statutory changes.

## Consequences

### Positive

- Regressions caught before deploy; supports DogForce finance sign-off process
- Tests document expected Namibia calculation behavior as executable specs
- CI gate prevents silent breakage on `main`

### Negative

- Tests are slow (Odoo DB bootstrap per run) — mitigated by `--test-tags` for single tests
- Attendance, leave, and mobile API still lack tests — coverage is uneven
- Test fixtures duplicate localization data when XML not loaded

### Neutral

- TESTING.md documents run commands and coverage via `run-coverage.sh`
- Future `security_l10n_na` tests should cover bracket boundaries without going through full payslip pipeline
