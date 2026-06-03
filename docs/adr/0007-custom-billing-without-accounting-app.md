# ADR-0007: Custom Billing Model Without Odoo Accounting

**Date:** 2026-05-27  
**Status:** Accepted

## Context

DogForce requires client invoicing: Namibian format, VAT breakdown, amount in words, branding, generation from contracts/attendance, payment tracking, and ageing. Odoo **Accounting** (`account` module) provides `account.move` for invoices, GL posting, and reconciliation — but:

- Accounting is an optional app; Community deployments may not install it
- ADR-0002 commits reusable modules to Community without Enterprise/Accounting dependency
- Security billing rules (per-guard-per-shift, posting sheet sources) are domain-specific

`security_billing` manifest depends only on `security_payroll_core`, not `account`.

## Decision

Implement billing as **custom models**:

- `security.billing.plan`, `security.billing.invoice`, `security.billing.invoice.line`
- VAT, amount-in-words, and PDF report in-module (`reports/security_invoice_report.xml`)
- Payment tracking in `security_accounting_controls` via `security.client.payment` extending the custom invoice

Do **not** require `account.move` for core billing workflows. Optionally read `account.move` in owner KPIs when Accounting is installed.

A future **bridge module** may sync `security.billing.invoice` → `account.move` for full GL integration.

## Consequences

### Positive

- Billing works on a minimal Community install (HR + custom modules only)
- Invoice layout tailored to Namibian security contracts without fighting Accounting report templates
- Clear domain model aligned with roster/attendance generation sources

### Negative

- No automatic general ledger posting; double-entry accounting is manual or requires future bridge
- Bank reconciliation specification largely unimplemented — duplicate effort vs Accounting app
- Two sources of truth if both custom invoices and `account.move` are used without sync

### Neutral

- Client service reports (`security_client_reports`) aggregate same attendance data as billing
- ARCHITECTURE.md flags this as architectural debt to resolve before full finance go-live
