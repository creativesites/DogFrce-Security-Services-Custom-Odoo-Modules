from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBaselineAndAbandonment(TransactionCase):
    """docs/deployguard/09-adoption-engine.md §5."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create({"name": "Abandonment Guard"})
        cls.definition = cls.env.ref("security_adoption.def_attendance_post")
        cls.Item = cls.env["security.adoption.expected.work.item"]
        cls.Baseline = cls.env["security.adoption.baseline"]
        cls.Signal = cls.env["security.adoption.abandonment.signal"]

    def _item(self, days_ago, state):
        period_date = fields.Date.context_today(self.Item) - timedelta(days=days_ago)
        return self.Item.create({
            "definition_id": self.definition.id, "employee_id": self.employee.id,
            "period_date": period_date, "state": state,
        })

    def _seed_healthy_history(self, weeks=6, per_week=5, start_days_ago=10):
        """Seeds fulfilled history starting `start_days_ago` back, leaving
        the trailing days free for tests to layer a recent deviation on
        top without colliding with the unique (definition, employee,
        site, period_date, source_res_id) constraint."""
        for week in range(weeks):
            for day in range(per_week):
                self._item(start_days_ago + week * 7 + day, "fulfilled")

    def test_no_baseline_below_minimum_history(self):
        for day in range(3):
            self._item(day + 1, "fulfilled")
        self.Baseline.action_compute_all()
        baseline = self.Baseline.search([("employee_id", "=", self.employee.id)])
        self.assertFalse(baseline.has_enough_history)

    def test_baseline_reflects_healthy_history(self):
        self._seed_healthy_history()
        self.Baseline.action_compute_all()
        baseline = self.Baseline.search([("employee_id", "=", self.employee.id)])
        self.assertTrue(baseline.has_enough_history)
        self.assertGreater(baseline.rate, 90.0)

    def test_deviation_after_healthy_history_triggers_a_signal(self):
        """3 consecutive missed days against a near-100% baseline satisfies
        both spec §5 trigger conditions at once (a trailing-window
        fulfilment collapse *is* 3+ consecutive misses here) -- either is
        a correct detection of the same real deviation, so this only
        asserts that a signal opens, not which named trigger fired."""
        self._seed_healthy_history()
        self.Baseline.action_compute_all()
        for day in range(1, 4):
            self._item(day, "missed")
        self.Signal.action_detect_all()
        signal = self.Signal.search([("employee_id", "=", self.employee.id)])
        self.assertEqual(len(signal), 1)
        self.assertIn(signal.trigger_type, ("consecutive_missed", "below_baseline"))
        self.assertEqual(signal.state, "signal")

    def test_no_signal_when_no_deviation(self):
        self._seed_healthy_history()
        self.Baseline.action_compute_all()
        self.Signal.action_detect_all()
        self.assertFalse(self.Signal.search([("employee_id", "=", self.employee.id)]))

    def test_signal_lifecycle_and_checkin_routing(self):
        self._seed_healthy_history()
        self.Baseline.action_compute_all()
        for day in range(1, 4):
            self._item(day, "missed")
        self.Signal.action_detect_all()
        signal = self.Signal.search([("employee_id", "=", self.employee.id)])

        signal.action_start_investigating()
        self.assertEqual(signal.state, "investigating")

        signal.action_send_assist_checkin()
        self.assertEqual(signal.state, "assist")
        self.assertEqual(len(signal.checkin_ids), 1)

        signal.checkin_ids.action_record_answer("too_busy")
        self.assertIn("operations manager", signal.checkin_ids.routed_action)

        signal.action_escalate()
        self.assertEqual(signal.state, "escalated")
        self.assertTrue(signal.escalated_at)

    def test_second_run_does_not_duplicate_open_signal(self):
        self._seed_healthy_history()
        self.Baseline.action_compute_all()
        for day in range(1, 4):
            self._item(day, "missed")
        self.Signal.action_detect_all()
        self.Signal.action_detect_all()
        self.assertEqual(
            self.Signal.search_count([("employee_id", "=", self.employee.id)]), 1
        )
