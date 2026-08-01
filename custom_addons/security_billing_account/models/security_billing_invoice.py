from odoo import api, fields, models


class SecurityBillingInvoice(models.Model):
    _inherit = "security.billing.invoice"

    move_id = fields.Many2one(
        "account.move",
        string="Linked Odoo Invoice",
        ondelete="set null",
        copy=False,
    )

    def action_sync_to_odoo_invoice(self):
        """Delegates invoice synchronization to Reconciliation Core Adapter."""
        Adapter = self.env["security.reconciliation.billing.adapter"]
        Job = self.env["security.reconciliation.job"]
        for inv in self:
            company = inv.company_id if hasattr(inv, "company_id") and inv.company_id else self.env.company
            rule = Adapter._get_or_create_rule(company)
            job = Job.create({
                "rule_id": rule.id,
                "company_id": company.id,
                "origin_model": "security.billing.invoice",
                "origin_res_id": inv.id,
                "event_type": "write",
                "direction": "deployguard_to_odoo",
            })
            job._process()
        return True

    def action_auto_reconcile(self):
        """Delegates auto reconciliation to Reconciliation Core Adapter."""
        return self.action_sync_to_odoo_invoice()

    def action_view_odoo_invoice(self):
        self.ensure_one()
        if not self.move_id:
            self.action_sync_to_odoo_invoice()
        if self.move_id:
            return {
                "type": "ir.actions.act_window",
                "res_model": "account.move",
                "res_id": self.move_id.id,
                "view_mode": "form",
                "target": "current",
            }
        return False


class SecurityClientPayment(models.Model):
    _inherit = "security.client.payment"

    def action_post(self):
        res = super().action_post()
        if self.env.context.get("reconciliation_origin") == "billing_account_invoice":
            return res
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
            job._process()
        return res


class SecurityBillingCreditNote(models.Model):
    _inherit = "security.billing.credit.note"

    move_id = fields.Many2one(
        "account.move",
        string="Linked Odoo Credit Note",
        ondelete="set null",
        copy=False,
    )

    def action_confirm(self):
        res = super().action_confirm()
        if self.env.context.get("reconciliation_origin") == "billing_account_invoice":
            return res
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
            job._process()
        return res
