from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    billing_plan_ids = fields.One2many(
        "security.billing.plan",
        "lead_id",
        string="Security Billing Plans",
    )
    billing_plan_count = fields.Integer(
        compute="_compute_billing_plan_count",
        string="Billing Plan Count",
    )

    @api.depends("billing_plan_ids")
    def _compute_billing_plan_count(self):
        for lead in self:
            lead.billing_plan_count = len(lead.billing_plan_ids)

    def action_view_billing_plans(self):
        self.ensure_one()
        # Find action by XML ID
        action = self.env["ir.actions.actions"]._for_xml_id("security_billing.action_security_billing_plan")
        action.update({
            "domain": [("lead_id", "=", self.id)],
            "context": {
                "default_lead_id": self.id,
                "default_partner_id": self.partner_id.id if self.partner_id else False,
            },
        })
        return action

    def action_create_security_contract(self):
        self.ensure_one()
        if not self.partner_id:
            raise ValidationError("Please assign a customer to this opportunity first.")

        contract_vals = {
            "name": f"CTR/{self.name}",
            "partner_id": self.partner_id.id,
            "currency_id": self.company_currency.id if hasattr(self, "company_currency") and self.company_currency else self.env.company.currency_id.id,
            "date_start": fields.Date.today(),
            "monthly_value": self.expected_revenue or 0.0,
            "state": "draft",
        }
        contract = self.env["security.client.contract"].create(contract_vals)
        return {
            "type": "ir.actions.act_window",
            "res_model": "security.client.contract",
            "res_id": contract.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_create_security_billing_plan(self):
        self.ensure_one()
        if not self.partner_id:
            raise ValidationError("Please assign a customer to this opportunity first.")

        plan_vals = {
            "name": f"Plan for {self.name}",
            "partner_id": self.partner_id.id,
            "currency_id": self.company_currency.id if hasattr(self, "company_currency") and self.company_currency else self.env.company.currency_id.id,
            "date_start": fields.Date.today(),
            "lead_id": self.id,
        }
        plan = self.env["security.billing.plan"].create(plan_vals)
        return {
            "type": "ir.actions.act_window",
            "res_model": "security.billing.plan",
            "res_id": plan.id,
            "view_mode": "form",
            "target": "current",
        }


class SecurityBillingPlan(models.Model):
    _inherit = "security.billing.plan"

    lead_id = fields.Many2one(
        "crm.lead",
        string="Linked CRM Lead",
        ondelete="set null",
    )
