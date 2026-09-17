from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestEscalation(TransactionCase):
    """docs/deployguard/BUILD-STATUS-AND-PHASE-PLAN.md Phase 6.3: two-level
    escalation, cancelled by acknowledging, paused on stale data. Elapsed
    time is simulated by backdating first_seen_at/last_confirmed_at rather
    than sleeping in real time."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Instance = cls.env["security.exception.instance"]
        cls.Notification = cls.env["security.notification"]
        cls.Policy = cls.env["security.exception.escalation.policy"]
        cls.Rule = cls.env["security.exception.rule"]

        cls.group_l1 = cls.env["res.groups"].create({"name": "Escalation L1 Test Group"})
        cls.group_l2 = cls.env["res.groups"].create({"name": "Escalation L2 Test Group"})
        cls.policy = cls.Policy.create({
            "name": "Test policy", "use_working_calendar": False,
            "level1_delay_minutes": 10, "level1_group_id": cls.group_l1.id,
            "level2_delay_minutes": 30, "level2_group_id": cls.group_l2.id,
        })
        cls.rule = cls.Rule.create({
            "notification_type": "cert_expiry", "tier": "attention",
            "escalation_policy_id": cls.policy.id, "stale_after_minutes": 60,
        })

    def _instance(self, minutes_old, last_confirmed_minutes_ago=0):
        notification = self.Notification.create({
            "title": "Test cert expiry", "notification_type": "cert_expiry", "state": "unread",
        })
        instance = self.Instance.create({
            "notification_id": notification.id, "rule_id": self.rule.id,
            "first_seen_at": fields.Datetime.now() - timedelta(minutes=minutes_old),
            "last_confirmed_at": fields.Datetime.now() - timedelta(minutes=last_confirmed_minutes_ago),
        })
        return instance

    def test_no_escalation_before_level1_delay(self):
        instance = self._instance(minutes_old=5)
        self.Instance.action_process_escalations()
        self.assertEqual(instance.escalation_level, 0)

    def test_escalates_to_level1_after_delay(self):
        instance = self._instance(minutes_old=11)
        self.Instance.action_process_escalations()
        self.assertEqual(instance.escalation_level, 1)
        self.assertTrue(instance.escalated_at)

    def test_escalates_to_level2_after_second_delay(self):
        instance = self._instance(minutes_old=31)
        instance.write({"escalation_level": 1})
        self.Instance.action_process_escalations()
        self.assertEqual(instance.escalation_level, 2)

    def test_acknowledging_stops_escalation(self):
        instance = self._instance(minutes_old=31)
        instance.action_acknowledge()
        self.Instance.action_process_escalations()
        self.assertEqual(instance.escalation_level, 0, "acknowledged instances must never be escalated")

    def test_stale_data_pauses_escalation(self):
        instance = self._instance(minutes_old=31, last_confirmed_minutes_ago=90)
        self.Instance.action_process_escalations()
        self.assertEqual(instance.state, "stale_paused")
        self.assertEqual(instance.escalation_level, 0, "must not escalate on data nobody has reconfirmed")

    def test_reconfirmed_data_unpauses(self):
        instance = self._instance(minutes_old=31, last_confirmed_minutes_ago=90)
        self.Instance.action_process_escalations()
        self.assertEqual(instance.state, "stale_paused")

        instance.last_confirmed_at = fields.Datetime.now()
        self.Instance.action_process_escalations()
        self.assertEqual(instance.state, "open")
        self.assertEqual(instance.escalation_level, 1)
