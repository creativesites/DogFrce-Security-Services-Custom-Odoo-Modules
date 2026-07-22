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
            if not self.env.context.get("skip_auto_reconcile"):
                self.action_auto_reconcile()
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

            # If the custom invoice is sent or paid, make sure the Odoo invoice is posted
            if inv.state in ("sent", "paid") and move.state == "draft":
                move.action_post()

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

    def action_auto_reconcile(self):
        """Bidirectionally reconcile custom security invoices and standard Odoo invoices."""
        if self.env.context.get("skip_auto_reconcile"):
            return True

        for inv in self:
            # 1. Ensure Odoo invoice exists and is posted if custom invoice is sent/paid
            if inv.state in ("sent", "paid"):
                if not inv.move_id:
                    inv.action_sync_to_odoo_invoice()
                
                move = inv.move_id
                if move and move.state == "draft":
                    move.action_post()

            # 2. If Odoo invoice is posted, perform bidirectional payment matching
            if inv.move_id and inv.move_id.state == "posted":
                move = inv.move_id
                
                # In Odoo, paid amount = amount_total - amount_residual
                odoo_paid = move.amount_total - move.amount_residual
                
                # In DeployGuard, total posted payments
                custom_paid = sum(
                    inv.payment_ids.filtered(lambda p: p.state == "posted").mapped("amount")
                )

                if abs(odoo_paid - custom_paid) > 0.01:
                    if odoo_paid > custom_paid:
                        # Odoo is ahead. Synchronize payments from Odoo -> DeployGuard
                        diff = odoo_paid - custom_paid
                        self.env["security.client.payment"].with_context(
                            skip_odoo_payment_sync=True,
                            skip_auto_reconcile=True
                        ).create({
                            "invoice_id": inv.id,
                            "amount": diff,
                            "payment_date": fields.Date.context_today(self),
                            "payment_method": "bank_transfer",
                            "bank_reference": f"Auto-Reconciled from Odoo Invoice {move.name}",
                            "state": "posted",
                        })
                        inv._compute_payment_status()
                    else:
                        # DeployGuard is ahead. Synchronize payments from DeployGuard -> Odoo
                        diff = custom_paid - odoo_paid
                        journal = self.env["account.journal"].search([
                            ("type", "in", ("bank", "cash")),
                            ("company_id", "=", inv.currency_id.company_id.id or self.env.company.id)
                        ], limit=1)
                        if journal:
                            register_wizard = self.env["account.payment.register"].with_context(
                                active_model="account.move",
                                active_ids=move.ids,
                                skip_auto_reconcile=True,
                            ).create({
                                "amount": diff,
                                "payment_date": fields.Date.context_today(self),
                                "journal_id": journal.id,
                            })
                            register_wizard.action_create_payments()

            # 3. Synchronize final invoice state
            if inv.move_id:
                move = inv.move_id
                if move.payment_state in ("paid", "in_payment") and inv.state != "paid":
                    inv.with_context(skip_auto_reconcile=True).write({"state": "paid"})
                elif inv.state == "paid" and move.payment_state not in ("paid", "in_payment"):
                    # If custom is paid, make sure standard Odoo invoice is fully paid
                    if move.state == "posted" and move.amount_residual > 0.01:
                        journal = self.env["account.journal"].search([
                            ("type", "in", ("bank", "cash")),
                            ("company_id", "=", inv.currency_id.company_id.id or self.env.company.id)
                        ], limit=1)
                        if journal:
                            register_wizard = self.env["account.payment.register"].with_context(
                                active_model="account.move",
                                active_ids=move.ids,
                                skip_auto_reconcile=True,
                            ).create({
                                "amount": move.amount_residual,
                                "payment_date": fields.Date.context_today(self),
                                "journal_id": journal.id,
                            })
                            register_wizard.action_create_payments()

        return True


class SecurityClientPayment(models.Model):
    _inherit = "security.client.payment"

    def action_post(self):
        super().action_post()
        if self.env.context.get("skip_odoo_payment_sync") or self.env.context.get("skip_auto_reconcile"):
            return True

        for payment in self:
            invoice = payment.invoice_id
            if invoice.move_id and invoice.move_id.state == "posted":
                # Find standard bank or cash journal
                journal = self.env["account.journal"].search([
                    ("type", "in", ("bank", "cash")),
                    ("company_id", "=", invoice.currency_id.company_id.id or self.env.company.id)
                ], limit=1)
                if journal:
                    # Check how much has already been paid on Odoo compared to custom
                    odoo_paid = invoice.move_id.amount_total - invoice.move_id.amount_residual
                    custom_paid = sum(
                        invoice.payment_ids.filtered(lambda p: p.state == "posted").mapped("amount")
                    )
                    # Register standard Odoo payment for the delta if any
                    if odoo_paid < custom_paid:
                        delta = custom_paid - odoo_paid
                        register_wizard = self.env["account.payment.register"].with_context(
                            active_model="account.move",
                            active_ids=invoice.move_id.ids,
                            skip_auto_reconcile=True,
                        ).create({
                            "amount": delta,
                            "payment_date": payment.payment_date or fields.Date.context_today(self),
                            "journal_id": journal.id,
                        })
                        register_wizard.action_create_payments()
                    
                    # Call auto-reconcile to align all balances and states
                    invoice.with_context(skip_auto_reconcile=True).action_auto_reconcile()
        return True

    def action_cancel(self):
        super().action_cancel()
        if self.env.context.get("skip_odoo_payment_sync") or self.env.context.get("skip_auto_reconcile"):
            return True

        for payment in self:
            invoice = payment.invoice_id
            if invoice.move_id:
                # Trigger a reconciliation pass to re-align DeployGuard and standard Odoo
                invoice.action_auto_reconcile()
        return True


class AccountMove(models.Model):
    _inherit = "account.move"

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get("skip_auto_reconcile"):
            return res

        if "payment_state" in vals or "amount_residual" in vals:
            # Find linked custom security invoices
            custom_invoices = self.env["security.billing.invoice"].search([("move_id", "in", self.ids)])
            if custom_invoices:
                custom_invoices.with_context(skip_auto_reconcile=True).action_auto_reconcile()
        return res
