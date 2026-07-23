from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    billing_plan_ids = fields.One2many(
        "security.billing.plan",
        "sale_order_id",
        string="Security Billing Plans",
    )
    billing_plan_count = fields.Integer(
        compute="_compute_billing_plan_count",
        string="Billing Plan Count",
    )

    @api.depends("billing_plan_ids")
    def _compute_billing_plan_count(self):
        for order in self:
            order.billing_plan_count = len(order.billing_plan_ids)

    def action_view_billing_plans(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("security_billing.action_security_billing_plan")
        action.update({
            "domain": [("sale_order_id", "=", self.id)],
            "context": {
                "default_sale_order_id": self.id,
                "default_partner_id": self.partner_id.id if self.partner_id else False,
            },
        })
        return action

    def action_create_security_billing_plan(self):
        self.ensure_one()
        if not self.partner_id:
            raise ValidationError("Please specify a customer on the sales order first.")

        plan_vals = {
            "name": f"Billing Plan for {self.name}",
            "partner_id": self.partner_id.id,
            "currency_id": self.currency_id.id if self.currency_id else self.env.company.currency_id.id,
            "date_start": fields.Date.today(),
            "sale_order_id": self.id,
        }
        plan = self.env["security.billing.plan"].create(plan_vals)

        # Map lines
        lines = []
        for line in self.order_line:
            # We skip section/note lines
            if line.display_type:
                continue
            lines.append((0, 0, {
                "name": line.name or line.product_id.name or "Service Line",
                "quantity": line.product_uom_qty,
                "unit_price": line.price_unit,
            }))
        if lines:
            plan.write({"line_ids": lines})

        # Return action to open the newly created plan in form view
        return {
            "type": "ir.actions.act_window",
            "res_model": "security.billing.plan",
            "res_id": plan.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_create_security_contract(self):
        self.ensure_one()
        if not self.partner_id:
            raise ValidationError("Please specify a customer on the sales order first.")

        contract_vals = {
            "name": f"CTR/{self.name}",
            "partner_id": self.partner_id.id,
            "currency_id": self.currency_id.id if self.currency_id else self.env.company.currency_id.id,
            "date_start": fields.Date.today(),
            "monthly_value": self.amount_total,
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


class SecurityBillingPlan(models.Model):
    _inherit = "security.billing.plan"

    sale_order_id = fields.Many2one(
        "sale.order",
        string="Linked Sales Order",
        ondelete="set null",
    )
