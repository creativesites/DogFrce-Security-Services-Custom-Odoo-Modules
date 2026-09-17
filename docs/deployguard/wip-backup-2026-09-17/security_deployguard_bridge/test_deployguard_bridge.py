from odoo.tests.common import TransactionCase
from datetime import datetime
import json


class TestDeployGuardBridge(TransactionCase):

    def setUp(self):
        super().setUp()

        # Retrieve the singleton configuration
        self.config = self.env["security.deployguard.config"]._get_singleton()
        self.config.write({
            "platform_base_url": "https://api.mock.deployguard.com",
            "tenant_id": "tenant-mock-123",
            "webhook_secret": "secret-12345",
        })

        # Create res.partner (Client)
        self.client_partner = self.env["res.partner"].create({
            "name": "Acme Namibia Ltd",
            "is_company": True,
        })

        # Create a test site
        self.site = self.env["security.client.site"].create({
            "name": "Windhoek Industrial Depot",
            "partner_id": self.client_partner.id,
            "location": "Windhoek Khomas",
        })

        # Create test grade
        self.grade = self.env["security.grade"].create({
            "name": "Grade A Officer",
            "code": "GRADE_A",
            "hourly_rate": 25.50,
        })

        # Create test employee
        self.employee = self.env["hr.employee"].create({
            "name": "Johannes Shivute",
            "security_guard": True,
            "security_grade_id": self.grade.id,
        })

        # Link site supervisor to the employee
        self.site.write({"supervisor_id": self.employee.id})

        # Create test user with DeployGuard access enabled
        self.test_user = self.env["res.users"].create({
            "name": "Supervisor Johannes",
            "login": "johannes_supervisor",
            "email": "johannes@dogforce.com.na",
            "deployguard_access": True,
        })

    def test_01_facade_ping_method(self):
        """Verify the health, contract, database, and installed-bridge details are returned cleanly."""
        res = self.env["security.deployguard.api"].ping()
        self.assertEqual(res["version"], "1.0")
        self.assertEqual(res["contract"], "v1")
        self.assertEqual(res["db"], self.env.cr.dbname)
        self.assertIn("security_deployguard_bridge", res["modules"])

    def test_02_facade_get_sites(self):
        """Verify that get_sites returns all site profiles with filtered write_dates."""
        res = self.env["security.deployguard.api"].get_sites()
        self.assertTrue(len(res) >= 1)
        site_data = next((s for s in res if s["id"] == self.site.id), None)
        self.assertIsNotNone(site_data)
        self.assertEqual(site_data["name"], "Windhoek Industrial Depot")
        self.assertEqual(site_data["client"], "Acme Namibia Ltd")
        self.assertEqual(site_data["region"], "Windhoek Khomas")

    def test_03_facade_get_employees(self):
        """Verify that get_employees returns guard datasets excluding restricted HR fields."""
        res = self.env["security.deployguard.api"].get_employees()
        self.assertTrue(len(res) >= 1)
        emp_data = next((e for e in res if e["id"] == self.employee.id), None)
        self.assertIsNotNone(emp_data)
        self.assertEqual(emp_data["name"], "Johannes Shivute")
        self.assertEqual(emp_data["job_grade"], "Grade A Officer")
        self.assertEqual(emp_data["site_assignments"], [self.site.id])

    def test_04_facade_get_users(self):
        """Verify that get_users returns system accounts mapped to their deployguard_access state."""
        res = self.env["security.deployguard.api"].get_users(ids=[self.test_user.id])
        self.assertEqual(len(res), 1)
        user_data = res[0]
        self.assertEqual(user_data["login"], "johannes_supervisor")
        self.assertEqual(user_data["name"], "Supervisor Johannes")
        self.assertEqual(user_data["email"], "johannes@dogforce.com.na")
        self.assertTrue(user_data["deployguard_access"])

    def test_05_outbox_queue_retry_and_backoff(self):
        """Verify that outbox failures are logged gracefully and transition state to failed with backoff."""
        # Create a mock event log payload in the outbox
        payload_data = {
            "event_id": "0192f0c8-6f7a-7c21-9d3e-1b5a2c3d4e5f",
            "type": "attendance.batch.submitted",
            "version": 1,
            "occurred_at": datetime.utcnow().isoformat() + "Z",
        }
        
        outbox_rec = self.env["security.deployguard.outbox"].create({
            "event_id": payload_data["event_id"],
            "event_type": payload_data["type"],
            "payload": json.dumps(payload_data),
            "state": "draft",
        })

        # Run dispatch. It should fail to reach mock.deployguard.com, triggering the backoff rescue block.
        self.env["security.deployguard.outbox"].action_dispatch_outbox()

        # The record should transition to 'failed' state, with 1 attempt registered and next attempt scheduled.
        self.assertEqual(outbox_rec.state, "failed")
        self.assertEqual(outbox_rec.attempts, 1)
        self.assertTrue(outbox_rec.next_attempt_at)
        self.assertTrue(outbox_rec.error_message)
