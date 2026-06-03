# ADR-0006: Custom Payroll Engine in security_payroll_core

**Date:** 2026-05-26  
**Status:** Accepted

## Context

Namibia payroll requires PAYE, SSC (with caps), Sunday/public holiday/night/overtime premiums, shift splitting across midnight, loan deductions, behavioral deductions, and no-work-no-pay from attendance. Odoo Community has **no built-in payroll app**. Odoo Enterprise Payroll exists on DogForce production but is proprietary and not a dependency for the reusable suite.

Alternatives considered:

- **OCA payroll modules** — may not cover Namibia statutory rules
- **Enterprise Payroll adapter** — ties reusable suite to licensed app
- **Custom payroll engine** — full control, testable, Community-compatible

PROJECT_PLAN.md states payroll calculations must be test-driven.

## Decision

Build a **custom payroll engine** in `security_payroll_core`:

- Models: `security.payroll.period`, `security.payslip`, earning/deduction lines
- Pipeline: `action_generate_payslips()` → `action_compute_from_sources()` pulling attendance, loans, incidents, equipment damage
- Statutory rates from `security_l10n_na` configuration records
- Automated tests in `tests/test_payroll.py` using `TransactionCase`

If Enterprise Payroll is adopted later, this module should become an **adapter** feeding computed hours/deductions into Enterprise — not duplicate Enterprise payslip UI.

## Consequences

### Positive

- Full control over Namibia rules with unit tests to N$0.01 tolerance (project goal)
- Payslip PDF via QWeb without Enterprise
- Cross-module deductions via `_inherit` on `security.payslip` (loans, discipline, equipment)

### Negative

- High maintenance burden — tax law changes require developer updates and sign-off
- Legal/payroll liability: DogForce finance must manually verify before go-live (documented in PROJECT_PLAN.md)
- Feature gap vs Enterprise Payroll (payslip batches, accounting integration hooks, employee self-service)

### Neutral

- SSC/PAYE bracket models are data-driven (`security.tax.bracket`, `security.payroll.rule.set`)
- Only three modules have tests today; payroll tests are the most comprehensive
