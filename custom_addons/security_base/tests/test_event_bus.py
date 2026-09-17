from odoo.tests.common import TransactionCase


class TestSecurityEventBus(TransactionCase):

    def setUp(self):
        super().setUp()

    def test_01_event_registration_and_dynamic_dispatch(self):
        """Verify that registering an event creates a processed log and routes without exception."""
        # Register a test event
        log = self.env["security.event.log"].register_event(
            name="attendance.missed",
            source_model="security.attendance.record",
            source_id=99,
            payload={"guard_name": "Test Guard", "site_name": "Test Site"},
        )

        self.assertEqual(log.name, "attendance.missed")
        self.assertEqual(log.source_model, "security.attendance.record")
        self.assertEqual(log.source_id, 99)
        self.assertEqual(log.state, "processed", "Event log should be marked as processed after dispatch.")
