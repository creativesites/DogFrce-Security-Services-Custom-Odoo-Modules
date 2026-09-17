from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestExceptionIngestion(TransactionCase):
    """docs/deployguard/BUILD-STATUS-AND-PHASE-PLAN.md Phase 6.1, 6.2:
    exception instances are ingested 1:1 from security.notification, never
    re-derived from the underlying condition."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Instance = cls.env["security.exception.instance"]
        cls.Notification = cls.env["security.notification"]

    def _notification(self, notification_type="roster_gap", state="unread"):
        return self.Notification.create({
            "title": "Test alert", "notification_type": notification_type, "state": state,
        })

    def test_sync_creates_one_instance_per_open_notification(self):
        notification = self._notification()
        self.Instance.action_sync_from_notifications()
        instances = self.Instance.search([("notification_id", "=", notification.id)])
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances.state, "open")
        self.assertEqual(instances.tier, "critical")

    def test_sync_is_idempotent_no_duplicate_instance(self):
        notification = self._notification()
        self.Instance.action_sync_from_notifications()
        self.Instance.action_sync_from_notifications()
        count = self.Instance.search_count([("notification_id", "=", notification.id)])
        self.assertEqual(count, 1)

    def test_dismissing_source_notification_auto_resolves(self):
        notification = self._notification()
        self.Instance.action_sync_from_notifications()
        notification.action_dismiss()
        self.Instance.action_sync_from_notifications()
        instance = self.Instance.search([("notification_id", "=", notification.id)])
        self.assertEqual(instance.state, "auto_resolved")
        self.assertTrue(instance.resolved_at)

    def test_no_rule_no_instance(self):
        """A notification_type with no active security.exception.rule
        (e.g. "system") is never ingested -- Phase 6 only triages the
        notification_types it has an explicit rule for."""
        notification = self._notification(notification_type="system")
        self.Instance.action_sync_from_notifications()
        self.assertFalse(self.Instance.search([("notification_id", "=", notification.id)]))

    def test_acknowledge_and_resolve_lifecycle(self):
        notification = self._notification()
        self.Instance.action_sync_from_notifications()
        instance = self.Instance.search([("notification_id", "=", notification.id)])

        instance.action_acknowledge()
        self.assertEqual(instance.state, "acknowledged")
        self.assertEqual(instance.acknowledged_by_id, self.env.user)

        instance.action_resolve()
        self.assertEqual(instance.state, "resolved")
        self.assertTrue(instance.resolved_at)

        instance.action_reopen()
        self.assertEqual(instance.state, "open")
        self.assertFalse(instance.resolved_at)
