from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestScoreSnapshot(TransactionCase):
    """docs/deployguard/09-adoption-engine.md §3. Feeds
    security.adoption.expected.work.item rows directly rather than going
    through materialization, since scoring only ever reads item state --
    that's the model boundary this test exercises."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create({"name": "Scoring Guard"})
        cls.definition = cls.env.ref("security_adoption.def_attendance_post")
        cls.Item = cls.env["security.adoption.expected.work.item"]
        cls.Snapshot = cls.env["security.adoption.snapshot"]

    def _item(self, days_ago, state, on_time=False, excusal_reason=None):
        period_date = fields.Date.context_today(self.Item) - timedelta(days=days_ago)
        return self.Item.create({
            "definition_id": self.definition.id, "employee_id": self.employee.id,
            "period_date": period_date, "state": state, "on_time": on_time,
            "excusal_reason": excusal_reason,
        })

    def test_insufficient_confidence_below_five_items(self):
        for i in range(3):
            self._item(i + 1, "fulfilled", on_time=True)
        window_end = fields.Date.context_today(self.Item) - timedelta(days=1)
        snapshot = self.Snapshot._compute_for_employee(
            self.employee.id, window_end - timedelta(days=6), window_end
        )
        self.assertEqual(snapshot.confidence, "insufficient")

    def test_full_coverage_scores_high_with_medium_confidence(self):
        for i in range(1, 16):
            self._item(i, "fulfilled", on_time=True)
        window_end = fields.Date.context_today(self.Item) - timedelta(days=1)
        snapshot = self.Snapshot._compute_for_employee(
            self.employee.id, window_end - timedelta(days=6), window_end
        )
        self.assertEqual(snapshot.confidence, "medium")
        self.assertEqual(snapshot.expected_total, 15)
        f1 = snapshot.factor_ids.filtered(lambda f: f.factor_key == "f1_coverage")
        self.assertEqual(f1.raw_value, 100.0)

    def test_excused_items_do_not_count_against_coverage(self):
        for i in range(1, 6):
            self._item(i, "fulfilled", on_time=True)
        for i in range(6, 9):
            self._item(i, "excused", excusal_reason="leave")
        window_end = fields.Date.context_today(self.Item) - timedelta(days=1)
        snapshot = self.Snapshot._compute_for_employee(
            self.employee.id, window_end - timedelta(days=13), window_end
        )
        f1 = snapshot.factor_ids.filtered(lambda f: f.factor_key == "f1_coverage")
        self.assertEqual(f1.raw_value, 100.0, "excused items must not appear in the coverage denominator")
        self.assertEqual(snapshot.excused_total, 3)

    def test_missed_items_reduce_coverage(self):
        for i in range(1, 6):
            self._item(i, "fulfilled", on_time=True)
        for i in range(6, 11):
            self._item(i, "missed")
        window_end = fields.Date.context_today(self.Item) - timedelta(days=1)
        snapshot = self.Snapshot._compute_for_employee(
            self.employee.id, window_end - timedelta(days=13), window_end
        )
        f1 = snapshot.factor_ids.filtered(lambda f: f.factor_key == "f1_coverage")
        self.assertEqual(f1.raw_value, 50.0)

    def test_late_fulfilment_reduces_timeliness_not_coverage(self):
        for i in range(1, 6):
            self._item(i, "fulfilled", on_time=True)
        self._item(6, "fulfilled", on_time=False)
        window_end = fields.Date.context_today(self.Item) - timedelta(days=1)
        snapshot = self.Snapshot._compute_for_employee(
            self.employee.id, window_end - timedelta(days=13), window_end
        )
        f1 = snapshot.factor_ids.filtered(lambda f: f.factor_key == "f1_coverage")
        f2 = snapshot.factor_ids.filtered(lambda f: f.factor_key == "f2_timeliness")
        self.assertEqual(f1.raw_value, 100.0)
        self.assertAlmostEqual(f2.raw_value, 5 / 6 * 100.0)

    def test_rule_version_is_stamped_on_every_snapshot(self):
        for i in range(1, 6):
            self._item(i, "fulfilled", on_time=True)
        window_end = fields.Date.context_today(self.Item) - timedelta(days=1)
        snapshot = self.Snapshot._compute_for_employee(
            self.employee.id, window_end - timedelta(days=13), window_end
        )
        self.assertTrue(snapshot.rule_version)
