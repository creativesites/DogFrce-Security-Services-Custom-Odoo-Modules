from odoo.tests.common import TransactionCase


class TestBillingReconciliation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.nad = cls.env.ref("base.NAD", raise_if_not_found=False) or cls.env.company.currency_id
        cls.partner = cls.env["res.partner"].create({
            "name": "Test Reconciliation Client",
            "is_company": True,
            "email": "reconciliation@test.na",
        })
        cls.billing_plan = cls.env["security.billing.plan"].create({
            "name": "Test Reconciliation Plan",
            "partner_id": cls.partner.id,
            "billing_mode": "recurring",
            "currency_id": cls.nad.id,
            "date_start": "2026-01-01",
        })

    def _make_invoice(self, amount=100.0):
        invoice = self.env["security.billing.invoice"].create({
            "billing_plan_id": self.billing_plan.id,
            "partner_id": self.partner.id,
            "service_date_from": "2026-05-01",
            "service_date_to": "2026-05-31",
            "vat_rate": 0.0,
        })
        self.env["security.billing.invoice.line"].create({
            "invoice_id": invoice.id,
            "name": "Guard Patrol Services",
            "quantity": 1.0,
            "unit_price": amount,
        })
        invoice.invalidate_recordset()
        return invoice

    def test_partial_payment_reconciliation(self):
        # 1. Create invoice of 100.0 and mark sent
        invoice = self._make_invoice(amount=100.0)
        self.assertEqual(invoice.state, "draft")
        self.assertEqual(invoice.payment_status, "unpaid")
        self.assertAlmostEqual(invoice.total_amount, 100.0, places=2)
        self.assertAlmostEqual(invoice.balance_amount, 100.0, places=2)

        invoice.action_mark_sent()
        self.assertEqual(invoice.state, "sent")

        # Check partner outstanding balance is 100.0
        self.partner._compute_invoice_outstanding()
        self.assertAlmostEqual(self.partner.security_invoice_outstanding, 100.0, places=2)
        self.assertEqual(self.partner.security_invoice_count, 1)

        # 2. Record a partial payment of 40.0
        payment1 = self.env["security.client.payment"].create({
            "invoice_id": invoice.id,
            "amount": 40.0,
            "payment_method": "bank_transfer",
        })
        self.assertEqual(payment1.state, "draft")
        
        # Post the payment
        payment1.action_post()
        self.assertEqual(payment1.state, "posted")

        # Force compute payment status & partner outstanding
        invoice._compute_payment_status()
        self.partner._compute_invoice_outstanding()

        # Check invoice status and remaining balance (100 - 40 = 60)
        self.assertEqual(invoice.payment_status, "partial")
        self.assertAlmostEqual(invoice.paid_amount, 40.0, places=2)
        self.assertAlmostEqual(invoice.balance_amount, 60.0, places=2)

        # Check partner outstanding balance is now 60.0 (and NOT gross 100.0!)
        self.assertAlmostEqual(self.partner.security_invoice_outstanding, 60.0, places=2)
        self.assertEqual(self.partner.security_invoice_count, 1)

        # 3. Record remaining payment of 60.0
        payment2 = self.env["security.client.payment"].create({
            "invoice_id": invoice.id,
            "amount": 60.0,
            "payment_method": "bank_transfer",
        })
        payment2.action_post()

        invoice._compute_payment_status()
        invoice.action_mark_paid()
        self.partner._compute_invoice_outstanding()

        # Check paid status and zero balance
        self.assertEqual(invoice.state, "paid")
        self.assertEqual(invoice.payment_status, "paid")
        self.assertAlmostEqual(invoice.paid_amount, 100.0, places=2)
        self.assertAlmostEqual(invoice.balance_amount, 0.0, places=2)

        # Check partner outstanding is now 0.0 (paid state invoices are excluded from outstanding list)
        self.assertAlmostEqual(self.partner.security_invoice_outstanding, 0.0, places=2)
        self.assertEqual(self.partner.security_invoice_count, 0)
