import json
import os

from odoo import fields
from odoo.tests.common import TransactionCase

from odoo.addons.security_deployguard_bridge.models import security_deployguard_crypto as crypto


class TestDeployguardOutbox(TransactionCase):

    def setUp(self):
        super().setUp()
        self._orig_env_key = os.environ.get(crypto.MASTER_KEY_ENV_VAR)
        os.environ[crypto.MASTER_KEY_ENV_VAR] = "a-test-master-key"
        self.addCleanup(self._restore_env_key)

    def _restore_env_key(self):
        if self._orig_env_key is not None:
            os.environ[crypto.MASTER_KEY_ENV_VAR] = self._orig_env_key
        else:
            os.environ.pop(crypto.MASTER_KEY_ENV_VAR, None)

    def test_enqueue_builds_the_documented_envelope(self):
        row = self.env["security.deployguard.outbox"].enqueue(
            "attendance.batch.submitted",
            {"site_id": 1, "state": "captured"},
            model="security.attendance.batch",
            res_id=42,
        )
        envelope = json.loads(row.payload)
        self.assertEqual(envelope["type"], "attendance.batch.submitted")
        self.assertEqual(envelope["odoo"]["model"], "security.attendance.batch")
        self.assertEqual(envelope["odoo"]["res_id"], 42)
        self.assertEqual(envelope["data"]["state"], "captured")
        self.assertTrue(envelope["event_id"])
        self.assertTrue(envelope["correlation_id"])
        self.assertEqual(row.state, "pending")

    def test_enqueue_generates_unique_event_ids(self):
        Outbox = self.env["security.deployguard.outbox"]
        first = Outbox.enqueue("test.event", {})
        second = Outbox.enqueue("test.event", {})
        self.assertNotEqual(first.event_id, second.event_id)

    def test_dispatch_without_platform_url_reschedules_not_fails_dead(self):
        row = self.env["security.deployguard.outbox"].enqueue("test.event", {})
        row.action_dispatch_due()
        row.invalidate_recordset()
        self.assertEqual(row.state, "failed")
        self.assertEqual(row.attempts, 1)
        self.assertIn("No DeployGuard Platform URL", row.last_error)

    def test_backoff_doubles_each_attempt(self):
        row = self.env["security.deployguard.outbox"].enqueue("test.event", {})
        delays = []
        previous = row.next_attempt_at
        for _ in range(3):
            row.action_dispatch_due()
            row.invalidate_recordset()
            delay = (row.next_attempt_at - previous).total_seconds() / 60.0
            delays.append(round(delay))
            previous = row.next_attempt_at
        self.assertEqual(delays, [1, 2, 4])

    def test_row_goes_dead_after_max_attempts(self):
        row = self.env["security.deployguard.outbox"].enqueue("test.event", {})
        row.write({"attempts": 19})
        row._reschedule("forced failure")
        self.assertEqual(row.state, "dead")

    def test_requeue_resets_a_dead_row(self):
        row = self.env["security.deployguard.outbox"].enqueue("test.event", {})
        row.write({"state": "dead", "attempts": 20, "last_error": "boom"})
        row.action_requeue()
        self.assertEqual(row.state, "pending")
        self.assertEqual(row.attempts, 0)
        self.assertFalse(row.last_error)

    def test_requeue_leaves_pending_rows_alone(self):
        row = self.env["security.deployguard.outbox"].enqueue("test.event", {})
        row.action_requeue()
        self.assertEqual(row.state, "pending")
        self.assertEqual(row.attempts, 0)

    def test_dispatch_due_only_picks_up_rows_whose_time_has_come(self):
        Outbox = self.env["security.deployguard.outbox"]
        due = Outbox.enqueue("test.event.due", {})
        not_due = Outbox.enqueue("test.event.not_due", {})
        not_due.next_attempt_at = fields.Datetime.add(fields.Datetime.now(), hours=1)

        Outbox.action_dispatch_due()

        due.invalidate_recordset()
        not_due.invalidate_recordset()
        self.assertEqual(due.attempts, 1)
        self.assertEqual(not_due.attempts, 0)

    def test_signature_changes_with_secret(self):
        config = self.env["security.deployguard.config"].get_config()
        config.action_generate_webhook_secret()
        secret_a = config.get_webhook_secret()
        row = self.env["security.deployguard.outbox"].enqueue("test.event", {"a": 1})
        sig_a = row._sign(secret_a)

        config.action_generate_webhook_secret()
        secret_b = config.get_webhook_secret()
        sig_b = row._sign(secret_b)

        self.assertNotEqual(sig_a, sig_b)
        self.assertTrue(sig_a.startswith("t="))
        self.assertIn(",v1=", sig_a)
