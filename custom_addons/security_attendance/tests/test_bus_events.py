from odoo.tests.common import TransactionCase


class TestAttendanceBusEvents(TransactionCase):
    """docs/deployguard/12-odoo-integration.md §4 event catalogue. Needed as
    real infrastructure for security_work's auto-completion (Phase 3)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Bus Event Test Client"})
        cls.front_desk_user = cls.env["res.users"].create({
            "name": "Bus Event Front Desk",
            "login": "bus_event_front_desk_user",
            "groups_id": [(6, 0, [
                cls.env.ref("security_operations.group_security_front_desk").id
            ])],
        })

    def _batch(self):
        return self.env["security.attendance.batch"].create({
            "partner_id": self.partner.id,
            "state": "captured",
        })

    def test_review_emits_bus_event(self):
        batch = self._batch()
        before = self.env["security.event.log"].search_count(
            [("name", "=", "attendance.batch.reviewed"), ("source_id", "=", batch.id)]
        )
        batch.with_user(self.front_desk_user).action_review()
        after = self.env["security.event.log"].search_count(
            [("name", "=", "attendance.batch.reviewed"), ("source_id", "=", batch.id)]
        )
        self.assertEqual(after, before + 1)

    def test_lock_emits_bus_event(self):
        batch = self._batch()
        batch.action_lock()
        self.assertTrue(
            self.env["security.event.log"].search_count(
                [("name", "=", "attendance.batch.locked"), ("source_id", "=", batch.id)]
            )
        )

    def test_event_payload_carries_site_and_date(self):
        import json
        site = self.env["security.client.site"].create({
            "name": "Bus Event Site", "partner_id": self.partner.id,
        })
        batch = self.env["security.attendance.batch"].create({
            "partner_id": self.partner.id, "site_id": site.id,
            "state": "captured", "attendance_date": "2026-08-15",
        })
        batch.action_lock()
        event = self.env["security.event.log"].search(
            [("name", "=", "attendance.batch.locked"), ("source_id", "=", batch.id)], limit=1
        )
        payload = json.loads(event.event_data)
        self.assertEqual(payload["site_id"], site.id)
        self.assertEqual(payload["attendance_date"], "2026-08-15")
