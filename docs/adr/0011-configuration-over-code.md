# ADR-0011: Configuration Over Code for Business Rules

**Date:** 2026-05-26  
**Status:** Accepted

## Context

Security companies configure grades, certifications, tax brackets, premium multipliers, incident types, billing plans, and approval thresholds differently. Hardcoding DogForce or Namibia values in Python creates forks and requires developer deploys for routine HR/finance adjustments.

PROJECT_PLAN.md principle #2: business rules must be records/settings.

## Decision

Store variable business rules as **Odoo data records**, not Python constants:

| Rule type | Model / location |
|-----------|------------------|
| Grades, certifications | `security.grade`, `security.certification` |
| PAYE brackets, SSC rates | `security.tax.bracket`, `security.payroll.rule.set` in `security_l10n_na` |
| Public holidays | `security.public.holiday` |
| Incident types | `security.incident.type` |
| Billing rates | `security.billing.plan` / lines |
| Leave types | `security.leave.type` |

Python implements **engines** (compute pipelines, validators); administrators maintain **configuration** via Odoo UI or XML data loads.

## Consequences

### Positive

- DogForce HR/payroll officers can adjust rates without code changes (with appropriate ACLs)
- Demo and UAT datasets swap via `security_demo_data` without touching core
- Localization packs ship XML/CSV data files

### Negative

- Complex rules (shift split at midnight) still need code — configuration has limits
- Misconfigured records can cause silent payroll errors — tests and sign-off required
- More models and views to build and secure

### Neutral

- Test fixtures may still create rule sets inline when XML data is not loaded (`test_payroll.py` fallback)
- CONTRIBUTING.md requires payroll changes to keep rates in configuration where possible
