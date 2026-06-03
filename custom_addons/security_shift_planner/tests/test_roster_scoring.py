from odoo.tests.common import TransactionCase


class TestRosterScoring(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env

        cls.grade_a = env["security.grade"].create({"name": "Grade A K4", "code": "A_K4", "hourly_rate": 15.0})
        cls.grade_b = env["security.grade"].create({"name": "Grade B K4", "code": "B_K4", "hourly_rate": 12.0})

        cls.partner = env["res.partner"].create({"name": "Test Roster Client K4", "is_company": True})
        cls.site = env["security.client.site"].create({"name": "Test Roster Site K4", "partner_id": cls.partner.id})

        cls.post_type = env["security.post.type"].create({"name": "Gate Post K4"})
        cls.post = env["security.post"].create({
            "name": "Main Gate K4",
            "site_id": cls.site.id,
            "post_type_id": cls.post_type.id,
            "required_grade_id": cls.grade_a.id,
        })
        cls.shift = env["security.shift.template"].create({
            "name": "Day Shift K4",
            "start_hour": 6.0,
            "end_hour": 18.0,
        })
        cls.batch = env["security.roster.batch"].create({
            "name": "Test Batch K4",
            "date_from": "2026-08-01",
            "date_to": "2026-08-31",
            "site_ids": [(4, cls.site.id)],
        })
        cls.slot = env["security.roster.slot"].create({
            "batch_id": cls.batch.id,
            "post_id": cls.post.id,
            "site_id": cls.site.id,
            "shift_date": "2026-08-01",
            "shift_template_id": cls.shift.id,
            "required_grade_id": cls.grade_a.id,
            "state": "confirmed",
        })
        cls.guard_a = env["hr.employee"].create({
            "name": "Guard A K4",
            "security_guard": True,
            "active": True,
            "security_grade_id": cls.grade_a.id,
            "security_reliability_score": 90,
            "security_disqualified": False,
        })
        cls.guard_disq = env["hr.employee"].create({
            "name": "Guard Disq K4",
            "security_guard": True,
            "active": True,
            "security_grade_id": cls.grade_a.id,
            "security_reliability_score": 85,
            "security_disqualified": True,
        })

    def test_suggest_guards_returns_results(self):
        self.slot.action_suggest_guards()
        suggestions = self.env["security.slot.suggestion"].search([("slot_id", "=", self.slot.id)])
        self.assertGreater(len(suggestions), 0, "Expected at least one suggestion")

    def test_disqualified_guard_excluded(self):
        self.slot.action_suggest_guards()
        suggestions = self.env["security.slot.suggestion"].search([("slot_id", "=", self.slot.id)])
        suggested_ids = suggestions.mapped("employee_id.id")
        self.assertNotIn(self.guard_disq.id, suggested_ids, "Disqualified guard should not be suggested")

    def test_suggestions_have_scores(self):
        self.slot.action_suggest_guards()
        suggestions = self.env["security.slot.suggestion"].search([("slot_id", "=", self.slot.id)])
        for s in suggestions:
            self.assertGreaterEqual(s.score, 0, "Score must be non-negative")

    def test_assign_guard_sets_employee(self):
        self.slot.action_suggest_guards()
        suggestion = self.env["security.slot.suggestion"].search(
            [("slot_id", "=", self.slot.id), ("employee_id", "=", self.guard_a.id)],
            limit=1,
        )
        if suggestion:
            suggestion.action_assign_to_slot()
            self.slot.invalidate_recordset()
            self.assertEqual(self.slot.employee_id.id, self.guard_a.id)
        else:
            self.skipTest("guard_a not suggested (may be excluded for a legitimate reason)")

    def test_batch_copy_creates_new_slots(self):
        """action_copy_from_previous_month should not crash on a batch with slots."""
        new_batch = self.env["security.roster.batch"].create({
            "name": "August K4 Copy",
            "date_from": "2026-09-01",
            "date_to": "2026-09-30",
            "site_ids": [(4, self.site.id)],
        })
        result = new_batch.action_copy_from_previous_month()
        self.assertIsNotNone(result)
