from odoo.tests.common import TransactionCase


class TestBillingPipeline(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.nad = cls.env.ref("base.NAD", raise_if_not_found=False) or cls.env.company.currency_id
        cls.partner = cls.env["res.partner"].create({
            "name": "Test Billing Client K2",
            "is_company": True,
            "email": "billing@testclient.na",
        })
        cls.site = cls.env["security.client.site"].create({
            "name": "Test Billing Site K2",
            "partner_id": cls.partner.id,
        })
        cls.billing_plan = cls.env["security.billing.plan"].create({
            "name": "Test Billing Plan K2",
            "partner_id": cls.partner.id,
            "billing_mode": "recurring",
            "currency_id": cls.nad.id,
        })

    def _make_invoice(self, date_from="2026-05-01", date_to="2026-05-31", vat_rate=15.0):
        return self.env["security.billing.invoice"].create({
            "billing_plan_id": self.billing_plan.id,
            "partner_id": self.partner.id,
            "service_date_from": date_from,
            "service_date_to": date_to,
            "vat_rate": vat_rate,
        })

    def test_invoice_creates_in_draft(self):
        invoice = self._make_invoice()
        self.assertEqual(invoice.state, "draft")

    def test_invoice_vat_computation(self):
        invoice = self._make_invoice(vat_rate=15.0)
        self.env["security.billing.invoice.line"].create({
            "invoice_id": invoice.id,
            "name": "Security Services",
            "quantity": 1.0,
            "unit_price": 10000.0,
        })
        invoice.invalidate_recordset()
        self.assertAlmostEqual(invoice.vat_amount, 1500.0, places=1)
        self.assertAlmostEqual(invoice.total_amount, 11500.0, places=1)

    def test_invoice_state_machine_draft_sent_paid(self):
        invoice = self._make_invoice(date_from="2026-06-01", date_to="2026-06-30")
        self.assertEqual(invoice.state, "draft")
        invoice.action_mark_sent()
        self.assertEqual(invoice.state, "sent")
        invoice.action_mark_paid()
        self.assertEqual(invoice.state, "paid")

    def test_invoice_cancel_and_reset(self):
        invoice = self._make_invoice(date_from="2026-07-01", date_to="2026-07-31")
        invoice.action_cancel()
        self.assertEqual(invoice.state, "cancelled")
        invoice.action_reset_to_draft()
        self.assertEqual(invoice.state, "draft")

    def test_amount_in_words_populated(self):
        invoice = self._make_invoice(vat_rate=15.0)
        self.env["security.billing.invoice.line"].create({
            "invoice_id": invoice.id,
            "name": "Guard Services",
            "quantity": 2.0,
            "unit_price": 5000.0,
        })
        invoice.invalidate_recordset()
        self.assertTrue(invoice.amount_in_words, "amount_in_words should not be empty")

    def test_zero_vat_rate(self):
        invoice = self._make_invoice(vat_rate=0.0)
        self.env["security.billing.invoice.line"].create({
            "invoice_id": invoice.id,
            "name": "Zero VAT Service",
            "quantity": 1.0,
            "unit_price": 8000.0,
        })
        invoice.invalidate_recordset()
        self.assertAlmostEqual(invoice.vat_amount, 0.0, places=2)
        self.assertAlmostEqual(invoice.total_amount, 8000.0, places=2)
