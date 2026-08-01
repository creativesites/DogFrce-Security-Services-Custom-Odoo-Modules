# DeployGuard Cross-Module Synchronization & Reconciliation Guide

**Author:** DeployGuard Architecture Team  
**Date:** 2026-08-01  
**Status:** Operational / Active  

---

## 1. Executive Summary & Core Principles

DeployGuard Cross-Module Synchronization & Reconciliation provides reliable, durable, and auditable data flow between DeployGuard's security operations modules and native Odoo core models (Accounting, HR, Stock, Chatter).

### Key Architectural Principles

1. **Accounting is Legal Financial Truth:** Once an `account.move` or `account.payment` is posted in Odoo Accounting, it represents the legal general ledger. DeployGuard mirrors Accounting after posting and never competes with or overrides posted financial entries.
2. **DeployGuard is Operational Truth:** DeployGuard owns site requirements, roster slots, shift delivery, attendance interpretation, and draft billing proposals.
3. **Outbox Pattern with Durable Queuing:** Operational events write durable job entries into `security.reconciliation.job` within the same transaction. A dispatcher cron executes jobs asynchronously with bounded exponential retries.
4. **Post-Posting Guardrail (No Direct Rewrites):** Posted `account.move` records are never reopened (`button_draft()`) or directly edited. Material financial differences generate an open `security.reconciliation.conflict` for accountant review.
5. **No Synthetic Delta Payments:** Payment differences create invoice-balance or payment-mismatch exception records; the system never creates anonymous balancing payments.
6. **Multi-Company Isolation:** All rules, links, jobs, conflicts, and audit logs are strictly isolated by `company_id`.

---

## 2. System Architecture

```text
security_reconciliation_core
├── security.reconciliation.rule     (Multi-company rules & adapter settings)
├── security.reconciliation.link     (Canonical source <-> target record identities)
├── security.reconciliation.job      (Outbox job queue with retries & correlation IDs)
├── security.reconciliation.log      (Append-only audit log)
└── security.reconciliation.conflict (Financial & operational exception workspace)
      │
      ├── security_reconciliation_billing_account (Invoice, payment & credit note adapter)
      ├── security_reconciliation_attendance_hr  (Attendance & HR adapter)
      └── security_reconciliation_equipment_stock (Equipment & Inventory adapter)
```

---

## 3. How It Works: Billing & Accounting Synchronization

### 3.1 Draft Invoice Synchronization
- **Trigger:** A draft `security.billing.invoice` is created or modified.
- **Action:** Enqueues a job for adapter `billing_account_invoice`. The adapter creates or updates a draft `account.move` (`type='out_invoice'`) and registers a `security.reconciliation.link`.
- **Line Mapping:** Services, guard quantities, rate card unit prices, and sales taxes are synced cleanly to `invoice_line_ids`.

### 3.2 Invoice Validation & Posting
- **Trigger:** DeployGuard invoice transitions to `sent` or `paid`.
- **Action:** The adapter posts the linked draft `account.move` (`move.action_post()`).

### 3.3 Post-Posting Guardrails & Conflict Management
- **Scenario:** A user attempts to edit lines or amounts on a `security.billing.invoice` whose linked `account.move` is already posted in Accounting.
- **Guardrail Action:**
  - The adapter detects `move.state == 'posted'`.
  - It compares calculated DeployGuard totals against `move.amount_total`.
  - Because posted moves cannot be rewritten, the adapter **does NOT alter `account.move`**.
  - It creates a `security.reconciliation.conflict` with `severity='financial'` detailing the exact total mismatch.
  - The job marks itself as `conflict` and records an audit entry in `security.reconciliation.log`.

### 3.4 Payment Reconciliation
- **Trigger:** A `security.client.payment` is posted against a DeployGuard invoice.
- **Action:** The adapter registers the payment on the posted `account.move` using standard payment journal entries.
- **Mismatch Policy:** If payments do not match the residual balance, an open conflict is flagged for manual review rather than creating synthetic delta payments.

### 3.5 Credit Notes & Adjustments
- **Trigger:** A `security.billing.credit.note` is confirmed or applied.
- **Action:** Generates and posts a linked `account.move` of type `out_refund` (Customer Refund), maintaining full audit compliance.

### 3.6 Nightly Discovery Sweep
- **Trigger:** Automated nightly cron (`ir_cron_reconciliation_billing_sweep`).
- **Action:** Scans all active companies for unlinked invoices, payment state drift, or un-reconciled residuals, auto-generating outbox jobs to restore alignment.

---

## 4. User Workspace & Operational Workflows

To access the Reconciliation Admin Workspace in Odoo:
Navigating to **Operations → Reconciliation** opens five dedicated tabs:

### 1. Conflicts (`security.reconciliation.conflict`)
- View all open financial or operational differences.
- Review side-by-side field diffs (`field_diffs_json`).
- Action: **Assign to Me** → Choose Resolution (**Use Source**, **Use Target**, **Manual Adjustment**, or **Ignore**) → Provide an Audit Note → Click **Resolve**.

### 2. Sync Jobs (`security.reconciliation.job`)
- Monitor pending, running, retry, conflict, and failed jobs.
- View attempt counts, correlation IDs, and detailed exception tracebacks.
- Actions: **Requeue Job** (for transient failures) or **Cancel Job**.

### 3. Record Links (`security.reconciliation.link`)
- View active relational links between DeployGuard records and Odoo models.
- Click **Open Source Record** or **Open Target Record** to navigate directly to linked forms.

### 4. Sync Rules (`security.reconciliation.rule`)
- Enable or disable reconciliation rules per company.
- Configure retry policies (`max_attempts`, `retry_delay_minutes`), conflict policies, and handler methods.

### 5. Audit Log (`security.reconciliation.log`)
- Search append-only execution history by actor, result (`done`, `conflict`, `retry`, `failed`), correlation ID, or timestamp.

---

## 5. Troubleshooting & Best Practices

| Issue | Root Cause | Recommended Action |
|---|---|---|
| Job in `retry` state | Temporary database lock or network timeout. | Wait for next retry cycle or click **Requeue Job** in Sync Jobs view. |
| Job in `conflict` state | Post-posting edit attempt or payment total mismatch. | Open **Reconciliation → Conflicts**, inspect field diffs, issue a Credit Note or adjust in Accounting, and mark conflict resolved. |
| Missing linked invoice | Invoice created prior to module installation. | Run **Nightly Sweep** or click **View Odoo Invoice** on the invoice form to force instant sync. |

---
