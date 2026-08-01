from odoo.tests.common import TransactionCase
from odoo.fields import Date


class TestReconciliationBillingAccount(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env["res.partner"].create({
            "name": "Test Client Reconciliation Corp",
            "company_id": cls.company.id,
        })
        cls.journal = cls.env["account.journal"].search([
            ("type", "=", "sale"),
            ("company_id", "=", cls.company.id),
        ], limit=1)
        if not cls.journal:
            cls.journal = cls.env["account.journal"].create({
                "name": "Sales Test Journal",
                "code": "TSALE",
                "type": "sale",
                "company_id": cls.company.id,
            })

        cls.Adapter = cls.env["security.reconciliation.billing.adapter"]
        cls.rule = cls.Adapter._get_or_create_rule(cls.company)

    def test_draft_invoice_reconciliation_sync(self):
        """Test draft DeployGuard invoice creates draft account.move and link."""
        inv = self.env["security.billing.invoice"].with_context(sync_inline=True).create({
            "partner_id": self.partner.id,
            "invoice_date": Date.today(),
            "company_id": self.company.id,
            "state": "draft",
            "line_ids": [(0, 0, {
                "name": "Static Security Guard Hours",
                "quantity": 10.0,
                "unit_price": 50.0,
            })],
        })

        # Process queued reconciliation job
        job = self.env["security.reconciliation.job"].search([
            ("origin_model", "=", "security.billing.invoice"),
            ("origin_res_id", "=", inv.id),
        ], limit=1)
        self.assertTrue(job, "Reconciliation outbox job should be created.")
        job._process()

        self.assertEqual(job.state, "done", "Job should complete successfully.")
        self.assertTrue(inv.move_id, "Linked account.move should be created.")
        self.assertEqual(inv.move_id.state, "draft", "Move should be draft when custom invoice is draft.")

        link = self.env["security.reconciliation.link"].search([
            ("source_model", "=", "security.billing.invoice"),
            ("source_res_id", "=", inv.id),
        ], limit=1)
        self.assertTrue(link, "Reconciliation link should be registered.")
        self.assertEqual(link.target_res_id, inv.move_id.id)

    def test_posted_invoice_guardrail_conflict(self):
        """Test modifying a posted Accounting invoice generates a financial conflict without altering posted move."""
        inv = self.env["security.billing.invoice"].with_context(sync_inline=True).create({
            "partner_id": self.partner.id,
            "invoice_date": Date.today(),
            "company_id": self.company.id,
            "state": "sent",
            "line_ids": [(0, 0, {
                "name": "Guarding Shift",
                "quantity": 100.0,
                "unit_price": 10.0,
            })],
        })

        # Process initial sync and post
        job1 = self.env["security.reconciliation.job"].search([
            ("origin_model", "=", "security.billing.invoice"),
            ("origin_res_id", "=", inv.id),
        ], limit=1)
        job1._process()
        self.assertTrue(inv.move_id)
        self.assertEqual(inv.move_id.state, "posted", "Linked account.move should be posted.")

        # Simulate editing DeployGuard invoice lines after posting
        self.env["security.billing.invoice.line"].with_context(sync_inline=False).create({
            "invoice_id": inv.id,
            "name": "Additional Supervision Fee",
            "quantity": 1.0,
            "unit_price": 500.0,
        })
        inv.invalidate_recordset(["line_ids", "total_amount"])
        inv._compute_totals()

        # Process edit job
        job2 = self.env["security.reconciliation.job"].create({
            "rule_id": self.rule.id,
            "company_id": self.company.id,
            "origin_model": "security.billing.invoice",
            "origin_res_id": inv.id,
            "event_type": "write",
            "direction": "deployguard_to_odoo",
        })
        job2._process()

        # Guardrail check: Posted move must remain posted and unchanged
        self.assertEqual(inv.move_id.state, "posted", "Posted move must NOT be drafted or rewritten.")
        self.assertEqual(job2.state, "conflict", "Job state should be conflict.")

        conflict = self.env["security.reconciliation.conflict"].search([
            ("job_id", "=", job2.id),
        ], limit=1)
        self.assertTrue(conflict, "A financial conflict record must be created.")
        self.assertEqual(conflict.severity, "financial")

    def test_nightly_sweep_discovery(self):
        """Test nightly sweep discovers unlinked invoices."""
        inv = self.env["security.billing.invoice"].create({
            "partner_id": self.partner.id,
            "invoice_date": Date.today(),
            "company_id": self.company.id,
            "state": "sent",
            "line_ids": [(0, 0, {
                "name": "Unlinked Guarding",
                "quantity": 5.0,
                "unit_price": 20.0,
            })],
        })

        # Run sweep
        self.Adapter._cron_reconciliation_billing_sweep()

        job = self.env["security.reconciliation.job"].search([
            ("origin_model", "=", "security.billing.invoice"),
            ("origin_res_id", "=", inv.id),
            ("event_type", "=", "sweep"),
        ], limit=1)
        self.assertTrue(job, "Sweep should discover unlinked invoice and create job.")
