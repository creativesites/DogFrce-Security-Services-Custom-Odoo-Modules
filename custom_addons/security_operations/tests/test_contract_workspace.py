from datetime import date
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestContractWorkspace(TransactionCase):
    """Test suite for the Contract Workspace and Single Source of Truth architecture."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = cls.env["res.partner"].create({
            "name": "Namibia Breweries Ltd",
            "is_company": True,
        })
        cls.shift_day = cls.env["security.shift.template"].create({
            "name": "Day Shift 12h",
            "start_hour": 6.0,
            "end_hour": 18.0,
            "shift_category": "day",
            "duration_hours": 12.0,
        })
        cls.shift_night = cls.env["security.shift.template"].create({
            "name": "Night Shift 12h",
            "start_hour": 18.0,
            "end_hour": 6.0,
            "shift_category": "night",
            "duration_hours": 12.0,
        })
        cls.grade_a = cls.env["security.grade"].create({
            "name": "Grade A",
            "code": "GRA",
            "hourly_rate": 35.0,
        })
        cls.supervisor = cls.env["hr.employee"].create({
            "name": "Supervisor Thomas",
            "security_guard": True,
        })
        cls.contract = cls.env["security.client.contract"].create({
            "name": "CTR-2026-NBL-001",
            "partner_id": cls.client.id,
            "date_start": date(2026, 3, 1),
            "monthly_value": 85000.0,
            "state": "draft",
        })

    def test_cycle_dates_calculation(self):
        """Operational cycle must strictly follow the 21st-to-20th cycle."""
        # 1. Target date before 21st (e.g. 5th March 2026) -> 21 Feb 2026 to 20 Mar 2026
        start, end = self.env["security.client.contract"].get_cycle_dates_for(date(2026, 3, 5))
        self.assertEqual(start, date(2026, 2, 21))
        self.assertEqual(end, date(2026, 3, 20))

        # 2. Target date on or after 21st (e.g. 21st March 2026) -> 21 Mar 2026 to 20 Apr 2026
        start2, end2 = self.env["security.client.contract"].get_cycle_dates_for(date(2026, 3, 21))
        self.assertEqual(start2, date(2026, 3, 21))
        self.assertEqual(end2, date(2026, 4, 20))

    def test_setup_health_diagnostics_blocks_activation_on_incomplete(self):
        """Atomic activation must reject incomplete configurations with descriptive error messages."""
        # Empty contract has 0 sites
        with self.assertRaises(UserError) as cm:
            self.contract.action_activate()
        self.assertIn("has no sites configured", str(cm.exception))

        # Add a site without posts
        c_site = self.env["security.contract.site"].create({
            "contract_id": self.contract.id,
            "name": "Windhoek Plant",
            "location": "Northern Industrial",
            "supervisor_id": self.supervisor.id,
        })
        self.contract._compute_summary_metrics()
        self.contract._evaluate_setup_health()

        with self.assertRaises(UserError) as cm:
            self.contract.action_activate()
        self.assertIn("has no security posts defined", str(cm.exception))

        # Add a post without shift requirements
        c_post = self.env["security.contract.post"].create({
            "contract_site_id": c_site.id,
            "name": "Main Gate",
            "required_guard_count": 1,
        })
        self.contract._compute_summary_metrics()
        self.contract._evaluate_setup_health()

        with self.assertRaises(UserError) as cm:
            self.contract.action_activate()
        self.assertIn("has no shift requirements", str(cm.exception))

    def test_atomic_activation_and_sync(self):
        """A complete contract setup syncs atomically to live operational records."""
        c_site = self.env["security.contract.site"].create({
            "contract_id": self.contract.id,
            "name": "Windhoek Brewery Main Gate",
            "location": "Northern Industrial",
            "supervisor_id": self.supervisor.id,
        })
        c_post = self.env["security.contract.post"].create({
            "contract_site_id": c_site.id,
            "name": "Main Access Gate",
            "required_guard_count": 2,
        })
        c_req = self.env["security.contract.shift.requirement"].create({
            "contract_site_id": c_site.id,
            "contract_post_id": c_post.id,
            "shift_template_id": self.shift_day.id,
            "guard_count": 2,
            "monday": True,
            "tuesday": True,
            "wednesday": True,
            "thursday": True,
            "friday": True,
            "saturday": True,
            "sunday": True,
            "bill_rate": 110.0,
            "pay_rate": 55.0,
        })

        self.contract._compute_summary_metrics()
        self.contract._evaluate_setup_health()
        self.assertEqual(self.contract.readiness_pct, 100)

        # Activate contract
        self.contract.action_activate()
        self.assertEqual(self.contract.state, "active")

        # Verify operational site was created and linked
        self.assertTrue(c_site.site_id)
        op_site = c_site.site_id
        self.assertEqual(op_site.name, "Windhoek Brewery Main Gate")
        self.assertEqual(op_site.partner_id, self.client)
        self.assertEqual(op_site.contract_id, self.contract)
        self.assertTrue(op_site.is_contract_managed)

        # Verify operational post was created and linked
        self.assertTrue(c_post.post_id)
        op_post = c_post.post_id
        self.assertEqual(op_post.site_id, op_site)
        self.assertEqual(op_post.contract_post_id, c_post)
        self.assertTrue(op_post.is_contract_managed)
        self.assertEqual(op_post.required_guard_count, 2)

        # Verify operational requirement was created and linked
        self.assertTrue(c_req.requirement_id)
        op_req = c_req.requirement_id
        self.assertEqual(op_req.site_id, op_site)
        self.assertEqual(op_req.post_id, op_post)
        self.assertEqual(op_req.contract_requirement_id, c_req)
        self.assertTrue(op_req.is_contract_managed)
        self.assertEqual(op_req.guard_count, 2)
        self.assertEqual(op_req.bill_rate, 110.0)

        # Verify idempotency: re-activating updates without duplicate records
        self.contract.action_activate()
        all_sites = self.env["security.client.site"].search([("contract_id", "=", self.contract.id)])
        self.assertEqual(len(all_sites), 1)

    def test_rate_card_inheritance_and_override(self):
        """Shift requirements inherit contract rate card unless explicit override is flagged."""
        # Add rate card line to contract
        self.env["security.contract.rate"].create({
            "contract_id": self.contract.id,
            "shift_category": "day",
            "hourly_rate": 95.0,
        })

        c_site = self.env["security.contract.site"].create({
            "contract_id": self.contract.id,
            "name": "Depot",
            "supervisor_id": self.supervisor.id,
        })
        c_post = self.env["security.contract.post"].create({
            "contract_site_id": c_site.id,
            "name": "Gate",
            "required_guard_count": 1,
        })

        # 1. Inherited requirement (override = False)
        req_inherited = self.env["security.contract.shift.requirement"].create({
            "contract_site_id": c_site.id,
            "contract_post_id": c_post.id,
            "shift_template_id": self.shift_day.id,
            "guard_count": 1,
            "bill_rate_override": False,
        })
        req_inherited._compute_bill_rates()
        self.assertEqual(req_inherited.bill_rate, 95.0)

        # 2. Overridden requirement (override = True)
        req_override = self.env["security.contract.shift.requirement"].create({
            "contract_site_id": c_site.id,
            "contract_post_id": c_post.id,
            "shift_template_id": self.shift_day.id,
            "guard_count": 1,
            "bill_rate_override": True,
            "contract_bill_rate": 135.0,
            "override_reason": "High risk zone premium",
        })
        req_override._compute_bill_rates()
        self.assertEqual(req_override.bill_rate, 135.0)

    def test_legacy_migration_wizard(self):
        """Legacy site and post structures migrate seamlessly into contract-managed hierarchy."""
        # Create legacy site and post directly
        leg_site = self.env["security.client.site"].create({
            "name": "Legacy Swakopmund Facility",
            "partner_id": self.client.id,
            "location": "Swakopmund",
        })
        leg_post = self.env["security.post"].with_context(allow_standalone_post=True).create({
            "name": "Front Gate",
            "site_id": leg_site.id,
            "partner_id": self.client.id,
            "required_guard_count": 1,
        })
        leg_req = self.env["security.shift.requirement"].create({
            "site_id": leg_site.id,
            "post_id": leg_post.id,
            "shift_template_id": self.shift_day.id,
            "guard_count": 1,
            "bill_rate": 80.0,
            "pay_rate": 45.0,
        })

        # Run migration wizard
        wizard = self.env["security.legacy.contract.migration.wizard"].create({})
        wizard.action_run_migration()

        self.assertEqual(wizard.state, "done")
        self.assertGreaterEqual(wizard.sites_mapped, 1)

        # Verify contract site was created under this client's contract
        c_site = self.contract.contract_site_ids.filtered(lambda cs: cs.site_id == leg_site)
        self.assertTrue(c_site)
        self.assertEqual(c_site.name, "Legacy Swakopmund Facility")

        # Verify contract post was created
        c_post = c_site.post_line_ids.filtered(lambda cp: cp.post_id == leg_post)
        self.assertTrue(c_post)

        # Verify contract requirement was created
        c_req = c_post.requirement_line_ids.filtered(lambda cr: cr.requirement_id == leg_req)
        self.assertTrue(c_req)
        self.assertEqual(c_req.bill_rate, 80.0)

    def test_duplicate_audit_wizard(self):
        """Duplicate audit detects duplicates and safely archives them without deleting history."""
        # Create a near-duplicate partner
        dup_partner = self.env["res.partner"].create({
            "name": "Namibia Breweries Ltd.",  # Note the period
            "is_company": True,
            "active": True,
        })

        wizard = self.env["security.duplicate.audit.wizard"].create({})
        wizard.action_run_audit()

        # Should detect candidate
        dup_line = wizard.line_ids.filtered(lambda l: l.record_type == "client" and l.dup_partner_id == dup_partner)
        self.assertTrue(dup_line, "Duplicate audit must detect near-identical partner name")

        # Approve and merge
        dup_line.action_approve()
        wizard.action_merge_approved()

        # Verify safe merge: duplicate partner archived, not deleted
        self.assertFalse(dup_partner.active, "Duplicate record must be safely archived")
        self.assertTrue(dup_partner.exists(), "Duplicate record must never be permanently deleted")
