# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestRosterScheduleImport(TransactionCase):
    """
    Test suite for Security Roster Schedule Import Wizard:
    - Matrix & Tabular parsing
    - Guard matching engine (exact, transposed, fuzzy)
    - Slot creation & unassigned gap filling
    - Override handling & conflict flagging (double booking, leave)
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = cls.env["res.partner"].create({
            "name": "Namibia Breweries Ltd (Test)",
            "is_company": True,
        })
        cls.shift_day = cls.env["security.shift.template"].create({
            "name": "Day Shift 12h",
            "start_hour": 6.0,
            "end_hour": 18.0,
            "duration_hours": 12.0,
        })
        cls.shift_night = cls.env["security.shift.template"].create({
            "name": "Night Shift 12h",
            "start_hour": 18.0,
            "end_hour": 6.0,
            "duration_hours": 12.0,
        })
        cls.grade_a = cls.env["security.grade"].create({
            "name": "Grade A Import",
            "code": "GRA_IMP",
            "hourly_rate": 35.0,
            "sequence": 1,
        })
        cls.post_type = cls.env["security.post.type"].create({
            "name": "Import Test Post Type",
            "code": "ITPT",
            "min_grade_id": cls.grade_a.id,
        })
        cls.site = cls.env["security.client.site"].create({
            "name": "Eros Main Depot",
            "code": "EMD01",
            "partner_id": cls.client.id,
            "guard_pool_mode": "site_then_relief",
        })
        cls.post = cls.env["security.post"].create({
            "name": "Main Gate",
            "site_id": cls.site.id,
            "post_type_id": cls.post_type.id,
        })

        # Create guards with varying naming structures
        cls.guard1 = cls.env["hr.employee"].create({
            "name": "Petrus Shilongo",
            "employee_code": "DF001",
            "security_guard": True,
            "security_grade_id": cls.grade_a.id,
            "active": True,
            "security_disqualified": False,
        })
        cls.guard2 = cls.env["hr.employee"].create({
            "name": "Johannes Amukoto",
            "employee_code": "DF002",
            "security_guard": True,
            "security_grade_id": cls.grade_a.id,
            "active": True,
            "security_disqualified": False,
        })
        cls.guard3 = cls.env["hr.employee"].create({
            "name": "Matheus Shikongo",
            "employee_code": "DF003",
            "security_guard": True,
            "security_grade_id": cls.grade_a.id,
            "active": True,
            "security_disqualified": False,
        })

        # Assign guard1 to regular site pool
        cls.site.write({"site_guard_pool_ids": [(4, cls.guard1.id)]})

        # Create an existing roster batch and slot for Eros Main Depot on 2026-10-21
        cls.batch = cls.env["security.roster.batch"].create({
            "name": "Test Cycle Oct-Nov 2026",
            "date_from": date(2026, 10, 21),
            "date_to": date(2026, 11, 20),
            "state": "draft",
        })
        cls.existing_slot_unassigned = cls.env["security.roster.slot"].create({
            "batch_id": cls.batch.id,
            "site_id": cls.site.id,
            "post_id": cls.post.id,
            "shift_template_id": cls.shift_day.id,
            "shift_date": date(2026, 10, 21),
            "state": "draft",
            "employee_id": False,
            "critical_gap": True,
        })
        cls.existing_slot_assigned = cls.env["security.roster.slot"].create({
            "batch_id": cls.batch.id,
            "site_id": cls.site.id,
            "post_id": cls.post.id,
            "shift_template_id": cls.shift_day.id,
            "shift_date": date(2026, 10, 22),
            "state": "assigned",
            "employee_id": cls.guard1.id,
            "critical_gap": False,
        })

    def test_01_tabular_csv_import_fills_gap_and_overrides(self):
        """Test importing CSV format text fills unassigned gap on Oct 21 and overrides guard on Oct 22."""
        csv_text = (
            "Site,Date,Shift,Guard\n"
            "Eros Main Depot,2026-10-21,Day,Petrus Shilongo\n"
            "Eros Main Depot,2026-10-22,Day,Johannes Amukoto\n"
        )
        wizard = self.env["security.roster.schedule.import.wizard"].create({
            "site_id": self.site.id,
            "date_from": date(2026, 10, 21),
            "date_to": date(2026, 11, 20),
            "import_mode": "text",
            "raw_text": csv_text,
            "override_assigned": True,
            "create_missing_slots": True,
        })
        wizard.action_parse_and_preview()

        self.assertEqual(len(wizard.line_ids), 2)
        line21 = wizard.line_ids.filtered(lambda l: l.shift_date == date(2026, 10, 21))
        line22 = wizard.line_ids.filtered(lambda l: l.shift_date == date(2026, 10, 22))

        self.assertEqual(line21.action_type, "fill", "Oct 21 should fill open slot")
        self.assertEqual(line21.employee_id.id, self.guard1.id)
        self.assertEqual(line22.action_type, "override", "Oct 22 should override guard1 with guard2")
        self.assertEqual(line22.employee_id.id, self.guard2.id)

        # Apply import
        wizard.action_apply_import()

        self.existing_slot_unassigned.invalidate_recordset()
        self.existing_slot_assigned.invalidate_recordset()

        self.assertEqual(self.existing_slot_unassigned.employee_id.id, self.guard1.id)
        self.assertFalse(self.existing_slot_unassigned.critical_gap)
        self.assertEqual(self.existing_slot_assigned.employee_id.id, self.guard2.id)
        self.assertTrue(self.existing_slot_assigned.is_override)

    def test_02_guard_matching_transposed_and_fuzzy(self):
        """Test matching transposed 'Shilongo, Petrus' and fuzzy name variations."""
        csv_text = (
            "Site,Date,Shift,Guard\n"
            "Eros Main Depot,2026-10-23,Day,Shilongo Petrus\n"
            "Eros Main Depot,2026-10-24,Night,Amukoto Johaness\n"
        )
        wizard = self.env["security.roster.schedule.import.wizard"].create({
            "site_id": self.site.id,
            "date_from": date(2026, 10, 21),
            "date_to": date(2026, 11, 20),
            "import_mode": "text",
            "raw_text": csv_text,
            "create_missing_slots": True,
        })
        wizard.action_parse_and_preview()

        self.assertEqual(len(wizard.line_ids), 2)
        l1 = wizard.line_ids.filtered(lambda l: l.shift_date == date(2026, 10, 23))
        l2 = wizard.line_ids.filtered(lambda l: l.shift_date == date(2026, 10, 24))

        self.assertEqual(l1.employee_id.id, self.guard1.id, "Transposed Petrus Shilongo should match")
        self.assertEqual(l2.employee_id.id, self.guard2.id, "Fuzzy Amukoto Johaness should match")

    def test_03_double_booking_conflict_detection(self):
        """Test conflict flagging when the same guard appears multiple times on the same date."""
        csv_text = (
            "Site,Date,Shift,Guard\n"
            "Eros Main Depot,2026-10-25,Day,Matheus Shikongo\n"
            "Eros Main Depot,2026-10-25,Night,Matheus Shikongo\n"
        )
        wizard = self.env["security.roster.schedule.import.wizard"].create({
            "site_id": self.site.id,
            "date_from": date(2026, 10, 21),
            "date_to": date(2026, 11, 20),
            "import_mode": "text",
            "raw_text": csv_text,
            "create_missing_slots": True,
        })
        wizard.action_parse_and_preview()

        self.assertEqual(len(wizard.line_ids), 2)
        for l in wizard.line_ids:
            self.assertEqual(l.clash_type, "double_booking", "Multiple shifts on same date should warn double-booking")
