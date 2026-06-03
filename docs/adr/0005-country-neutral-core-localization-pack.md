# ADR-0005: Country-Neutral Core + Localization Pack

**Date:** 2026-05-26  
**Status:** Accepted

## Context

The suite targets DogForce (Namibia) first, then potentially Zambia and other markets. Namibia-specific rules include PAYE brackets, SSC rates, public holidays, VAT wording on invoices, and NAD defaults. Hardcoding these in core modules would force a fork per country.

The project plan explicitly separates:

- **Dogforce implementation** (one client)
- **Reusable Security Suite** (many clients/countries)

## Decision

Split country-specific logic into **localization packs**:

| Scope | Module(s) |
|-------|-----------|
| Country-neutral | `security_base`, `security_operations`, `security_attendance`, `security_leave`, `security_payroll_core` (engine), `security_billing` (structure) |
| Namibia | `security_l10n_na` — rule sets, tax brackets, public holidays, statutory rates |
| Client-specific (planned) | `security_dogforce_migration` — imports, defaults, cutover scripts |
| Demo/sample | `security_demo_data` — Namibian demo records, not for production |

Core modules must not import Namibia-only constants. Payroll engine reads rule sets from `security.payroll.rule.set` records supplied by localization data.

Future countries add `security_l10n_zm` (or similar) depending on the same payroll core.

## Consequences

### Positive

- Zambia deployment reuses operations/attendance; swaps localization module
- Statutory changes (PAYE brackets) update XML/data records, not core Python — when configuration-over-code is followed
- Clear audit boundary for compliance ("Namibia rules live in `security_l10n_na`")

### Negative

- Every new country is a non-trivial module (tax, holidays, invoice legal text)
- Risk of Namibia assumptions leaking into core if reviewers are not vigilant
- `security_l10n_na` sits in the payroll dependency chain — a country-neutral install still pulls it today unless dependency is refactored

### Neutral

- Billing VAT rate is configurable per plan; Namibia default (15%) lives in data and demo hooks
- PROJECT_PLAN.md principle #1 is now enforced structurally
