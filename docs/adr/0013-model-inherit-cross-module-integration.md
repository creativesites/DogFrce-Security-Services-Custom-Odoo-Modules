# ADR-0013: Model Extension for Cross-Module Integration

**Date:** 2026-05-27  
**Status:** Accepted

## Context

Deductions and integrations span modules: loans, discipline incidents, and equipment damage all affect payslips; leave blocks roster slots; accounting controls extend billing invoices; fleet links to incidents.

Integration options in Odoo:

- **Separate services / event bus** — not idiomatic Odoo; high complexity
- **Direct cross-module imports** — tight coupling, circular import risk
- **`_inherit` model extension** — standard Odoo pattern; extend shared models in dependent modules

The module dependency graph is a DAG; extensions flow downstream.

## Decision

Integrate cross-cutting concerns via **`_inherit`** on existing models:

| Extended model | Extended by | Purpose |
|----------------|-------------|---------|
| `hr.employee` | `security_base`, `security_payroll_core`, `security_mobile` | Guard profile, pay fields, mobile session |
| `security.payslip` | `security_loans`, `security_discipline`, `security_equipment` | Inject deduction lines in compute |
| `security.roster.slot` | `security_leave` | Block assignment during leave |
| `security.billing.invoice` | `security_accounting_controls` | Payments and ageing |
| `security.incident` | `security_fleet` | Vehicle linkage |

Use **optional integration** where modules may be absent:

```python
if "security.incident" in self.env:
    ...
```

Workflow methods (`action_compute_from_sources`, `action_generate_payslips`) orchestrate reads — no separate service layer.

## Consequences

### Positive

- Idiomatic Odoo; familiar to Odoo developers
- Install order enforced by manifest `depends`
- Payslip compute stays one transaction — consistent totals

### Negative

- Extension chain can be hard to trace (`security.payslip` touched by three modules)
- Method override order depends on module load order — subtle bugs possible
- No explicit API contract between modules beyond model fields

### Neutral

- ARCHITECTURE.md documents extension table
- Testing integration requires installing full dependency chain (payroll + loans + discipline + equipment)
