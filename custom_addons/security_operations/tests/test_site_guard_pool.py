# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSiteGuardPool(TransactionCase):
    """
    Comprehensive test suite for DogForce Regular Site Guard Pools,
    Roster-Cycle Snapshots, Fallback Hierarchy, and Document Import Wizard.
    """

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
        cls.grade_a = cls.env["security.grade"].create({
            "name": "Grade A",
            "code": "GRA",
            "hourly_rate": 35.0,
            "sequence": 1,
        })

        # Create 20 security guards
        cls.all_guards = []
        for i in range(1, 21):
            guard = cls.env["hr.employee"].create({
                "name": f"Guard {i:02d} Tester",
                "security_guard": True,
                "active": True,
                "security_disqualified": False,
                "security_grade_id": cls.grade_a.id,
            })
            cls.all_guards.append(guard)

        # Site A with 4 regular guards in site_only mode
        cls.site_a = cls.env["security.client.site"].create({
            "name": "NBL Main Brewery Gate",
            "partner_id": cls.client.id,
            "guard_pool_mode": "site_only",
            "site_guard_pool_ids": [(6, 0, [g.id for g in cls.all_guards[:4]])],
        })
        cls.post_a = cls.env["security.post"].create({
            "name": "Main Gate Sentry",
            "site_id": cls.site_a.id,
        })

        # Site B with 3 regular guards in site_then_relief mode
        cls.site_b = cls.env["security.client.site"].create({
            "name": "NBL Warehouse Depot",
            "partner_id": cls.client.id,
            "guard_pool_mode": "site_then_relief",
            "site_guard_pool_ids": [(6, 0, [g.id for g in cls.all_guards[4:7]])],
        })
        cls.post_b = cls.env["security.post"].create({
            "name": "Warehouse Depot Post",
            "site_id": cls.site_b.id,
        })

    def _create_batch_and_slot(self, site, post, shift_date=None, shift_template=None):
        shift_date = shift_date or date(2026, 4, 1)
        shift_template = shift_template or self.shift_day
        batch = self.env["security.roster.batch"].create({
            "partner_id": self.client.id,
            "site_id": site.id,
            "date_from": shift_date,
            "date_to": shift_date + timedelta(days=6),
            "state": "draft",
        })
        slot = self.env["security.roster.slot"].create({
            "batch_id": batch.id,
            "site_id": site.id,
            "post_id": post.id,
            "shift_date": shift_date,
            "shift_template_id": shift_template.id,
            "state": "draft",
        })
        return batch, slot

    def test_01_auto_assign_picks_only_from_site_pool(self):
        """Scenario 1: Site pool of 4 vs company of 20 -> auto-assign picks only from the 4."""
        batch, slot = self._create_batch_and_slot(self.site_a, self.post_a)
        # Snapshot the pool
        batch._get_effective_site_pool(self.site_a)
        slot.action_auto_assign_all()

        self.assertTrue(slot.employee_id)
        self.assertIn(slot.employee_id.id, self.site_a.site_guard_pool_ids.ids)
        self.assertFalse(slot.is_relief)

    def test_02_pool_guard_on_leave(self):
        """Scenario 2: Pool guard on leave -> another pool guard assigned."""
        test_date = date(2026, 4, 2)
        # Put first 3 pool guards of site A on leave
        for guard in self.all_guards[:3]:
            self.env["security.leave.request"].create({
                "employee_id": guard.id,
                "date_from": test_date,
                "date_to": test_date,
                "state": "approved",
                "leave_type": "annual",
            })

        batch, slot = self._create_batch_and_slot(self.site_a, self.post_a, shift_date=test_date)
        batch._get_effective_site_pool(self.site_a)
        slot.action_auto_assign_all()

        # The 4th guard (index 3) should be assigned
        self.assertEqual(slot.employee_id.id, self.all_guards[3].id)
        self.assertFalse(slot.is_relief)

    def test_03_no_pool_guard_available_in_site_only_critical_gap(self):
        """Scenario 3: No pool guard available in site_only -> critical gap."""
        test_date = date(2026, 4, 3)
        # Put all 4 pool guards on leave
        for guard in self.all_guards[:4]:
            self.env["security.leave.request"].create({
                "employee_id": guard.id,
                "date_from": test_date,
                "date_to": test_date,
                "state": "approved",
                "leave_type": "annual",
            })

        batch, slot = self._create_batch_and_slot(self.site_a, self.post_a, shift_date=test_date)
        batch._get_effective_site_pool(self.site_a)
        slot.action_auto_assign_all()

        self.assertFalse(slot.employee_id)
        self.assertTrue(slot.critical_gap)
        self.assertTrue(slot.wrong_fit_reasons)

    def test_04_no_pool_guard_available_in_site_then_relief_fallback(self):
        """Scenario 4: No pool guard available in site_then_relief -> relief guard assigned with is_relief=True."""
        test_date = date(2026, 4, 4)
        # Site B has guards [4, 5, 6]. Put them on leave.
        for guard in self.all_guards[4:7]:
            self.env["security.leave.request"].create({
                "employee_id": guard.id,
                "date_from": test_date,
                "date_to": test_date,
                "state": "approved",
                "leave_type": "annual",
            })

        batch, slot = self._create_batch_and_slot(self.site_b, self.post_b, shift_date=test_date)
        batch._get_effective_site_pool(self.site_b)
        slot.action_auto_assign_all()

        self.assertTrue(slot.employee_id)
        # Guard must be from outside site B's regular pool
        self.assertNotIn(slot.employee_id.id, self.site_b.site_guard_pool_ids.ids)
        self.assertTrue(slot.is_relief)
        self.assertTrue(slot.relief_reason)

    def test_05_preferred_guard_assignment(self):
        """Scenario 5: Preferred guard available -> preferred guard assigned."""
        preferred_guard = self.all_guards[1]
        req = self.env["security.shift.requirement"].create({
            "site_id": self.site_a.id,
            "post_id": self.post_a.id,
            "shift_template_id": self.shift_day.id,
            "preferred_employee_id": preferred_guard.id,
            "allow_preferred_only": False,
        })
        batch, slot = self._create_batch_and_slot(self.site_a, self.post_a)
        slot.shift_requirement_id = req.id
        batch._get_effective_site_pool(self.site_a)
        slot.action_auto_assign_all()

        self.assertEqual(slot.employee_id.id, preferred_guard.id)
        self.assertTrue(slot.is_preferred_assignment)

    def test_06_preferred_only_blocks_substitution(self):
        """Scenario 6: Preferred-only requirement + unavailable -> critical gap (no substitution)."""
        test_date = date(2026, 4, 5)
        preferred_guard = self.all_guards[1]
        self.env["security.leave.request"].create({
            "employee_id": preferred_guard.id,
            "date_from": test_date,
            "date_to": test_date,
            "state": "approved",
            "leave_type": "annual",
        })

        req = self.env["security.shift.requirement"].create({
            "site_id": self.site_a.id,
            "post_id": self.post_a.id,
            "shift_template_id": self.shift_day.id,
            "preferred_employee_id": preferred_guard.id,
            "allow_preferred_only": True,
        })
        batch, slot = self._create_batch_and_slot(self.site_a, self.post_a, shift_date=test_date)
        slot.shift_requirement_id = req.id
        batch._get_effective_site_pool(self.site_a)
        slot.action_auto_assign_all()

        self.assertFalse(slot.employee_id)
        self.assertTrue(slot.critical_gap)
        self.assertIn("Preferred-only guard", slot.wrong_fit_reasons)

    def test_07_temporary_guard_added_to_batch(self):
        """Scenario 7: Temporary guard added to batch -> participates in that batch only."""
        batch, slot = self._create_batch_and_slot(self.site_a, self.post_a)
        batch._get_effective_site_pool(self.site_a)
        batch_pool = batch.roster_site_pool_ids.filtered(lambda p: p.site_id == self.site_a)

        guest_guard = self.all_guards[15]
        batch_pool.write({
            "added_guard_ids": [(4, guest_guard.id)],
            "guard_ids": [(4, guest_guard.id)],
        })

        eff_guards, _mode = batch._get_effective_site_pool(self.site_a)
        self.assertIn(guest_guard.id, eff_guards.ids)
        self.assertTrue(batch_pool.is_modified_from_defaults)

    def test_08_temporary_guard_removed_from_batch(self):
        """Scenario 8: Temporary guard removed from batch -> excluded from that batch only."""
        batch, slot = self._create_batch_and_slot(self.site_a, self.post_a)
        batch._get_effective_site_pool(self.site_a)
        batch_pool = batch.roster_site_pool_ids.filtered(lambda p: p.site_id == self.site_a)

        removed_guard = self.all_guards[0]
        batch_pool.write({
            "removed_guard_ids": [(4, removed_guard.id)],
            "guard_ids": [(3, removed_guard.id)],
        })

        eff_guards, _mode = batch._get_effective_site_pool(self.site_a)
        self.assertNotIn(removed_guard.id, eff_guards.ids)

    def test_09_temporary_batch_change_does_not_mutate_site_pool(self):
        """Scenario 9: Temporary batch change does not mutate site pool."""
        original_site_guard_ids = set(self.site_a.site_guard_pool_ids.ids)

        batch, slot = self._create_batch_and_slot(self.site_a, self.post_a)
        batch._get_effective_site_pool(self.site_a)
        batch_pool = batch.roster_site_pool_ids.filtered(lambda p: p.site_id == self.site_a)

        guest_guard = self.all_guards[18]
        batch_pool.write({"guard_ids": [(4, guest_guard.id)]})

        # Permanent site pool must remain unchanged
        self.assertEqual(set(self.site_a.site_guard_pool_ids.ids), original_site_guard_ids)

    def test_10_save_as_site_defaults_updates_site_pool(self):
        """Scenario 10: action_save_as_site_defaults() updates site pool."""
        batch, slot = self._create_batch_and_slot(self.site_a, self.post_a)
        batch._get_effective_site_pool(self.site_a)
        batch_pool = batch.roster_site_pool_ids.filtered(lambda p: p.site_id == self.site_a)

        new_guard = self.all_guards[12]
        batch_pool.write({"guard_ids": [(4, new_guard.id)]})
        batch_pool.action_save_as_site_defaults()

        self.assertIn(new_guard.id, self.site_a.site_guard_pool_ids.ids)

    def test_11_site_pool_change_does_not_alter_existing_batch_snapshot(self):
        """Scenario 11: Site pool change after generation does not alter existing batch snapshot."""
        batch, slot = self._create_batch_and_slot(self.site_a, self.post_a)
        batch._get_effective_site_pool(self.site_a)
        batch_pool = batch.roster_site_pool_ids.filtered(lambda p: p.site_id == self.site_a)
        snapshot_guards = set(batch_pool.guard_ids.ids)

        # Mutate the permanent site pool
        new_guard = self.all_guards[19]
        self.site_a.write({"site_guard_pool_ids": [(4, new_guard.id)]})

        # The existing batch snapshot remains unchanged
        self.assertEqual(set(batch_pool.guard_ids.ids), snapshot_guards)

    def test_12_all_sites_view_isolates_slot_candidate_pools(self):
        """Scenario 12: Multi-site roster isolates slot candidate pools."""
        batch = self.env["security.roster.batch"].create({
            "partner_id": self.client.id,
            "site_id": False,  # All Sites batch
            "date_from": date(2026, 4, 10),
            "date_to": date(2026, 4, 16),
            "state": "draft",
        })
        slot_a = self.env["security.roster.slot"].create({
            "batch_id": batch.id,
            "site_id": self.site_a.id,
            "post_id": self.post_a.id,
            "shift_date": date(2026, 4, 10),
            "shift_template_id": self.shift_day.id,
            "state": "draft",
        })
        slot_b = self.env["security.roster.slot"].create({
            "batch_id": batch.id,
            "site_id": self.site_b.id,
            "post_id": self.post_b.id,
            "shift_date": date(2026, 4, 10),
            "shift_template_id": self.shift_day.id,
            "state": "draft",
        })

        # Auto assign both
        (slot_a | slot_b).action_auto_assign_all()

        # Slot A guard must be in Site A pool, Slot B guard must be in Site B pool
        self.assertIn(slot_a.employee_id.id, self.site_a.site_guard_pool_ids.ids)
        self.assertIn(slot_b.employee_id.id, self.site_b.site_guard_pool_ids.ids)

    def test_13_previous_roster_copy_rejects_out_of_pool_guards(self):
        """Scenario 13: Previous roster copy rejects out-of-pool / ineligible guards."""
        batch1, slot1 = self._create_batch_and_slot(self.site_a, self.post_a, shift_date=date(2026, 4, 1))
        assigned_guard = self.all_guards[0]
        slot1.write({"employee_id": assigned_guard.id, "state": "confirmed"})

        # Create batch 2
        batch2, slot2 = self._create_batch_and_slot(self.site_a, self.post_a, shift_date=date(2026, 4, 8))
        # In batch 2, assigned_guard is on approved leave
        self.env["security.leave.request"].create({
            "employee_id": assigned_guard.id,
            "date_from": date(2026, 4, 8),
            "date_to": date(2026, 4, 8),
            "state": "approved",
            "leave_type": "annual",
        })

        batch2.copy_source_batch_id = batch1.id
        batch2.action_copy_from_previous_batch()

        # Slot 2 should remain unassigned because guard is on leave
        self.assertFalse(slot2.employee_id)
        self.assertTrue(slot2.wrong_fit_reasons)

    def test_14_inactive_disqualified_pool_members_excluded(self):
        """Scenario 14: Inactive/disqualified pool members excluded."""
        disqualified_guard = self.all_guards[0]
        disqualified_guard.write({"security_disqualified": True})

        batch, slot = self._create_batch_and_slot(self.site_a, self.post_a)
        batch._get_effective_site_pool(self.site_a)
        slot.action_auto_assign_all()

        self.assertNotEqual(slot.employee_id.id, disqualified_guard.id)

    def test_15_capacity_warning_triggers(self):
        """Scenario 15: Capacity warning triggers when peak staffing > pool size."""
        # Create a site with 4 shift requirements requiring 4 guards, but only 2 guards in pool
        site_c = self.env["security.client.site"].create({
            "name": "Understaffed Site",
            "partner_id": self.client.id,
            "site_guard_pool_ids": [(6, 0, [self.all_guards[0].id, self.all_guards[1].id])],
        })
        post_c = self.env["security.post"].create({"name": "Post C", "site_id": site_c.id})
        for i in range(4):
            self.env["security.shift.requirement"].create({
                "site_id": site_c.id,
                "post_id": post_c.id,
                "shift_template_id": self.shift_day.id,
                "day_of_week": str(i),
            })

        site_c.invalidate_recordset(["guard_pool_capacity_warning", "peak_staffing_required"])
        self.assertTrue(site_c.guard_pool_capacity_warning)

    def test_16_import_wizard_flags_unmatched_names(self):
        """Scenario 16: Import wizard flags unmatched names (< 0.82) without creating fake employees."""
        wizard = self.env["security.roster.team.import.wizard"].create({
            "site_id": self.site_a.id,
            "import_mode": "raw_text",
            "raw_text": f"1. {self.all_guards[0].name}\n2. NonExistent Guard X999",
        })
        wizard.action_parse_and_preview()

        self.assertEqual(len(wizard.line_ids), 2)
        matched_line = wizard.line_ids.filtered(lambda l: l.raw_employee_name == self.all_guards[0].name)
        unmatched_line = wizard.line_ids.filtered(lambda l: "NonExistent" in l.raw_employee_name)

        self.assertEqual(matched_line.match_status, "exact")
        self.assertEqual(unmatched_line.match_status, "unmatched")
        self.assertFalse(unmatched_line.is_confirmed)

    def test_17_import_wizard_confirmation_commits_guards(self):
        """Scenario 17: Import wizard confirmation commits confirmed guards to site pool."""
        new_site = self.env["security.client.site"].create({
            "name": "Fresh Import Site",
            "partner_id": self.client.id,
        })
        wizard = self.env["security.roster.team.import.wizard"].create({
            "site_id": new_site.id,
            "import_mode": "raw_text",
            "raw_text": f"{self.all_guards[8].name}\n{self.all_guards[9].name}",
        })
        wizard.action_parse_and_preview()
        wizard.action_confirm()

        self.assertIn(self.all_guards[8].id, new_site.site_guard_pool_ids.ids)
        self.assertIn(self.all_guards[9].id, new_site.site_guard_pool_ids.ids)
        self.assertEqual(len(new_site.site_guard_pool_ids), 2)
