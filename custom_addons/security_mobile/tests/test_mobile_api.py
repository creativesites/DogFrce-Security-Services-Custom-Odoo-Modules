from odoo.tests.common import HttpCase


class TestMobileAPI(HttpCase):
    """Basic smoke tests for the security_mobile REST endpoints."""

    def setUp(self):
        super().setUp()
        # Authenticate as admin (who has all groups)
        self.authenticate("admin", "admin")

    def test_supervisor_today_returns_200(self):
        """GET /api/security/mobile/supervisor/today must return 200 with success key."""
        resp = self.url_open("/api/security/mobile/supervisor/today")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("success", data)

    def test_supervisor_history_returns_200(self):
        """GET /api/security/mobile/supervisor/history must return 200."""
        resp = self.url_open("/api/security/mobile/supervisor/history")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("success", data)
        if data.get("success"):
            self.assertIn("batches", data.get("data", {}))

    def test_manager_dashboard_returns_200(self):
        """GET /api/security/mobile/manager/dashboard must return 200."""
        resp = self.url_open("/api/security/mobile/manager/dashboard")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("success", data)

    def test_owner_kpis_returns_200(self):
        """GET /api/security/mobile/owner/kpis must return 200."""
        resp = self.url_open("/api/security/mobile/owner/kpis")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("success", data)

    def test_mark_invalid_record_returns_error(self):
        """POST mark with non-existent record_id must return error."""
        resp = self.url_open(
            "/api/security/mobile/supervisor/mark",
            data=b'{"record_id": 999999, "manual_presence": "present"}',
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(resp.status_code, 404)
