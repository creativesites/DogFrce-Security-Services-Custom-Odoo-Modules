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


class SecurityBillingPlan(models.Model):
    _inherit = "security.billing.plan"

    lead_id = fields.Many2one(
        "crm.lead",
        string="Linked CRM Lead",
        ondelete="set null",
    )
