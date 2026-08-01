# DeployGuard Cross-Module Synchronization and Reconciliation Plan

**Status:** Approved for planning  
**Date:** 2026-08-01

## Decision

Odoo Accounting is the legal source of truth for posted invoices, payments, reconciliations, refunds, and credit notes. Once posted, `account.move`, `account.payment`, and reconciled journal items define financial truth.

DeployGuard remains authoritative for security operations, including contracts, sites, posts, rosters, attendance interpretation, service delivery, and draft billing proposals. DeployGuard billing mirrors Accounting after posting and must not compete with the ledger.

## Current state

- `security_billing_account` already links `security.billing.invoice` to `account.move` via `move_id`.
- `security.attendance.record` already links to `hr.attendance` via `hr_attendance_id`.
- `security_accounting_controls` provides `security.client.payment` and custom payment-status logic.
- The current bridges lack a shared identity model, durable queue, complete audit trail, common loop prevention, conflict management, and repair tools.

## Guardrails

1. Never reopen and rewrite a posted `account.move` to resemble a DeployGuard invoice.
2. Never create anonymous balancing or delta payments merely to align totals.
3. Never delete a posted Accounting record because the linked DeployGuard record changed or was deleted.
4. Correct posted documents only through Odoo credit-note, reversal, cancellation, and reconciliation workflows.
5. Constrain reconciliation records by `company_id` and normal Odoo record rules.

## Authority matrix

| Priority | DeployGuard model | Native Odoo model | Authority |
|---|---|---|---|
| P0 | `security.billing.invoice` | `account.move` | DeployGuard owns service data and drafts; Accounting owns posted legal state. |
| P0 | `security.client.payment` | `account.payment` | Accounting owns posted payment and reconciliation; DeployGuard mirrors the linked payment. |
| P1 | `security.attendance.record` | `hr.attendance` | DeployGuard owns roster, AWOL, approval, and payable hours; configured capture source owns raw timestamps. |
| P2 | `security.equipment.allocation` | `stock.picking` / `stock.move` | DeployGuard owns custody; Inventory owns completed stock movements. |
| P3 | `security.incident` | `mail.message` / activities | Publish employee-history summary; do not duplicate the case. |
| Backlog | `security.roster.slot` | Planning/calendar | Requires its own approved Planning design. |

## Proposed modules

```text
security_reconciliation_core
├── links, jobs, logs, conflicts, rules, dashboard, scheduled sweeps
├── security_reconciliation_billing_account
├── security_reconciliation_payment_account
├── security_reconciliation_attendance_hr
├── security_reconciliation_equipment_stock       (future)
└── security_reconciliation_incident_chatter       (future)
```

Adapters auto-install only when both paired modules exist. Existing bridges are refactored to call their adapter and must not operate in parallel.

## Core records

- `security.reconciliation.link`: canonical source/target identity, adapter code, company, state, fingerprints, timestamps, and uniqueness constraints.
- `security.reconciliation.job`: durable outbox job with origin, direction, event, minimal payload, correlation ID, retry fields, and state.
- `security.reconciliation.log`: append-only audit record with actor, result, links, correlation ID, and normalized differences.
- `security.reconciliation.conflict`: source/target differences, severity, owner, explicit resolution, and audit note.
- `security.reconciliation.rule`: per-company adapter enablement, thresholds, retry policy, authority settings, and escalation recipients.

Complex accounting mappings remain adapter code; they are not generic JSON `write()` mappings.

## Processing model

Adapters listen only to approved lifecycle transitions: draft invoice changes, invoice posting, payment posting/reconciliation, and approved attendance changes. Each event writes an outbox job in the same transaction; rollback removes both source change and job. An Odoo cron dispatcher processes jobs after commit.

Every adapter write carries an origin, correlation ID, and job ID. Listeners ignore reflected writes from the same adapter. Link uniqueness, fingerprints, and idempotency checks also prevent loops and duplicates.

| Mode | Use |
|---|---|
| Inline validation | Financial precondition checks before invalid actions. |
| Queued synchronization | Normal propagation, bulk work, and retries. |
| Scheduled sweep | Detection of missed events, imports, direct edits, and drift. |

Transient failures use bounded exponential backoff. Unsafe financial differences create a conflict rather than an automatic overwrite. Odoo's durable queue is sufficient initially because both sides are inside one Odoo database.

## Phase 1: invoice and payment reconciliation

