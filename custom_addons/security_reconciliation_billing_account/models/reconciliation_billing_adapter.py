import hashlib
import json

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class SecurityReconciliationBillingAdapter(models.AbstractModel):
    _name = "security.reconciliation.billing.adapter"
    _description = "Reconciliation Adapter — Billing & Accounting"

    @api.model
    def _get_or_create_rule(self, company_id):
        Rule = self.env["security.reconciliation.rule"]
        rule = Rule.search([
            ("company_id", "=", company_id.id if hasattr(company_id, "id") else company_id),
            ("adapter_code", "=", "billing_account_invoice"),
            ("active", "=", True),
        ], limit=1)
        if not rule:
            rule = Rule.create({
                "name": f"Invoice Reconciliation ({company_id.name if hasattr(company_id, 'name') else 'Default'})",
                "company_id": company_id.id if hasattr(company_id, "id") else company_id,
                "adapter_code": "billing_account_invoice",
                "source_model": "security.billing.invoice",
                "target_model": "account.move",
                "handler_model": "security.reconciliation.billing.adapter",
                "handler_method": "_process_reconciliation_job",
                "sync_direction": "bidirectional",
                "sync_mode": "queued",
                "conflict_policy": "manual",
            })
        return rule

    @api.model
    def _process_reconciliation_job(self, job):
        """Main dispatcher for billing reconciliation jobs."""
        if job.origin_model == "security.billing.invoice":
            self._sync_invoice(job)
        elif job.origin_model == "security.client.payment":
            self._sync_client_payment(job)
        elif job.origin_model == "security.billing.credit.note":
            self._sync_credit_note(job)
        elif job.origin_model == "account.move":
            self._sync_account_move(job)
        elif job.origin_model == "account.payment":
            self._sync_account_payment(job)
        else:
            job._log("skipped", f"Unsupported origin model: {job.origin_model}")

    # ═══════════════════════════════════════════════════════════════════════════
    # 1. INVOICE RECONCILIATION & SYNC
    # ═══════════════════════════════════════════════════════════════════════════
    @api.model
    def _sync_invoice(self, job):
        Invoice = self.env["security.billing.invoice"]
        Link = self.env["security.reconciliation.link"]
        Conflict = self.env["security.reconciliation.conflict"]
        
        inv = Invoice.browse(job.origin_res_id)
        if not inv.exists():
            job._log("skipped", f"Invoice #{job.origin_res_id} no longer exists.")
            return

        link = Link.search([
            ("rule_id", "=", job.rule_id.id),
            ("source_model", "=", "security.billing.invoice"),
            ("source_res_id", "=", inv.id),
        ], limit=1)

        move = inv.move_id
        if move and move.exists():
            # Ensure link is populated
            if not link:
                link = Link.create({
                    "rule_id": job.rule_id.id,
                    "company_id": job.company_id.id,
                    "source_model": "security.billing.invoice",
                    "source_res_id": inv.id,
                    "target_model": "account.move",
                    "target_res_id": move.id,
                    "external_key": f"INV-{inv.id}->MOVE-{move.id}",
                    "state": "active",
                })

            # GUARDRAIL 1: Accounting is authoritative for posted moves!
            if move.state == "posted":
                # Check for material financial line/amount drift
                calc_total = getattr(inv, "total_amount", 0.0) or getattr(inv, "amount_total", 0.0)
                move_total = move.amount_total
                
                if abs(calc_total - move_total) > 0.01:
                    diff_data = {
                        "deployguard_invoice_id": inv.id,
                        "deployguard_name": inv.name,
                        "deployguard_total": calc_total,
                        "account_move_id": move.id,
                        "account_move_name": move.name,
                        "account_move_total": move_total,
                        "difference": abs(calc_total - move_total),
                        "message": _("Posted Accounting Invoice total (%s) differs from DeployGuard draft/updated total (%s). Posted moves cannot be rewritten directly.") % (move_total, calc_total),
                    }
                    existing_conflict = Conflict.search([
                        ("job_id", "=", job.id),
                        ("state", "in", ("open", "assigned")),
                    ], limit=1)
                    if not existing_conflict:
                        Conflict.create({
                            "job_id": job.id,
                            "rule_id": job.rule_id.id,
                            "link_id": link.id if link else False,
                            "company_id": job.company_id.id,
                            "severity": "financial",
                            "state": "open",
                            "field_diffs_json": diff_data,
                            "resolution_note": "Awaiting accountant review / credit note adjustment.",
                        })
                    job._log("conflict", _("Financial mismatch on posted move. Created conflict entry."), diff_data)
                    raise ValidationError(_("Financial mismatch on posted move %s: Accounting total is %s but DeployGuard total is %s.") % (move.name, move_total, calc_total))

                # Mirror Accounting Payment State to DeployGuard
                if move.payment_state in ("paid", "in_payment") and inv.state != "paid":
                    inv.with_context(reconciliation_origin="billing_account_invoice").write({"state": "paid"})
                    job._log("done", _("Mirrored 'paid' status from posted account.move %s") % move.name)
                elif move.payment_state not in ("paid", "in_payment") and inv.state == "paid":
                    # Check payment residual mismatch
                    if move.amount_residual > 0.01:
                        job._log("skipped", _("Account move %s has residual balance %s.") % (move.name, move.amount_residual))
                return

        # ─── SYNC DRAFT/NEW INVOICE TO ACCOUNTING ────────────────────────────
        journal = self.env["account.journal"].search([
            ("type", "=", "sale"),
            ("company_id", "=", job.company_id.id),
        ], limit=1)

        if not journal:
            job._log("retry", _("No Sales Journal configured for company %s. Retry later.") % job.company_id.name)
            raise UserError(_("No Sales Journal found for company %s.") % job.company_id.name)

        move_vals = {
            "move_type": "out_invoice",
            "partner_id": inv.partner_id.id,
            "invoice_date": inv.invoice_date or fields.Date.context_today(self),
            "invoice_date_due": getattr(inv, "due_date", False) or inv.invoice_date or fields.Date.context_today(self),
            "currency_id": inv.currency_id.id if inv.currency_id else self.env.company.currency_id.id,
            "ref": inv.name,
            "journal_id": journal.id,
            "company_id": job.company_id.id,
        }

        if not move:
            move = self.env["account.move"].with_context(reconciliation_origin="billing_account_invoice").create(move_vals)
            inv.with_context(reconciliation_origin="billing_account_invoice").write({"move_id": move.id})
        else:
            if move.state == "draft":
                move.with_context(reconciliation_origin="billing_account_invoice").write(move_vals)

        # Update lines
        tax = self.env["account.tax"].search([
            ("type_tax_use", "=", "sale"),
            ("company_id", "=", job.company_id.id),
        ], limit=1)

        product = self.env["product.product"].search([
            ("name", "ilike", "Security"),
            ("type", "=", "service"),
            ("company_id", "in", (False, job.company_id.id)),
        ], limit=1)

        if move.state == "draft":
            line_vals = [(5, 0, 0)]
            for line in inv.line_ids:
                guard_cnt = getattr(line, "guard_count", 1) or 1
                qty = (line.quantity or 1.0) * max(guard_cnt, 1)
                line_vals.append((0, 0, {
                    "name": line.name or "Security Service",
                    "quantity": qty,
                    "price_unit": line.unit_price or 0.0,
                    "product_id": product.id if product else False,
                    "tax_ids": [(6, 0, [tax.id])] if tax else [],
                }))
            if line_vals:
                move.with_context(reconciliation_origin="billing_account_invoice").write({"invoice_line_ids": line_vals})

        # Ensure Link is registered
        if not link:
            link = Link.create({
                "rule_id": job.rule_id.id,
                "company_id": job.company_id.id,
                "source_model": "security.billing.invoice",
                "source_res_id": inv.id,
                "target_model": "account.move",
                "target_res_id": move.id,
                "external_key": f"INV-{inv.id}->MOVE-{move.id}",
                "state": "active",
            })

        # Post Accounting move if DeployGuard invoice is sent or paid
        if inv.state in ("sent", "paid") and move.state == "draft":
            move.with_context(reconciliation_origin="billing_account_invoice").action_post()

        job._log("done", _("Successfully synchronized DeployGuard invoice %s with Odoo account.move %s") % (inv.name, move.name))

    # ═══════════════════════════════════════════════════════════════════════════
    # 2. CLIENT PAYMENT RECONCILIATION & SYNC
    # ═══════════════════════════════════════════════════════════════════════════
    @api.model
    def _sync_client_payment(self, job):
        Payment = self.env["security.client.payment"]
        Link = self.env["security.reconciliation.link"]
        Conflict = self.env["security.reconciliation.conflict"]

        payment = Payment.browse(job.origin_res_id)
        if not payment.exists() or payment.state != "posted":
            job._log("skipped", _("Client Payment #%s is not posted or no longer exists.") % job.origin_res_id)
            return

        inv = payment.invoice_id
        if not inv or not inv.move_id or inv.move_id.state != "posted":
            job._log("skipped", _("Payment #%s has no posted account.move linked.") % payment.id)
            return

        move = inv.move_id
        journal = self.env["account.journal"].search([
            ("type", "in", ("bank", "cash")),
            ("company_id", "=", job.company_id.id),
        ], limit=1)

        if not journal:
            job._log("retry", _("No Bank/Cash Journal configured for payment sync."))
            return

        # Register payment on posted move if move still has residual amount
        if move.amount_residual > 0.01:
            pay_amount = min(payment.amount, move.amount_residual)
            if pay_amount > 0:
                register_wizard = self.env["account.payment.register"].with_context(
                    active_model="account.move",
                    active_ids=move.ids,
                    reconciliation_origin="billing_account_invoice",
                ).create({
                    "amount": pay_amount,
                    "payment_date": payment.payment_date or fields.Date.context_today(self),
                    "journal_id": journal.id,
                })
                register_wizard.action_create_payments()

        # Check for un-reconciled residual discrepancy
        if abs(move.amount_residual) > 0.01 and inv.state == "paid":
            diff_data = {
                "deployguard_payment_id": payment.id,
                "payment_amount": payment.amount,
                "account_move_id": move.id,
                "account_move_residual": move.amount_residual,
                "message": _("Invoice is marked paid in DeployGuard, but Accounting move %s has remaining residual %s.") % (move.name, move.amount_residual),
            }
            Conflict.create({
                "job_id": job.id,
                "rule_id": job.rule_id.id,
                "company_id": job.company_id.id,
                "severity": "financial",
                "state": "open",
                "field_diffs_json": diff_data,
                "resolution_note": "Awaiting payment reconciliation in Accounting.",
            })
            job._log("conflict", _("Payment residual conflict on move %s.") % move.name, diff_data)
            return

        job._log("done", _("Successfully reconciled payment #%s against move %s") % (payment.id, move.name))

    # ═══════════════════════════════════════════════════════════════════════════
    # 3. CREDIT NOTE RECONCILIATION & SYNC
    # ═══════════════════════════════════════════════════════════════════════════
    @api.model
    def _sync_credit_note(self, job):
        CreditNote = self.env["security.billing.credit.note"]
        Link = self.env["security.reconciliation.link"]

        cn = CreditNote.browse(job.origin_res_id)
        if not cn.exists() or cn.state not in ("confirmed", "applied"):
            job._log("skipped", _("Credit Note #%s is draft or missing.") % job.origin_res_id)
            return

        move = cn.move_id
        if not move:
            refund_vals = {
                "move_type": "out_refund",
                "partner_id": cn.partner_id.id,
                "invoice_date": cn.date or fields.Date.context_today(self),
                "ref": f"Credit Note for {cn.invoice_id.name if cn.invoice_id else 'Customer'}: {cn.reason or ''}",
                "currency_id": cn.currency_id.id if cn.currency_id else self.env.company.currency_id.id,
                "company_id": job.company_id.id,
                "invoice_line_ids": [(0, 0, {
                    "name": f"Credit Note: {cn.reason or 'Adjustment'}",
                    "quantity": 1.0,
                    "price_unit": cn.amount or 0.0,
                })],
            }
            move = self.env["account.move"].with_context(reconciliation_origin="billing_account_invoice").create(refund_vals)
            cn.with_context(reconciliation_origin="billing_account_invoice").write({"move_id": move.id})

        if move.state == "draft" and cn.state in ("confirmed", "applied"):
            move.with_context(reconciliation_origin="billing_account_invoice").action_post()

        # Ensure Link
        Link.create({
            "rule_id": job.rule_id.id,
            "company_id": job.company_id.id,
            "source_model": "security.billing.credit.note",
            "source_res_id": cn.id,
            "target_model": "account.move",
            "target_res_id": move.id,
            "external_key": f"CN-{cn.id}->REFUND-{move.id}",
            "state": "active",
        })

        job._log("done", _("Synchronized Credit Note %s with out_refund move %s") % (cn.name, move.name))

    @api.model
    def _sync_account_move(self, job):
        """Odoo account.move state change listener -> update DeployGuard invoice."""
        move = self.env["account.move"].browse(job.origin_res_id)
        if not move.exists():
            return

        inv = self.env["security.billing.invoice"].search([("move_id", "=", move.id)], limit=1)
        if not inv:
            return

        if move.payment_state in ("paid", "in_payment") and inv.state != "paid":
            inv.with_context(reconciliation_origin="billing_account_invoice").write({"state": "paid"})
            job._log("done", _("Updated DeployGuard invoice %s to 'paid' from account.move %s") % (inv.name, move.name))

    @api.model
    def _sync_account_payment(self, job):
        """Odoo account.payment state change listener."""
        payment = self.env["account.payment"].browse(job.origin_res_id)
        if not payment.exists():
            return
        moves = payment.reconciled_bill_ids | payment.reconciled_invoice_ids
        for move in moves:
            inv = self.env["security.billing.invoice"].search([("move_id", "=", move.id)], limit=1)
            if inv and move.payment_state in ("paid", "in_payment") and inv.state != "paid":
                inv.with_context(reconciliation_origin="billing_account_invoice").write({"state": "paid"})
                job._log("done", _("Updated DeployGuard invoice %s to 'paid' from payment %s") % (inv.name, payment.name))

    # ═══════════════════════════════════════════════════════════════════════════
    # 4. NIGHTLY SWEEP DISCOVERY SCANNER
    # ═══════════════════════════════════════════════════════════════════════════
    @api.model
    def _cron_reconciliation_billing_sweep(self):
        """Scans for unlinked or drifted invoices and payments across all active companies."""
        companies = self.env["res.company"].search([])
        Job = self.env["security.reconciliation.job"]
        Link = self.env["security.reconciliation.link"]

        for company in companies:
            rule = self._get_or_create_rule(company.id)
            
            # 1. Unlinked Invoices
            unlinked_invoices = self.env["security.billing.invoice"].search([
                ("company_id", "=", company.id),
                ("state", "in", ("sent", "paid")),
                ("move_id", "=", False),
            ])
            for inv in unlinked_invoices:
                Job.create({
                    "rule_id": rule.id,
                    "company_id": company.id,
                    "origin_model": "security.billing.invoice",
                    "origin_res_id": inv.id,
                    "event_type": "sweep",
                    "direction": "deployguard_to_odoo",
                })

            # 2. Payment State Mismatches
            mismatched = self.env["security.billing.invoice"].search([
                ("company_id", "=", company.id),
                ("move_id", "!=", False),
                ("move_id.state", "=", "posted"),
            ])
            for inv in mismatched:
                move = inv.move_id
                if move.payment_state in ("paid", "in_payment") and inv.state != "paid":
                    Job.create({
                        "rule_id": rule.id,
                        "company_id": company.id,
                        "origin_model": "account.move",
                        "origin_res_id": move.id,
                        "event_type": "sweep",
                        "direction": "odoo_to_deployguard",
                    })

        return True
