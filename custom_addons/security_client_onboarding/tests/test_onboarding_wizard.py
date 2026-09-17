from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestOnboardingWizard(TransactionCase):
    """The wizard is the one supported path from new client to rosterable.

    The regression that matters most here is `test_confirm_creates_roster_batch`:
    before this rewrite, confirming with the default options wrote a `month`
    field that does not exist on security.roster.batch, and omitted the required
    date_from/date_to -- so the happy path raised.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.post_type = cls.env["security.post.type"].create({"name": "Static Guard"})
        cls.shift = cls.env["security.shift.template"].create({
            "name": "Day 06-18", "start_hour": 6.0, "end_hour": 18.0,
        })

    def _wizard(self, **overrides):
        vals = {
            "new_partner_name": "Acme Mining Ltd",
            "contract_start": date(2026, 9, 1),
        }
        vals.update(overrides)
        return self.env["security.client.onboarding.wizard"].create(vals)

    def _fully_populated(self):
        wiz = self._wizard()
        site = self.env["security.client.onboarding.site"].create({
            "wizard_id": wiz.id, "site_name": "Head Office", "code": "HQ",
        })
        self.env["security.client.onboarding.requirement"].create({
            "wizard_id": wiz.id,
            "site_line_id": site.id,
            "post_type_id": self.post_type.id,
            "shift_template_id": self.shift.id,
            "guard_count": 2,
            "bill_rate": 100.0,
            "pay_rate": 60.0,
        })
        return wiz, site

    # ── Validation ────────────────────────────────────────────────────

    def test_step_one_requires_a_client(self):
        wiz = self._wizard(new_partner_name=False)
        with self.assertRaises(ValidationError):
            wiz.action_next()

    def test_step_validation_is_scoped_to_that_step(self):
        """Leaving step 1 must not complain about sites not yet added."""
        wiz = self._wizard()
        wiz.action_next()
        self.assertEqual(wiz.step, "2_sites")

    def test_cannot_leave_sites_step_empty(self):
        wiz = self._wizard()
        wiz.action_next()
        with self.assertRaises(ValidationError):
            wiz.action_next()

    def test_confirm_refuses_when_incomplete(self):
        wiz = self._wizard()
        with self.assertRaises(ValidationError):
            wiz.action_confirm()

    def test_zero_rates_warn_but_never_block(self):
        wiz, site = self._fully_populated()
        wiz.requirement_line_ids.write({"bill_rate": 0.0, "pay_rate": 0.0})
        self.assertTrue(wiz.is_ready, "zero rates must not block setup")
        self.assertTrue(wiz._collect_warnings(), "zero rates must still warn")

    # ── Creation ──────────────────────────────────────────────────────

    def test_confirm_creates_the_full_chain(self):
        wiz, _site = self._fully_populated()
        wiz.action_confirm()

        partner = self.env["res.partner"].search([("name", "=", "Acme Mining Ltd")])
        self.assertEqual(len(partner), 1)
        self.assertTrue(partner.is_company)

        sites = self.env["security.client.site"].search([("partner_id", "=", partner.id)])
        self.assertEqual(len(sites), 1)
        self.assertEqual(sites.name, "Head Office")

        reqs = self.env["security.shift.requirement"].search([("site_id", "=", sites.id)])
        self.assertEqual(len(reqs), 1)
        self.assertEqual(reqs.guard_count, 2)
        self.assertTrue(reqs.post_id, "a post must be created for the requirement")
        self.assertEqual(reqs.post_id.post_type_id, self.post_type)

        plan = self.env["security.billing.plan"].search([("partner_id", "=", partner.id)])
        self.assertEqual(len(plan), 1)

    def test_confirm_creates_roster_batch(self):
        """Regression: the default options used to raise on confirm."""
        wiz, _site = self._fully_populated()
        wiz.write({"generate_first_roster": True, "roster_month": date(2026, 10, 1)})
        wiz.action_confirm()

        partner = self.env["res.partner"].search([("name", "=", "Acme Mining Ltd")])
        batch = self.env["security.roster.batch"].search([("partner_id", "=", partner.id)])
        self.assertEqual(len(batch), 1)
        self.assertEqual(batch.date_from, date(2026, 10, 1))
        self.assertEqual(batch.date_to, date(2026, 10, 31), "batch must span the month")
        self.assertEqual(batch.state, "draft")

    def test_roster_batch_is_optional(self):
        wiz, _site = self._fully_populated()
        wiz.generate_first_roster = False
        wiz.action_confirm()
        partner = self.env["res.partner"].search([("name", "=", "Acme Mining Ltd")])
        self.assertFalse(
            self.env["security.roster.batch"].search([("partner_id", "=", partner.id)])
        )

    def test_requirements_resolve_to_the_right_site(self):
        """The old wizard matched sites by typed name; two sites is where that
        went wrong."""
        wiz = self._wizard()
        site_a = self.env["security.client.onboarding.site"].create({
            "wizard_id": wiz.id, "site_name": "Warehouse",
        })
        site_b = self.env["security.client.onboarding.site"].create({
            "wizard_id": wiz.id, "site_name": "Head Office",
        })
        self.env["security.client.onboarding.requirement"].create({
            "wizard_id": wiz.id, "site_line_id": site_b.id,
            "post_type_id": self.post_type.id,
            "shift_template_id": self.shift.id, "guard_count": 1,
        })
        wiz.action_confirm()

        partner = self.env["res.partner"].search([("name", "=", "Acme Mining Ltd")])
        head_office = self.env["security.client.site"].search([
            ("partner_id", "=", partner.id), ("name", "=", "Head Office"),
        ])
        warehouse = self.env["security.client.site"].search([
            ("partner_id", "=", partner.id), ("name", "=", "Warehouse"),
        ])
        self.assertTrue(
            self.env["security.shift.requirement"].search([("site_id", "=", head_office.id)])
        )
        self.assertFalse(
            self.env["security.shift.requirement"].search([("site_id", "=", warehouse.id)]),
            "the requirement belonged to Head Office only",
        )

    def test_posts_are_reused_per_site_and_type(self):
        wiz, site = self._fully_populated()
        self.env["security.client.onboarding.requirement"].create({
            "wizard_id": wiz.id, "site_line_id": site.id,
            "post_type_id": self.post_type.id,
            "shift_template_id": self.shift.id, "guard_count": 3,
        })
        wiz.action_confirm()

        partner = self.env["res.partner"].search([("name", "=", "Acme Mining Ltd")])
        created_site = self.env["security.client.site"].search([("partner_id", "=", partner.id)])
        posts = self.env["security.post"].search([("site_id", "=", created_site.id)])
        self.assertEqual(len(posts), 1, "same site + same post type must share one post")