1. A DeployGuard invoice may create or update only its linked Accounting draft invoice.
2. Accounting owns journal, taxes, legal lines, totals, and state after posting.
3. A requested post-posting change becomes a correction exception: credit note or reversal plus replacement document where appropriate.
4. Each posted `security.client.payment` links to one real `account.payment`; legal status derives from Accounting residuals and partial reconciliations.
5. Payment differences become unmatched-payment or invoice-balance exceptions; the engine never creates a synthetic delta payment.
6. Bank/mobile-money records begin unmatched. Exact reference matches may later be automated; fuzzy matching requires approval in release one.
7. Credit notes link to `account.move` type `out_refund` and use controlled Accounting refund flow.
8. A nightly sweep detects missing/cross-company links, invoice-line drift, payment differences, and missed mirror updates.

## Phase 2: attendance reconciliation

DeployGuard attendance is a scheduled-shift operational record, while `hr.attendance` is raw check-in/check-out evidence. DeployGuard owns slot, site/post, expected shift, AWOL/no-show, approved overtime, and payable hours. The configured capture source owns timestamps.

Native attendance without a link is a candidate matched by employee/time window, not an automatic overwrite. Missing, extra, employee/site/shift mismatch, and material time variance become exceptions. Deletion normally detaches and raises an exception; it does not erase evidence already used by HR or payroll.

Before payroll finalization, unresolved blocking attendance exceptions stop the period. An authorized override requires a reason and creates an audit entry.

## Later adapters

- Equipment uses stock pickings/transfers, not raw `stock.move` writes, and activates only where Inventory is configured.
- Incidents publish a linked summary/activity on employee chatter; the custom incident remains the case record.
- Roster/Planning is deferred pending a separate domain mapping.

## User experience

Add **Operations → Reconciliation** with a health dashboard, rule management, searchable job queue, side-by-side conflict resolution, financial/attendance exception views, and an audit log searchable by record, actor, date, or correlation ID. The dashboard orchestrates normal Odoo actions and never bypasses Accounting, HR, or access rules.

## Rollout

1. **Discovery:** read-only baseline scanner counts records, existing links, missing targets, duplicates, cross-company errors, and drift.
2. **Backfill:** use existing relational links first, then immutable references plus company/partner/currency checks; ambiguous matches require review.
3. **Shadow mode:** capture events and report differences without propagation for one complete closing cycle.
4. **Financial pilot:** enable draft sync and Accounting-to-DeployGuard legal-state mirroring for one company; retire legacy bridge path.
5. **Attendance pilot:** compare two payroll cycles before enabling the payroll gate.
6. **Optional adapters:** activate only after target workflows are configured and signed off.

## Delivery and acceptance criteria

| Phase | Deliverable | Exit criterion |
|---|---|---|
| 0 | Discovery scanner and baseline | Data-owner sign-off. |
| 1 | Core module | Links, jobs, logs, conflicts, rules, dashboard shell, and record rules tested. |
| 2 | Invoice/payment adapters | Draft sync, legal-state mirror, payment identity, credit notes, and sweep tested. |
| 3 | Financial pilot | One month-end with no duplicate or missing finance record. |
| 4 | Attendance adapter/payroll gate | Two payroll cycles with only approved exceptions. |
| 5 | Optional adapters | Domain-specific criteria met. |

Tests must cover transaction rollback/outbox behavior, idempotent retries, loop prevention, multi-company access, posting, partial/full payment, refund, cancellation, native-only attendance, attendance mismatches, and payroll blocking.

Financial acceptance requires at most one linked Accounting draft, no silent rewrite of posted moves, one traceable Accounting payment per linked payment, no delta payments, proper credit-note flow, visible retryable failures, and a sweep that finds deliberately introduced drift.

## Decisions still needed before build

1. Pilot company/database and Accounting Manager responsible for sign-off.
2. Payment sources for release one: manual receipt, bank, MTN, Airtel, or all.
3. Raw attendance source at each pilot site.
4. Reconciliation-log retention policy.
5. Whether DeployGuard may initiate a controlled Accounting posting action or only mirror Accounting posting.

## ADR impact

`security_billing` remains valid for minimal Community deployments without Accounting. Where Accounting and the reconciliation adapters are installed, Accounting is the legal ledger for posted documents. ADR-0007 should be amended or superseded when implementation begins to record this conditional decision.
