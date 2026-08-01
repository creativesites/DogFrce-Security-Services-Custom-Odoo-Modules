from odoo import api, fields, models


class SecurityBillingInvoice(models.Model):
    _inherit = "security.billing.invoice"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    move_id = fields.Many2one(
        "account.move",
        string="Linked Odoo Invoice",
        ondelete="set null",
        copy=False,
    )

    def action_view_odoo_invoice(self):
        self.ensure_one()
        if not self.move_id:
            Adapter = self.env["security.reconciliation.billing.adapter"]
            rule = Adapter._get_or_create_rule(self.company_id if hasattr(self, "company_id") and self.company_id else self.env.company)
            job = self.env["security.reconciliation.job"].create({
                "rule_id": rule.id,
                "company_id": rule.company_id.id,
                "origin_model": "security.billing.invoice",
                "origin_res_id": self.id,
                "event_type": "write",
                "direction": "deployguard_to_odoo",
            })
            job._process()
        if self.move_id:
            return {
                "type": "ir.actions.act_window",
                "res_model": "account.move",
                "res_id": self.move_id.id,
                "view_mode": "form",
                "target": "current",
            }
        return False

    def _queue_reconciliation_job(self, event_type="write"):
        if self.env.context.get("reconciliation_origin") == "billing_account_invoice":
            return
        
        Adapter = self.env["security.reconciliation.billing.adapter"]
        Job = self.env["security.reconciliation.job"]

        for inv in self:
            company = inv.company_id if hasattr(inv, "company_id") and inv.company_id else self.env.company
            rule = Adapter._get_or_create_rule(company)
            
            # Create outbox job
            job = Job.create({
                "rule_id": rule.id,
                "company_id": company.id,
                "origin_model": "security.billing.invoice",
                "origin_res_id": inv.id,
                "event_type": event_type,
                "direction": "deployguard_to_odoo",
            })
            
            # If inline validation or context sync_inline requested, execute job immediately
            if rule.sync_mode == "inline_validation" or self.env.context.get("sync_inline"):
                job._process()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._queue_reconciliation_job(event_type="create")
        return records

    def write(self, vals):
        result = super().write(vals)
        if not self.env.context.get("reconciliation_origin"):
            self._queue_reconciliation_job(event_type="write")
        return result


class SecurityBillingInvoiceLine(models.Model):
    _inherit = "security.billing.invoice.line"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get("reconciliation_origin"):
            invoices = records.mapped("invoice_id")
            invoices._compute_totals()
            invoices._queue_reconciliation_job(event_type="write")
        return records

    def write(self, vals):
        result = super().write(vals)
        if not self.env.context.get("reconciliation_origin"):
            invoices = self.mapped("invoice_id")
            invoices._compute_totals()
            invoices._queue_reconciliation_job(event_type="write")
        return result


class SecurityClientPayment(models.Model):
    _inherit = "security.client.payment"

    def action_post(self):
        result = super().action_post()
        if self.env.context.get("reconciliation_origin") == "billing_account_invoice":
            return result

        Adapter = self.env["security.reconciliation.billing.adapter"]
        Job = self.env["security.reconciliation.job"]

        for payment in self:
            company = payment.company_id if hasattr(payment, "company_id") and payment.company_id else self.env.company
            rule = Adapter._get_or_create_rule(company)
            job = Job.create({
                "rule_id": rule.id,
                "company_id": company.id,
                "origin_model": "security.client.payment",
                "origin_res_id": payment.id,
                "event_type": "state_change",
                "direction": "deployguard_to_odoo",
            })
            if rule.sync_mode == "inline_validation" or self.env.context.get("sync_inline"):
                job._process()
        return result


class SecurityBillingCreditNote(models.Model):
    _inherit = "security.billing.credit.note"

    def action_confirm(self):
        result = super().action_confirm()
        if self.env.context.get("reconciliation_origin") == "billing_account_invoice":
            return result

        Adapter = self.env["security.reconciliation.billing.adapter"]
        Job = self.env["security.reconciliation.job"]

        for cn in self:
            company = cn.company_id if hasattr(cn, "company_id") and cn.company_id else self.env.company
            rule = Adapter._get_or_create_rule(company)
            job = Job.create({
                "rule_id": rule.id,
                "company_id": company.id,
                "origin_model": "security.billing.credit.note",
                "origin_res_id": cn.id,
                "event_type": "state_change",
                "direction": "deployguard_to_odoo",
            })
            if rule.sync_mode == "inline_validation" or self.env.context.get("sync_inline"):
                job._process()
        return result


class AccountMove(models.Model):
    _inherit = "account.move"

    def write(self, vals):
        result = super().write(vals)
        if self.env.context.get("reconciliation_origin") == "billing_account_invoice":
            return result

        if "payment_state" in vals or "state" in vals:
            Adapter = self.env["security.reconciliation.billing.adapter"]
            Job = self.env["security.reconciliation.job"]
            for move in self.filtered(lambda m: m.move_type == "out_invoice"):
                company = move.company_id or self.env.company
                rule = Adapter._get_or_create_rule(company)
                job = Job.create({
                    "rule_id": rule.id,
                    "company_id": company.id,
                    "origin_model": "account.move",
                    "origin_res_id": move.id,
                    "event_type": "state_change",
                    "direction": "odoo_to_deployguard",
                })
                if rule.sync_mode == "inline_validation" or self.env.context.get("sync_inline"):
                    job._process()
        return result


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_post(self):
        result = super().action_post()
        if self.env.context.get("reconciliation_origin") == "billing_account_invoice":
            return result

        Adapter = self.env["security.reconciliation.billing.adapter"]
        Job = self.env["security.reconciliation.job"]

        for payment in self:
            company = payment.company_id or self.env.company
            rule = Adapter._get_or_create_rule(company)
            job = Job.create({
                "rule_id": rule.id,
                "company_id": company.id,
                "origin_model": "account.payment",
                "origin_res_id": payment.id,
                "event_type": "state_change",
                "direction": "odoo_to_deployguard",
            })
            if rule.sync_mode == "inline_validation" or self.env.context.get("sync_inline"):
                job._process()
        return result
