from odoo import api, fields, models


class SecurityBillingInvoice(models.Model):
    _inherit = "security.billing.invoice"

    move_id = fields.Many2one(
        "account.move",
        string="Linked Odoo Invoice",
        ondelete="set null",
        copy=False,
    )

    def write(self, vals):
        result = super().write(vals)
        # Auto-sync to Odoo Account Move when validated/sent or paid
        if "state" in vals and vals["state"] in ("sent", "paid"):
            self.action_sync_to_odoo_invoice()
        return result

    def action_sync_to_odoo_invoice(self):
        """Create or update corresponding native Odoo account.move invoice."""
        journal_model = self.env["account.journal"]
        move_model = self.env["account.move"]

        for inv in self:
            if inv.state == "draft":
                continue

            journal = journal_model.search([
                ("type", "=", "sale"),
                ("company_id", "=", inv.currency_id.company_id.id or self.env.company.id)
            ], limit=1)

            vals = {
                "move_type": "out_invoice",
                "partner_id": inv.partner_id.id,
                "invoice_date": inv.invoice_date,
                "invoice_date_due": inv.due_date,
                "currency_id": inv.currency_id.id,
                "ref": inv.name,
                "journal_id": journal.id if journal else False,
            }

            move = inv.move_id
            if move:
                move.write(vals)
                # Reset lines
                move.invoice_line_ids.unlink()
            else:
                move = move_model.create(vals)
                # Avoid recursion during sync write
                super(SecurityBillingInvoice, inv).write({"move_id": move.id})

            # Map lines
            line_vals = []
            for line in inv.line_ids:
                product = self.env["product.product"].search([
                    ("name", "ilike", "Security"),
                    ("type", "=", "service")
                ], limit=1)

                line_vals.append((0, 0, {
                    "name": line.name,
                    "quantity": line.quantity * max(line.guard_count, 1),
                    "price_unit": line.unit_price,
                    "product_id": product.id if product else False,
                }))
            if line_vals:
                move.write({"invoice_line_ids": line_vals})

        return True

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
